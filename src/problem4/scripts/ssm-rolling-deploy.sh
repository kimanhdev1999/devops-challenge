#!/usr/bin/env bash
# Runs in GitHub Actions. Rolls one container image across every backend instance of an
# environment, one instance at a time, using an SSM Run Command document.
#
#   ssm-rolling-deploy.sh <image-uri>
#
# Env: ENVIRONMENT, SSM_DOCUMENT, TARGET_GROUP_ARN, AWS_REGION
# Exits non-zero if any instance fails; SSM stops the rollout at the first failure (max-errors 0).
set -euo pipefail

IMAGE="${1:?image uri required}"
: "${ENVIRONMENT:?}" "${SSM_DOCUMENT:?}" "${TARGET_GROUP_ARN:?}" "${AWS_REGION:?}"

echo "Deploying ${IMAGE} to ${ENVIRONMENT}"
cmd_id=$(aws ssm send-command \
  --document-name "${SSM_DOCUMENT}" \
  --targets "Key=tag:Service,Values=backend" "Key=tag:Environment,Values=${ENVIRONMENT}" \
  --parameters "ImageUri=${IMAGE},TargetGroupArn=${TARGET_GROUP_ARN}" \
  --max-concurrency 1 --max-errors 0 \
  --timeout-seconds 900 \
  --cloud-watch-output-config CloudWatchOutputEnabled=true,CloudWatchLogGroupName="/ssm/backend-deploy" \
  --comment "deploy ${GITHUB_SHA:-manual} run ${GITHUB_RUN_ID:-local}" \
  --query Command.CommandId --output text)
echo "SSM command: ${cmd_id}"

deadline=$((SECONDS + 1500))
while :; do
  read -r status targets completed errors < <(aws ssm list-commands --command-id "${cmd_id}" \
    --query 'Commands[0].[Status,TargetCount,CompletedCount,ErrorCount]' --output text)
  echo "status=${status} instances=${completed}/${targets} errors=${errors}"
  case "${status}" in
    Success)
      # A tag filter that matches nothing also reports Success; treat it as a failure.
      if [[ "${targets}" -eq 0 ]]; then echo "::error::no instances matched Service=backend,Environment=${ENVIRONMENT}"; exit 1; fi
      break ;;
    Failed|Cancelled|TimedOut|Cancelling)
      # shellcheck disable=SC2016  # backticks are JMESPath literals, not shell
      aws ssm list-command-invocations --command-id "${cmd_id}" --details \
        --query 'CommandInvocations[?Status!=`Success`].[InstanceId,Status,CommandPlugins[0].Output]' --output text || true
      echo "::error::deploy ${status} on ${errors} instance(s)"
      exit 1 ;;
  esac
  if (( SECONDS > deadline )); then echo "::error::timed out waiting for ${cmd_id}"; exit 1; fi
  sleep 10
done
echo "Deployed ${IMAGE} to ${targets} instance(s)"
