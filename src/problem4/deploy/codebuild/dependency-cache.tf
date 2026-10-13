# Dependency cache, in the same shared services / CI account as the runners and ECR.
#
#   npm packages   CodeArtifact repository with an upstream connection to npmjs. The first
#                  `npm ci` that asks for a version fetches and keeps it; every later build
#                  reads it from CodeArtifact. Published versions can't change, so a cached
#                  copy is always the same bytes as the lockfile's integrity hash.
#   base images    ECR pull-through cache for ECR Public, which mirrors the Docker Official
#                  Images (public.ecr.aws/docker/library/node). No upstream credentials and no
#                  Docker Hub pull limits.
#
# Release runners reach both through VPC endpoints, so dependency traffic stays off the NAT
# gateway. PR runners (no VPC) use the public AWS endpoints.
#
# Jobs read the cache with a read-only OIDC role (gha-deps-read). It can fetch packages and
# base images, and nothing else, so it is safe to hand to PR jobs.

variable "github_repo" {
  description = "<OWNER>/<REPO>"
  type        = string
}

variable "github_oidc_provider_arn" {
  description = "IAM OIDC provider for token.actions.githubusercontent.com in this account"
  type        = string
}

variable "release_route_table_ids" {
  description = "Route tables of the release subnets, for the S3 gateway endpoint"
  type        = list(string)
}

locals {
  account_id = data.aws_caller_identity.current.account_id
  region     = data.aws_region.current.id
  partition  = data.aws_partition.current.partition
}

# ---------------------------------------------------------------- npm: CodeArtifact

resource "aws_codeartifact_domain" "ci" {
  domain = "ci"
}

resource "aws_codeartifact_repository" "npm" {
  repository  = "npm"
  domain      = aws_codeartifact_domain.ci.domain
  description = "npm packages, fetched from npmjs on first use and kept"

  external_connections {
    external_connection_name = "public:npmjs"
  }
}

# ---------------------------------------------------------------- images: ECR pull-through

# <account>.dkr.ecr.<region>.amazonaws.com/ecr-public/docker/library/node:22-alpine
#   → public.ecr.aws/docker/library/node:22-alpine
resource "aws_ecr_pull_through_cache_rule" "ecr_public" {
  ecr_repository_prefix = "ecr-public"
  upstream_registry_url = "public.ecr.aws"
}

# Repositories the cache creates on first pull get scanned and pruned like our own.
resource "aws_ecr_repository_creation_template" "ecr_public" {
  prefix               = "ecr-public"
  description          = "Pull-through cache of ECR Public"
  applied_for          = ["PULL_THROUGH_CACHE"]
  image_tag_mutability = "MUTABLE" # the cache must be able to move 22-alpine to a new digest

  lifecycle_policy = jsonencode({
    rules = [{
      rulePriority = 1
      description  = "Drop cached images nobody has tagged for 90 days"
      selection = {
        tagStatus   = "untagged"
        countType   = "sinceImagePushed"
        countUnit   = "days"
        countNumber = 90
      }
      action = { type = "expire" }
    }]
  })
}

# ---------------------------------------------------------------- read-only OIDC role

data "aws_iam_policy_document" "deps_read_trust" {
  statement {
    actions = ["sts:AssumeRoleWithWebIdentity"]
    principals {
      type        = "Federated"
      identifiers = [var.github_oidc_provider_arn]
    }
    condition {
      test     = "StringEquals"
      variable = "token.actions.githubusercontent.com:aud"
      values   = ["sts.amazonaws.com"]
    }
    # Any workflow in this repo, PRs included: the role can only read public packages.
    condition {
      test     = "StringLike"
      variable = "token.actions.githubusercontent.com:sub"
      values   = ["repo:${var.github_repo}:*"]
    }
  }
}

resource "aws_iam_role" "deps_read" {
  name                 = "gha-deps-read"
  assume_role_policy   = data.aws_iam_policy_document.deps_read_trust.json
  max_session_duration = 3600
}

data "aws_iam_policy_document" "deps_read" {
  statement {
    sid       = "CodeArtifactToken"
    actions   = ["codeartifact:GetAuthorizationToken"]
    resources = [aws_codeartifact_domain.ci.arn]
  }

  statement {
    sid       = "CodeArtifactBearerToken"
    actions   = ["sts:GetServiceBearerToken"]
    resources = ["*"]
    condition {
      test     = "StringEquals"
      variable = "sts:AWSServiceName"
      values   = ["codeartifact.amazonaws.com"]
    }
  }

  statement {
    sid = "ReadNpm"
    # ReadFromRepository also lets a read pull a missing version through from npmjs.
    actions   = ["codeartifact:GetRepositoryEndpoint", "codeartifact:ReadFromRepository"]
    resources = [aws_codeartifact_repository.npm.arn]
  }

  statement {
    sid       = "EcrAuth"
    actions   = ["ecr:GetAuthorizationToken"]
    resources = ["*"]
  }

  statement {
    sid = "PullBaseImagesThroughCache"
    actions = [
      "ecr:BatchCheckLayerAvailability",
      "ecr:BatchGetImage",
      "ecr:GetDownloadUrlForLayer",
      # First pull of a new image/tag: create the cache repo and import from upstream.
      "ecr:CreateRepository",
      "ecr:BatchImportUpstreamImage",
    ]
    resources = ["arn:${local.partition}:ecr:${local.region}:${local.account_id}:repository/ecr-public/*"]
  }
}

resource "aws_iam_role_policy" "deps_read" {
  name   = "deps-read"
  role   = aws_iam_role.deps_read.id
  policy = data.aws_iam_policy_document.deps_read.json
}

# ---------------------------------------------------------------- VPC endpoints (release)

resource "aws_security_group" "endpoints" {
  name        = "ci-dependency-endpoints"
  description = "Interface endpoints for CodeArtifact and ECR, reachable from release runners"
  vpc_id      = var.release_vpc_id

  ingress {
    description     = "HTTPS from release runners"
    from_port       = 443
    to_port         = 443
    protocol        = "tcp"
    security_groups = [aws_security_group.release_runner.id]
  }
}

resource "aws_vpc_endpoint" "interface" {
  for_each = toset([
    "codeartifact.api",
    "codeartifact.repositories", # needs private DNS so npm can use the normal hostname
    "ecr.api",
    "ecr.dkr",
  ])

  vpc_id              = var.release_vpc_id
  service_name        = "com.amazonaws.${local.region}.${each.key}"
  vpc_endpoint_type   = "Interface"
  subnet_ids          = var.release_subnet_ids
  security_group_ids  = [aws_security_group.endpoints.id]
  private_dns_enabled = true

  tags = { Name = "ci-${each.key}" }
}

# ECR image layers and CodeArtifact package assets are served from S3.
resource "aws_vpc_endpoint" "s3" {
  vpc_id            = var.release_vpc_id
  service_name      = "com.amazonaws.${local.region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.release_route_table_ids

  tags = { Name = "ci-s3" }
}

output "deps_read_role_arn" {
  description = "Repository variable AWS_DEPS_ROLE_ARN"
  value       = aws_iam_role.deps_read.arn
}

output "codeartifact" {
  description = "Repository variables CODEARTIFACT_DOMAIN, CODEARTIFACT_DOMAIN_OWNER, CODEARTIFACT_REPOSITORY"
  value = {
    domain       = aws_codeartifact_domain.ci.domain
    domain_owner = aws_codeartifact_domain.ci.owner
    repository   = aws_codeartifact_repository.npm.repository
  }
}
