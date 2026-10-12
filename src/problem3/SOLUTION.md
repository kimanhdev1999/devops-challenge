# Problem 3: Debugging issues within the system

The API was unreliable for two reasons. NGINX proxied to the wrong port, so every `/api/*` call returned 502. Behind that, the API had no resilience: one Postgres restart killed the process permanently, a Redis outage stalled every request, and a slow database hung requests with no timeout. All issues below were reproduced on the original stack, fixed, and re-tested.

> The template README calls this "Problem 4"; it is the Problem 3 system (`src/problem3`).

## How I diagnosed it

1. Ran the stack as given and probed every route with `curl`, reading `docker compose logs nginx`.
2. Called the API directly inside its container (`docker exec api wget localhost:3000/...`) to separate NGINX problems from API problems.
3. Injected the failures a real environment sees: `docker restart postgres`, `docker stop redis`, `docker pause postgres` (a hung database), recreating the API container on a new IP, and a cold start on an empty Postgres volume.
   Issue #1 masks #8 (every request is already a 502), so #8 was tested on a copy of the original with only the port changed.
4. Read the code and configs for problems that don't show up on a happy-path run.

## Issues found

| # | Issue | Evidence | Impact |
| --- | --- | --- | --- |
| 1 | NGINX proxies to `api:3001`, the API listens on `3000` | `/api/users` → **502**; log: `connect() failed (111: Connection refused) ... upstream: "http://172.19.0.4:3001/api/users"` | API completely inaccessible |
| 2 | No `pool.on('error')` handler in the API | `docker restart postgres` → API container **exited (1)**: `error: terminating connection due to administrator command` (unhandled `'error'` event) | One DB restart or failover kills the API |
| 3 | No restart policy on any service | After #2 the API stayed down until manually started | Outage lasts until a human notices: "sometimes inaccessible" |
| 4 | No connection or query timeout on the pg pool | `docker pause postgres` → request **hung >25 s** with no response | Requests pile up; NGINX returns 504 after 60 s; clients hang |
| 5 | Client leak on query error: `db.release()` is skipped when `db.query()` throws | `connect()` → `query()` throws → jump to `catch`, client never released. Reproduced with the handler's pattern and a failing query (pool `max: 3`): after 3 failures the pool is full and a good query was **still waiting after 5 s**. With the default `max: 10`, 10 failures hang every request | Pool exhaustion → API hangs until restart |
| 6 | Request blocks on a non-essential Redis write | `docker stop redis` → `/api/users` took **10 s** then **500** (ioredis offline queue + 20 retries) | A cache outage takes down a DB-backed endpoint |
| 7 | `depends_on` without health checks | Cold start on an empty volume: API container started **70 ms** after Postgres, ~0.6 s before Postgres was ready; a request in that window → **500** (`ECONNREFUSED`) | First requests after a deploy fail (a longer window with a large database or crash recovery) |
| 8 | NGINX resolves `api` once at startup | Original with only the port fixed: API recreated on a new IP (`.4` → `.6`, old IP taken by another container) → **502 for 20 s+**, while the API was healthy; **200** only after restarting NGINX | If the API container is recreated with a new IP, NGINX keeps proxying to the old one until it restarts |
| 9 | `/status` health route not exposed through NGINX | `/status` → 404 | No way to health-check the API from outside |
| 10 | `postgres/init.sql` (`max_connections = 20`) is never mounted | `docker inspect` shows no init mount; `SHOW max_connections` → 100 | Dead config. Had it been mounted it would cap Postgres at 20 connections, so it was removed, not wired up |
| 11 | Empty `nginx/nginx.conf` | Not mounted | Mounting it would break NGINX; removed |
| 12 | No persistent volume for Postgres, hardcoded password, container runs as root | Compose file / Dockerfile | Data lost on `down`; weak secret handling |

## Fixes applied

