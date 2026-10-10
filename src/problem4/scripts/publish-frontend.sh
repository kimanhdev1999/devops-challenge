#!/usr/bin/env bash
# Runs in GitHub Actions. Publishes a built SPA (dist/) to the site bucket in two phases so
# users never load an index.html that points at assets which are not uploaded yet.
#
#   publish-frontend.sh <dist-dir>
#
# Env: SITE_BUCKET, DISTRIBUTION_ID, ENVIRONMENT, API_BASE_URL
set -euo pipefail

DIST="${1:?dist dir required}"
: "${SITE_BUCKET:?}" "${DISTRIBUTION_ID:?}" "${ENVIRONMENT:?}" "${API_BASE_URL:?}"

# Same build for every environment; only the runtime config differs.
jq -n --arg env "${ENVIRONMENT}" --arg api "${API_BASE_URL}" \
  '{environment: $env, apiBaseUrl: $api}' > "${DIST}/config.json"

# 1. Hashed assets first, cached for a year. No --delete: browsers holding the previous
#    index.html still need the previous assets, and keeping them makes rollback instant.
aws s3 sync "${DIST}/assets" "s3://${SITE_BUCKET}/assets" \
  --cache-control "public, max-age=31536000, immutable" --only-show-errors

# 2. Entry points last, never cached by browsers or CloudFront.
for f in index.html config.json manifest.json; do
  aws s3 cp "${DIST}/${f}" "s3://${SITE_BUCKET}/${f}" \
    --cache-control "no-cache, no-store, must-revalidate" --only-show-errors
done

# 3. Only the unhashed entry points can be stale at the edge.
inv_id=$(aws cloudfront create-invalidation --distribution-id "${DISTRIBUTION_ID}" \
  --paths /index.html /config.json /manifest.json / --query Invalidation.Id --output text)
aws cloudfront wait invalidation-completed --distribution-id "${DISTRIBUTION_ID}" --id "${inv_id}"
echo "Published $(jq -r .version "${DIST}/manifest.json") to ${ENVIRONMENT}"
