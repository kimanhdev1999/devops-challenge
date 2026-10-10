#!/usr/bin/env bash
# Launch-template user data for backend instances (Amazon Linux 2023).
# A new instance started by the Auto Scaling group runs whatever image the pipeline last
# recorded as current for its environment, so scale-out never brings back an old version.
set -euo pipefail
dnf install -y docker jq
systemctl enable --now docker

ENVIRONMENT="__ENVIRONMENT__"        # templated by Terraform
token=$(curl -fsS -X PUT http://169.254.169.254/latest/api/token -H 'X-aws-ec2-metadata-token-ttl-seconds: 60')
REGION=$(curl -fsS -H "X-aws-ec2-metadata-token: ${token}" http://169.254.169.254/latest/meta-data/placement/region)
IMAGE=$(aws ssm get-parameter --region "${REGION}" --name "/app/backend/${ENVIRONMENT}/image" --query Parameter.Value --output text)

mkdir -p /opt/backend
aws ecr get-login-password --region "${REGION}" | docker login --username AWS --password-stdin "${IMAGE%%/*}"
docker run -d --name backend --restart unless-stopped -p 3000:3000 \
  --log-driver awslogs --log-opt awslogs-region="${REGION}" --log-opt awslogs-group=/app/backend "${IMAGE}"
echo "${IMAGE}" > /opt/backend/current-image
# /opt/backend/deploy.sh is baked into the AMI; the ALB health check registers the instance.
