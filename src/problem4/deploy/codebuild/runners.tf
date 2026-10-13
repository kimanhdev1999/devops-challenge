# CodeBuild-hosted GitHub Actions runners, in the shared services / CI account.
#
# A job with `runs-on: codebuild-<project>-${{ github.run_id }}-${{ github.run_attempt }}`
# fires a WORKFLOW_JOB_QUEUED webhook; CodeBuild starts one fresh container that registers
# as an ephemeral runner, runs that single job, and is destroyed.
#
#   gha-ci       PR and test jobs. Untrusted code, so no VPC and no AWS permissions.
#   gha-release  Jobs on main that push images and deploy. Private subnets, fixed egress IP,
#                its own layer cache, so nothing a PR builds can reach a release build.
#
# The service roles below only let CodeBuild run the container. Deploy rights still come
# from the per-environment OIDC roles in ../iam, so a runner on its own can't deploy.

terraform {
  required_version = ">= 1.6"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = ">= 5.70"
    }
  }
}

variable "github_repo_url" {
  description = "https://github.com/<OWNER>/<REPO>.git"
  type        = string
}

variable "codeconnections_arn" {
  description = "AWS CodeConnections (GitHub App) connection, created and approved once in the console"
  type        = string
}

variable "release_vpc_id" {
  type = string
}

variable "release_subnet_ids" {
  description = "Private subnets whose route goes through a NAT gateway (fixed egress IP) or Network Firewall"
  type        = list(string)
}

locals {
  runners = {
    gha-ci = {
      compute_type = "BUILD_GENERAL1_MEDIUM"
      in_vpc       = false
    }
    gha-release = {
      compute_type = "BUILD_GENERAL1_MEDIUM"
      in_vpc       = true
    }
  }
}

data "aws_partition" "current" {}
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# Lets CodeBuild register runners against the repo through the GitHub App connection.
resource "aws_codebuild_source_credential" "github" {
  auth_type   = "CODECONNECTIONS"
  server_type = "GITHUB"
  token       = var.codeconnections_arn
}

resource "aws_security_group" "release_runner" {
  name        = "gha-release-runner"
  description = "GitHub Actions release runners: egress only"
  vpc_id      = var.release_vpc_id

  egress {
    description = "HTTPS to GitHub, ECR, npm and AWS APIs (narrowed further by Network Firewall)"
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_cloudwatch_log_group" "runner" {
  for_each          = local.runners
  name              = "/codebuild/${each.key}"
  retention_in_days = 90
}

data "aws_iam_policy_document" "codebuild_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["codebuild.amazonaws.com"]
    }
    condition {
      test     = "StringEquals"
      variable = "aws:SourceAccount"
      values   = [data.aws_caller_identity.current.account_id]
    }
  }
}

resource "aws_iam_role" "runner" {
  for_each           = local.runners
  name               = "codebuild-${each.key}"
  assume_role_policy = data.aws_iam_policy_document.codebuild_assume.json
}

data "aws_iam_policy_document" "runner" {
  for_each = local.runners

  statement {
    sid       = "WriteOwnLogs"
    actions   = ["logs:CreateLogStream", "logs:PutLogEvents"]
    resources = ["${aws_cloudwatch_log_group.runner[each.key].arn}:*"]
  }

  statement {
    sid       = "UseGitHubConnection"
    actions   = ["codeconnections:UseConnection", "codeconnections:GetConnectionToken"]
    resources = [var.codeconnections_arn]
  }

  dynamic "statement" {
    for_each = each.value.in_vpc ? [1] : []
    content {
      sid = "RunInVpc"
      actions = [
        "ec2:CreateNetworkInterface",
        "ec2:DeleteNetworkInterface",
        "ec2:DescribeNetworkInterfaces",
        "ec2:DescribeDhcpOptions",
        "ec2:DescribeSubnets",
        "ec2:DescribeSecurityGroups",
        "ec2:DescribeVpcs",
      ]
      resources = ["*"]
    }
  }

  dynamic "statement" {
    for_each = each.value.in_vpc ? [1] : []
    content {
      sid       = "AttachEniToReleaseSubnetsOnly"
      actions   = ["ec2:CreateNetworkInterfacePermission"]
      resources = ["arn:${data.aws_partition.current.partition}:ec2:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:network-interface/*"]
      condition {
        test     = "StringEquals"
        variable = "ec2:AuthorizedService"
        values   = ["codebuild.amazonaws.com"]
      }
      condition {
        test     = "ArnEquals"
        variable = "ec2:Subnet"
        values = [for id in var.release_subnet_ids :
        "arn:${data.aws_partition.current.partition}:ec2:${data.aws_region.current.id}:${data.aws_caller_identity.current.account_id}:subnet/${id}"]
      }
    }
  }
}

resource "aws_iam_role_policy" "runner" {
  for_each = local.runners
  name     = "runner"
  role     = aws_iam_role.runner[each.key].id
  policy   = data.aws_iam_policy_document.runner[each.key].json
}

resource "aws_codebuild_project" "runner" {
  for_each      = local.runners
  name          = each.key
  description   = "GitHub Actions runner (${each.key})"
  service_role  = aws_iam_role.runner[each.key].arn
  build_timeout = 60 # minutes; every workflow job also sets its own timeout-minutes

  source {
    type     = "GITHUB"
    location = var.github_repo_url
  }

  artifacts {
    type = "NO_ARTIFACTS"
  }

  environment {
    type         = "LINUX_CONTAINER"
    compute_type = each.value.compute_type
    image        = "aws/codebuild/standard:7.0" # Ubuntu; ships Docker, jq, curl, AWS CLI v2
    # Docker daemon inside the build: needed for Buildx image builds and the gitleaks container.
    privileged_mode = true
  }

  # Layer cache stays on the CodeBuild host and is per project, so PR builds (gha-ci)
  # can never seed layers into release builds (gha-release).
  cache {
    type  = "LOCAL"
    modes = ["LOCAL_DOCKER_LAYER_CACHE", "LOCAL_SOURCE_CACHE"]
  }

  logs_config {
    cloudwatch_logs {
      group_name = aws_cloudwatch_log_group.runner[each.key].name
    }
  }

  dynamic "vpc_config" {
    for_each = each.value.in_vpc ? [1] : []
    content {
      vpc_id             = var.release_vpc_id
      subnets            = var.release_subnet_ids
      security_group_ids = [aws_security_group.release_runner.id]
    }
  }

  depends_on = [aws_codebuild_source_credential.github]
}

# Fires on every queued workflow job; CodeBuild only picks up jobs whose runs-on label
# names this project.
resource "aws_codebuild_webhook" "runner" {
  for_each     = local.runners
  project_name = aws_codebuild_project.runner[each.key].name
  build_type   = "BUILD"

  filter_group {
    filter {
      type    = "EVENT"
      pattern = "WORKFLOW_JOB_QUEUED"
    }
  }
}
