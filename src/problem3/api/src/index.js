const express = require("express");
const { Pool } = require("pg");
const Redis = require("ioredis");

const PORT = Number(process.env.PORT || 3000);

const app = express();

const pool = new Pool({
  host: process.env.DB_HOST,
  user: process.env.DB_USER || "postgres",
  password: process.env.DB_PASSWORD,
  database: process.env.DB_NAME || "postgres",
  port: 5432,
  max: Number(process.env.DB_POOL_MAX || 10),
  connectionTimeoutMillis: 2000, // fail fast instead of waiting forever for a client
  idleTimeoutMillis: 30000,
  query_timeout: 5000,
});

// An idle client dying (e.g. Postgres restart) emits 'error' on the pool.
// Without a listener Node treats it as unhandled and kills the process.
pool.on("error", (err) => console.error("pg pool error:", err.message));

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: 6379,
  connectTimeout: 2000,
  maxRetriesPerRequest: 1, // don't block a request for ~10 s while Redis is down
  enableOfflineQueue: false,
});
redis.on("error", (err) => console.error("redis error:", err.message));

app.get("/api/users", async (req, res) => {
  try {
    // pool.query checks out and always releases the client, even when the query throws
    const result = await pool.query("SELECT NOW()");

    // last_call is bookkeeping: a Redis outage should not fail the request
    redis.set("last_call", Date.now()).catch((err) => console.error("redis set failed:", err.message));

    res.json({ ok: true, time: result.rows[0] });
  } catch (err) {
    console.error(err);
    res.status(503).json({ ok: false, error: "database unavailable" });
  }
});

// Liveness: the process is up and serving
app.get("/status", (req, res) => {
  res.json({ status: "ok" });
});

// Readiness: dependencies are reachable
app.get("/ready", async (req, res) => {
  const checks = {};
  try { await pool.query("SELECT 1"); checks.postgres = "ok"; } catch (e) { checks.postgres = e.message; }
  try { await redis.ping(); checks.redis = "ok"; } catch (e) { checks.redis = e.message; }
  const ok = Object.values(checks).every((v) => v === "ok");
  res.status(ok ? 200 : 503).json({ ready: ok, checks });
});

const server = app.listen(PORT, () => console.log(`API running on ${PORT}`));

// Graceful shutdown so `docker stop` doesn't cut in-flight requests
function shutdown(signal) {
  console.log(`${signal} received, shutting down`);
  server.close(async () => {
    await Promise.allSettled([pool.end(), redis.quit()]);
    process.exit(0);
  });
  setTimeout(() => process.exit(1), 10000).unref();
}
process.on("SIGTERM", () => shutdown("SIGTERM"));
process.on("SIGINT", () => shutdown("SIGINT"));
