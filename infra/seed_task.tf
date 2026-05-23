# One-shot seed task. Runs scripts/seed_all.py against the freshly
# provisioned RDS the first time, and on demand whenever the source CSVs
# change. Triggered manually via `aws ecs run-task` (see infra/README.md).
#
# The task definition references var.seed_image_uri. Until Phase 2 step 2
# publishes the backend image to ECR, this remains an empty string and
# the task definition is skipped (count = 0). Apply this whole module
# first to stand up the database; revisit once an image exists.

resource "aws_ecs_cluster" "main" {
  name = local.name
}

resource "aws_cloudwatch_log_group" "seed" {
  name              = "/aws/ecs/${local.name}/seed"
  retention_in_days = 30
}

resource "aws_ecs_task_definition" "seed" {
  count                    = var.seed_image_uri == "" ? 0 : 1
  family                   = "${local.name}-seed"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "seed"
    image     = var.seed_image_uri
    essential = true
    command   = ["python", "scripts/seed_all.py"]
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