| File | Change | Fixes |
| --- | --- | --- |
| `nginx/conf.d/default.conf` | Proxy to port `3000`; Docker DNS `resolver 127.0.0.11 valid=10s` with a variable `proxy_pass` so the API's IP is re-resolved; `proxy_connect_timeout 2s`, `proxy_read_timeout 10s`; forwarding headers + `X-Request-ID`; routes for `/status`, `/ready`; NGINX's own `/healthz` | 1, 4, 8, 9 |
| `api/src/index.js` | `pool.on('error')` and `redis.on('error')` listeners | 2 |
| | `pool.query()` instead of manual `connect/release` (always releases) | 5 |
| | `connectionTimeoutMillis: 2000`, `query_timeout: 5000`, `idleTimeoutMillis` | 4 |
| | Redis `maxRetriesPerRequest: 1`, `enableOfflineQueue: false`; `last_call` write is best-effort | 6 |
| | `/ready` endpoint checking Postgres and Redis; DB errors return `503` | 9 |
| | Graceful `SIGTERM` shutdown (close server, drain pool) | Clean deploys |
| `docker-compose.yml` | `restart: unless-stopped` on all services | 3 |
| | Health checks on every service; `depends_on: condition: service_healthy` | 7 |
| | `pgdata` volume; password from `.env` (`${POSTGRES_PASSWORD:?}`); `init: true`; memory limit; Redis `maxmemory` + LRU | 12 |
| `api/Dockerfile` | `NODE_ENV=production`, `npm install --omit=dev`, runs as `USER node` | 12 |
| removed | `postgres/init.sql`, `nginx/nginx.conf` | 10, 11 |

## Verification (after the fix)

| Test | Before | After |
| --- | --- | --- |
| `GET /api/users` | 502 | **200** in ~2 ms |
| `GET /status`, `/ready` | 404 | **200** (`/ready` reports each dependency) |
| `docker restart postgres` | API crashed, stayed down | API keeps running (0 restarts); next request **200** |
| `docker stop redis` | 10 s, then 500 | `/api/users` **200** in 2 ms; `/ready` **503** naming Redis |
| `docker pause postgres` (hung DB) | Hung indefinitely | **503 in 5 s** (bounded by `query_timeout`) |
| Pool leak: 15 failing queries, then a good one | Good query waits forever | Good query in 3 ms; pool idle, nothing waiting |
| Recreate the API container on a **new IP** | 502 for 20 s+, until NGINX restarts (tested with only the port fixed) | **200** on the next request |
| Cold start on an empty volume | API starts 70 ms after Postgres; early request → 500 | API starts only after Postgres is healthy (~5 s); first request **200**; 0 DB errors; NGINX up after the API is healthy (~10 s total) |
| 500 requests, 50 concurrent | — | **500 × 200** |

A plain `docker compose up -d --force-recreate api` usually hands the API its old IP back, so it passes even without the fix. To test #8, occupy the old IP first (e.g. stop the API and `docker run -d --network <project>_default alpine sleep 300`), then recreate.

Run it: `docker compose up --build`, then `curl localhost:8080/api/users`.

## Monitoring and alerts I would add

| Signal | Alert |
| --- | --- |
| NGINX 5xx rate by status (502/503/504) from access logs or `stub_status` / an exporter | 5xx > 1% for 5 min → page |
| API p99 latency on `/api/users` | p99 > 500 ms for 10 min → warn |
| `/ready` probe from outside (blackbox exporter) | 2 consecutive failures → page; include which dependency failed |
| Container restarts / exits (cAdvisor, `docker events`) | Any restart loop (> 3 in 10 min) → page |
| pg pool: `totalCount`, `idleCount`, `waitingCount` exported from the API | `waitingCount > 0` for 1 min → warn (pool exhaustion) |
| Postgres connections vs `max_connections`, replication/up | > 80% → warn |
| Redis up, memory vs `maxmemory`, evictions | Down → warn (non-critical); memory > 90% → warn |
| Structured JSON logs with `X-Request-ID` shipped centrally | Error-log rate spike → warn |

## How I would prevent this in production

- **Config tests in CI:** `nginx -t` plus a `docker compose up --wait` smoke test that curls `/api/users`. Issue #1 never reaches users.
- **Failure-injection tests:** restart or stop each dependency in CI or staging and assert the API survives (exactly the tests above).
- **Single source of truth for ports:** set `PORT` through env/compose and reference it in NGINX from the same variable or template.
- **Lint and review rules:** require timeouts on every outbound client, `try/finally` or `pool.query` for pooled resources, and error listeners on emitters (an ESLint rule plus a PR checklist).
- **Run on an orchestrator** (ECS/EKS) with liveness = `/status`, readiness = `/ready`, multiple API replicas behind the proxy, and managed Postgres/Redis (RDS / ElastiCache Multi-AZ). A single crash then never causes an outage.
- **Secrets from a secret manager**, not `.env`; Postgres on a persistent, backed-up volume.
- **SLOs with burn-rate alerts** on availability and latency instead of only threshold alerts.
