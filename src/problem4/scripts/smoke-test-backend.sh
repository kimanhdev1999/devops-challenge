#!/usr/bin/env bash
# Polls the public health endpoint until it reports the expected version.
#   smoke-test-backend.sh <base-url> <expected-version>
set -euo pipefail
URL="${1%/}"; EXPECTED="${2:?expected version required}"

for attempt in $(seq 1 12); do
  body=$(curl -fsS --max-time 5 "${URL}/healthz" || true)
  if [[ -n "${body}" && "$(jq -r .version <<<"${body}" 2>/dev/null)" == "${EXPECTED}" ]]; then
    echo "healthy: ${body}"; exit 0
  fi
  echo "attempt ${attempt}: ${body:-no response}"; sleep 5
done
echo "::error::${URL}/healthz never reported version ${EXPECTED}"
exit 1
