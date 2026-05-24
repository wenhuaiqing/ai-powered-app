# One-shot seed task. Runs scripts/seed_all.py against the freshly
# provisioned RDS the first time, and on demand whenever the source CSVs
# change. Triggered manually via `aws ecs run-task` (see infra/README.md).
#
# Reuses the backend ECR image (the seed scripts are baked in alongside
# the FastAPI app under scripts/). When `var.seed_image_uri` is empty
# (the default), we default to the backend repo's :latest tag.

resource "aws_ecs_cluster" "main" {
  name = local.name
}

resource "aws_cloudwatch_log_group" "seed" {
  name              = "/aws/ecs/${local.name}/seed"
  retention_in_days = 30
}

locals {
  seed_image = var.seed_image_uri != "" ? var.seed_image_uri : "${aws_ecr_repository.backend.repository_url}:latest"
}

resource "aws_ecs_task_definition" "seed" {
  family                   = "${local.name}-seed"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "seed"
    image     = local.seed_image
    essential = true
    # Run from /app (where misc/ + scripts/ live), not /app/backend.
    workingDirectory = "/app"
    # ETL runs on backend startup instead (each Fargate task has its own
    # ephemeral filesystem, so a seed-side DuckDB write wouldn't be
    # visible to the backend task). Seed handles only the MySQL side.
    command = [
      "sh", "-c",
      "python scripts/migrate_mysql.py && python scripts/build_mysql.py"
    ]
    environment = [
      { name = "MYSQL_HOST",     value = aws_db_instance.mysql.address },
      { name = "MYSQL_PORT",     value = tostring(aws_db_instance.mysql.port) },
      { name = "MYSQL_USER",     value = var.db_username },
      { name = "MYSQL_DATABASE", value = var.db_name },
    ]
    secrets = [
      {
        name      = "MYSQL_PASSWORD"
        valueFrom = "${aws_secretsmanager_secret.db.arn}:password::"
      }
    ]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.seed.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "seed"
      }
    }
  }])
}
