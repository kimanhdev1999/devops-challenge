# Problem 2: Diagnose Me Doctor

**Scenario:** an Ubuntu 24.04 VM with 64 GB of storage runs only NGINX as a load balancer for upstream services, and monitoring reports it constantly at 99% disk usage.

**Short answer:** on a box that only runs NGINX, the most likely cause is NGINX logs growing without bound (cause A), often combined with rotated or deleted logs that NGINX still holds open (cause B). Stabilise first, measure, then fix the root cause and add guardrails.

## 1. Stabilise first

At 99% the VM is minutes away from 100%. Once the disk is full, NGINX can't buffer request or response bodies to disk, so large uploads and responses fail with 5xx. Its cache and logs stop writing, and package updates and journald fail. Logging in can fail too. Because this VM routes all upstream traffic, that's a full outage.

Free space safely before investigating:

```bash
df -hT /                                       # which filesystem is full
df -i /                                        # inodes exhausted, not just bytes?
sudo journalctl --vacuum-size=500M             # quick win if the journal is large
sudo apt-get clean                             # quick win
sudo truncate -s 0 /var/log/nginx/access.log   # huge active log: truncate, never rm
```

Never `rm` a log NGINX has open: the space isn't freed until NGINX lets go of the file (cause B).

## 2. Find what's using the space

```bash
sudo du -xh --max-depth=1 / | sort -h | tail             # biggest top-level dirs, this filesystem only
sudo du -xh --max-depth=2 /var | sort -h | tail
sudo ncdu -x /                                            # interactive view
sudo find / -xdev -type f -size +500M -exec ls -lh {} \;  # large single files
sudo lsof -nP +L1                                         # deleted files still held open
journalctl --disk-usage
sudo iotop -oa                                            # what is writing right now
watch -n5 df -h /                                         # growth rate
```

- **`df` vs `du`:** if `df` says 63 GB is used but `du` finds 20 GB, deleted-but-open files hold the rest (cause B).
- **Growth rate:** a sudden jump points to a traffic spike, an attack or debug logging. Slow, steady growth points to rotation or retention that isn't working.

## 3. Possible root causes, impact and recovery

| # | Cause | How you spot it | Impact | Recovery | Prevention |
| --- | --- | --- | --- | --- | --- |
| A | **NGINX access/error logs grow unbounded.** logrotate isn't running or misses a custom log path, `error_log` is at `debug`/`info`, traffic grew, or an attack/scraper multiplies requests; health checks logged on every hit | `/var/log/nginx` dominates `du`; huge `access.log` / `error.log` | Disk fills → log writes fail → 5xx and OS issues above | Truncate the active log; fix `/etc/logrotate.d/nginx` (`daily`, `maxsize 1G`, `rotate 7`, `compress`, `delaycompress`, `postrotate nginx -s reopen`) and dry-run with `logrotate -d`; set `error_log ... warn` | Ship logs off-box (Fluent Bit/Vector → CloudWatch/Loki/S3), short local retention, `access_log ... if=$loggable` to skip health checks, rate-limit abusive clients |
| B | **Deleted logs still held open by NGINX.** Someone `rm`'d logs, or rotation ran without a reopen | `df` full but `du` doesn't add up; `lsof +L1` shows `nginx ... (deleted)` | Space never freed while NGINX runs | `sudo nginx -s reopen` or `systemctl reload nginx`; or truncate via the process handle `: > /proc/<pid>/fd/<n>` | Correct `postrotate`; never `rm` live logs |
| C | **System logs: journald / rsyslog.** No `SystemMaxUse` limit, or NGINX logs duplicated into `/var/log/syslog` | `journalctl --disk-usage` large; big `/var/log/syslog` | Same as A | `journalctl --vacuum-size=500M`; remove the duplicate rsyslog rule | `SystemMaxUse=1G` in `journald.conf`; logrotate for syslog |
| D | **NGINX proxy cache / temp files.** `proxy_cache_path` has no `max_size`, or large bodies are buffered to `proxy_temp_path` / `client_body_temp_path` | `/var/cache/nginx` or `/var/lib/nginx` large | Cache writes fail; large requests return 500 with "No space left on device" | Clear the cache directory and reload | `max_size=10g inactive=60m use_temp_path=off`; `proxy_max_temp_file_size`; `proxy_request_buffering off` where safe; cache on its own volume |
| E | **Leftovers unrelated to NGINX.** apt cache, old kernels, old snap revisions, core dumps from a crash-looping service, stray tcpdump captures or backups, old Docker images | `du` points at `/var/cache/apt`, `/var/lib/snapd`, `/var/crash`, `/var/lib/systemd/coredump`, `/home`, `/tmp` | Slow creep to full | `apt-get clean`; `apt-get autoremove --purge`; remove disabled snap revisions; clear crash dumps; delete stray files after checking with their owner | `snap set system refresh.retain=2`; limits in `coredump.conf`; unattended-upgrades with autoremove |
| F | **Inodes exhausted, not bytes.** Millions of small files (cache keys, temp or session files) | `df -i` at 100% while `df -h` may show space | Writes fail exactly like a full disk | Find the directory (`find / -xdev -type d -size +10M`, or count files per dir); clean it and cap the producer | Alert on inode usage as well as bytes |
| G | **Disk smaller than expected.** Disk resized in the cloud but the partition and filesystem were never grown; or monitoring watches a small root partition while data sits elsewhere | `lsblk` shows disk > partition | Fills sooner than planned | `growpart /dev/xvda 1` then `resize2fs /dev/xvda1` (or `xfs_growfs /`), online | Grow filesystems in the resize runbook / cloud-init |

## 4. Prevention and guardrails

- **Alerts:** warn at 75%, page at 85%, and alert on predicted fill time (Prometheus `predict_linear(node_filesystem_avail_bytes[6h], 4*3600) < 0`). Track inodes too.
- **Logs:** central shipping, short local retention, logrotate tested in configuration management or CI.
- **Disk layout:** `/var/log` and `/var/cache/nginx` on separate volumes so they can't fill the root filesystem.
- **Bounded NGINX caches and temp files** via `max_size` and temp-file limits.
- **No single point of failure:** at least two load balancers behind a cloud LB or a floating IP, so one full disk isn't an outage.
- **Immutable rebuilds:** the VM is built from an image / Terraform, so a sick node is replaced rather than repaired by hand.
