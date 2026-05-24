# OIDC trust for GitHub Actions. No static AWS keys ever live in GitHub
# secrets -- the workflow exchanges its short-lived OIDC token for an
# AssumeRole call against this role.
#
# The trust policy is scoped to a single GitHub repository so a fork
# can't borrow the role. Restrict further to specific refs (e.g. only
# main) if desired -- see the `sub` condition below.

# GitHub's public OIDC thumbprint. Hard-coded by convention; AWS publishes
# a list of trusted Actions provider thumbprints that rotate occasionally.
resource "aws_iam_openid_connect_provider" "github" {
  url             = "https://token.actions.githubusercontent.com"
  client_id_list  = ["sts.amazonaws.com"]
  # Empty list -> AWS uses its built-in chain validation. (Modern accounts
  # auto-trust the GitHub OIDC root cert.)
  thumbprint_list = ["6938fd4d98bab03faadb97b34396831e3780aea1"]
}

resource "aws_iam_role" "github_actions_deploy" {
  name = "${local.name}-gha-deploy"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = {
        Federated = aws_iam_openid_connect_provider.github.arn
      }
      Action = "sts:AssumeRoleWithWebIdentity"
      Condition = {
        StringEquals = {
          "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
        }
        # Restrict to the configured repo. To restrict further to a
        # specific branch, replace `*` with `ref:refs/heads/main`.
        StringLike = {
          "token.actions.githubusercontent.com:sub" = "repo:${var.github_repository}:*"
        }
      }
    }]
  })
}

# Scoped permissions: enough to build & push images and roll the ECS
# services, nothing else. No iam:*, no broad ecs:*.
resource "aws_iam_role_policy" "github_actions_deploy" {
  name = "${local.name}-gha-deploy-policy"
  role = aws_iam_role.github_actions_deploy.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # ECR auth token is account-scoped; can't be narrowed to a repo.
        Effect   = "Allow"
        Action   = ["ecr:GetAuthorizationToken"]
        Resource = "*"
      },
      {
        Effect = "Allow"
        Action = [
          "ecr:BatchCheckLayerAvailability",
          "ecr:BatchGetImage",
          "ecr:CompleteLayerUpload",
          "ecr:DescribeRepositories",
          "ecr:GetDownloadUrlForLayer",
          "ecr:InitiateLayerUpload",
          "ecr:PutImage",
          "ecr:UploadLayerPart",
        ]
        Resource = [
          aws_ecr_repository.backend.arn,
          aws_ecr_repository.frontend.arn,
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "ecs:DescribeServices",
          "ecs:DescribeTaskDefinition",
          "ecs:RegisterTaskDefinition",
          "ecs:UpdateService",
        ]
        Resource = "*"
      },
      {
        # Passing the execution + task roles is required when
        # registering a new task definition revision.
        Effect = "Allow"
        Action = ["iam:PassRole"]
        Resource = [
          aws_iam_role.execution.arn,
          aws_iam_role.task.arn,
        ]
      },
    ]
  })
}
