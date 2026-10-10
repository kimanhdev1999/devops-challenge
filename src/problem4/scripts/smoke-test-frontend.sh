#!/usr/bin/env bash
# Checks the live site serves the expected release and that every asset it references loads.
#   smoke-test-frontend.sh <site-url> <expected-version>
set -euo pipefail
URL="${1%/}"; EXPECTED="${2:?expected version required}"

for attempt in $(seq 1 10); do
  version=$(curl -fsS "${URL}/manifest.json" | jq -r .version || true)
  [[ "${version}" == "${EXPECTED}" ]] && break
  echo "attempt ${attempt}: live version '${version}', want '${EXPECTED}'"; sleep 6
done
[[ "${version}" == "${EXPECTED}" ]] || { echo "::error::site still serves ${version}"; exit 1; }

curl -fsS "${URL}/" | grep -oE '/assets/[A-Za-z0-9._-]+' | sort -u | while read -r asset; do
  curl -fsS -o /dev/null "${URL}${asset}" || { echo "::error::missing ${asset}"; exit 1; }
  echo "ok ${asset}"
done
