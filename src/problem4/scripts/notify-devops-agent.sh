#!/usr/bin/env bash
# Start an AWS DevOps Agent investigation for a failed release, through the Agent Space's
# generic webhook (HMAC). The agent then reads the run's logs through its GitHub integration
# and correlates them with CloudWatch, CloudTrail and the deployed resources.
#
# Only title, description and priority reach the agent, so everything it needs to start
# goes into the description.
#
# Env: WEBHOOK_URL, WEBHOOK_SECRET, APP, PRIORITY, RESULTS (toJSON(needs) of the caller),
#      plus the GITHUB_* variables Actions sets.
set -euo pipefail

: "${WEBHOOK_URL:?}" "${WEBHOOK_SECRET:?}" "${APP:?}" "${PRIORITY:?}" "${RESULTS:?}"

run_url="${GITHUB_SERVER_URL}/${GITHUB_REPOSITORY}/actions/runs/${GITHUB_RUN_ID}"
failed=$(jq -r '[to_entries[] | select(.value.result == "failure") | .key] | join(", ")' <<<"${RESULTS}")
image=$(jq -r '[.[].outputs.image // empty] | first // "n/a"' <<<"${RESULTS}")

description=$(cat <<EOF
GitHub Actions release of ${APP} failed in ${GITHUB_REPOSITORY}.
Workflow: ${GITHUB_WORKFLOW}, run ${run_url} (attempt ${GITHUB_RUN_ATTEMPT}).
Commit: ${GITHUB_SHA}. Triggered by ${GITHUB_EVENT_NAME} from ${GITHUB_ACTOR}.
Failed jobs: ${failed:-none reported}. Image: ${image}.
The deploy job restores the previously live release on failure, so check whether the
rollback also succeeded. Find the root cause: read the failed job logs, then the SSM Run
Command output (document Backend-Deploy) and ALB target health for the backend, or the
S3/CloudFront publish for the frontend. Compare with the previous successful release.
EOF
)

payload=$(jq -cn \
  --arg id "gha-${GITHUB_REPOSITORY//\//-}-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}" \
  --arg priority "${PRIORITY}" \
  --arg title "Release of ${APP} failed (${GITHUB_SHA:0:7})" \
  --arg description "${description}" \
  --arg service "${APP}" \
  --arg ts "$(date -u +%Y-%m-%dT%H:%M:%SZ)" \
  --arg run_url "${run_url}" \
  --arg sha "${GITHUB_SHA}" \
  '{eventType: "incident", incidentId: $id, action: "created", priority: $priority,
    title: $title, description: $description, timestamp: $ts, service: $service,
    data: {runUrl: $run_url, commit: $sha}}')

# Signature = base64(HMAC-SHA256(secret, "<timestamp>:<body>")).
timestamp=$(date -u +%Y-%m-%dT%H:%M:%S.000Z)
signature=$(printf '%s:%s' "${timestamp}" "${payload}" \
  | openssl dgst -sha256 -hmac "${WEBHOOK_SECRET}" -binary | base64)

curl -fsS --retry 3 --retry-all-errors --max-time 20 -X POST "${WEBHOOK_URL}" \
  -H "Content-Type: application/json" \
  -H "x-amzn-event-timestamp: ${timestamp}" \
  -H "x-amzn-event-signature: ${signature}" \
  --data "${payload}"
echo
echo "Investigation requested (priority ${PRIORITY}); follow it in the DevOps Agent web app."
