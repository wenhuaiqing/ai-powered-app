# Two ECS roles, standard pattern:
# - execution_role: ECS itself assumes this to pull the image from ECR,
#   read the secret out of Secrets Manager, and write CloudWatch logs.
# - task_role: the running container assumes this to call AWS APIs at
#   runtime (Bedrock invoke, future S3 reads, etc.). Initially has no
#   policies attached -- attach as the agents start calling AWS services.

data "aws_caller_identity" "current" {}
data "aws_region" "current" {}

resource "aws_iam_role" "execution" {
  name = "${local.name}-ecs-exec"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

resource "aws_iam_role_policy_attachment" "execution_managed" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

resource "aws_iam_role_policy" "execution_secrets" {
  name = "${local.name}-ecs-exec-secrets"
  role = aws_iam_role.execution.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["secretsmanager:GetSecretValue"]
      Resource = [
        aws_secretsmanager_secret.db.arn,
        aws_secretsmanager_secret.tavily.arn,
        aws_secretsmanager_secret.azure_openai.arn,
      ]
    }]
  })
}

resource "aws_iam_role" "task" {
  name = "${local.name}-ecs-task"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Principal = { Service = "ecs-tasks.amazonaws.com" }
      Action = "sts:AssumeRole"
    }]
  })
}

# Reserved for Phase 2 step 1 (Bedrock provider toggle):
# resource "aws_iam_role_policy" "task_bedrock" {
#   role = aws_iam_role.task.id
#   policy = jsonencode({
#     Version = "2012-10-17"
#     Statement = [{
#       Effect   = "Allow"
#       Action   = ["bedrock:InvokeModel", "bedrock:InvokeModelWithResponseStream"]
#       Resource = "*"
#     }]
#   })
# }
