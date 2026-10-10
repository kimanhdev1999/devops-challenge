#!/usr/bin/env bash
# Runs ON each backend EC2 instance, invoked by the Backend-Deploy SSM document.
# Baked into the AMI (or written by user data) at /opt/backend/deploy.sh.
#
#   deploy.sh <image-uri> <target-group-arn>
#
# Drain from the ALB -> swap container -> health check -> re-register.
# On a failed health check it restores the previous image and exits 1, which stops the
# rolling deploy before it reaches the next instance.
set -euo pipefail

IMAGE="$1"; TG_ARN="$2"
NAME=backend; PORT=3000; STATE=/opt/backend/current-image
log() { echo "[deploy $(date -u +%FT%TZ)] $*"; }

token=$(curl -fsS -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 300')
imds() { curl -fsS -H "X-aws-ec2-metadata-token: ${token}" "http://169.254.169.254/latest/meta-data/$1"; }
INSTANCE_ID=$(imds instance-id); REGION=$(imds placement/region)
PREVIOUS=$(cat "${STATE}" 2>/dev/null || true)

run_container() {
  docker stop -t 30 "${NAME}" >/dev/null 2>&1 || true   # SIGTERM; the app drains in-flight requests
  docker rm "${NAME}" >/dev/null 2>&1 || true
  docker run -d --name "${NAME}" --restart unless-stopped -p "${PORT}:3000" \
    --log-driver awslogs --log-opt awslogs-region="${REGION}" --log-opt awslogs-group=/app/backend \
    "$1" >/dev/null
}
healthy() {
  for _ in $(seq 1 30); do curl -fsS --max-time 2 "http://127.0.0.1:${PORT}/healthz" >/dev/null && return 0; sleep 2; done
  return 1
}
target() { aws elbv2 "$1" --region "${REGION}" --target-group-arn "${TG_ARN}" --targets "Id=${INSTANCE_ID},Port=${PORT}"; }

log "pulling ${IMAGE} (previous: ${PREVIOUS:-none})"
aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${IMAGE%%/*}" >/dev/null
docker pull --quiet "${IMAGE}"   # pull before draining so the instance is out of service only for the swap

log "draining ${INSTANCE_ID} from the target group"
target deregister-targets
target wait target-deregistered

run_container "${IMAGE}"
if healthy; then
  echo "${IMAGE}" > "${STATE}"
  target register-targets
  target wait target-in-service
  log "now serving ${IMAGE}"
  exit 0
fi

log "health check failed for ${IMAGE}; last log lines:"
docker logs --tail 50 "${NAME}" 2>&1 || true
if [[ -n "${PREVIOUS}" ]]; then
  log "restoring ${PREVIOUS}"
  run_container "${PREVIOUS}"
  healthy && target register-targets
fi
exit 1
