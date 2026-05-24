# Long-running ECS services for backend + frontend. Both Fargate, in
# the private subnets. ALB target groups are wired here; container
# definitions reference the secret + non-secret env vars the app needs.
#
# Initial image tag is `latest` -- GitHub Actions overrides this on
# every deploy by registering a new task definition revision with the
# fresh image URI.

resource "aws_cloudwatch_log_group" "backend" {
  name              = "/aws/ecs/${local.name}/backend"
  retention_in_days = 30
}

resource "aws_cloudwatch_log_group" "frontend" {
  name              = "/aws/ecs/${local.name}/frontend"
  retention_in_days = 30
}

# Bedrock invocation policy attached to the task role -- only the backend
# uses it, but they share the same task role here for simplicity. Scoped
# to bedrock-runtime actions only.
resource "aws_iam_role_policy" "task_bedrock" {
  name = "${local.name}-task-bedrock"
  role = aws_iam_role.task.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect   = "Allow"
      Action   = [
        "bedrock:InvokeModel",
        "bedrock:InvokeModelWithResponseStream",
        "bedrock:Converse",
        "bedrock:ConverseStream",
      ]
      Resource = "*"
    }]
  })
}

# ---- Backend task definition ----
resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name}-backend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "512"
  memory                   = "1024"
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = "backend"
    image     = "${aws_ecr_repository.backend.repository_url}:latest"
    essential = true
    portMappings = [{
      containerPort = 8000
      hostPort      = 8000
      protocol      = "tcp"
    }]
    environment = [
      { name = "LLM_PROVIDER",             value = "bedrock" },
      { name = "AWS_REGION",               value = var.region },
      { name = "MYSQL_HOST",               value = aws_db_instance.mysql.address },
      { name = "MYSQL_PORT",               value = tostring(aws_db_instance.mysql.port) },
      { name = "MYSQL_USER",               value = var.db_username },
      { name = "MYSQL_DATABASE",           value = var.db_name },
      { name = "CORS_ORIGINS",             value = "http://${aws_lb.main.dns_name}" },
      # Azure OpenAI URL + embed model name (the API key is a secret).
      # Embeddings always go via Azure regardless of LLM_PROVIDER --
      # the RAG parquets were built with text-embedding-3-small.
      { name = "AZURE_OPENAI_ENDPOINT",    value = var.azure_openai_endpoint },
      { name = "AZURE_OPENAI_EMBED_MODEL", value = var.azure_openai_embed_model },
    ]
    secrets = [
      { name = "MYSQL_PASSWORD",         valueFrom = "${aws_secretsmanager_secret.db.arn}:password::" },
      { name = "TAVILY_API_KEY",         valueFrom = aws_secretsmanager_secret.tavily.arn },
      { name = "AZURE_OPENAI_API_KEY",   valueFrom = aws_secretsmanager_secret.azure_openai.arn },
    ]
    healthCheck = {
      command     = ["CMD-SHELL", "python -c \"import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2).status==200 else 1)\""]
      interval    = 15
      timeout     = 5
      retries     = 4
      # Backend boots by running the MySQL -> DuckDB ETL before uvicorn
      # starts; gives that ~60s of grace before health checks fail.
      startPeriod = 90
    }
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.backend.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "backend"
      }
    }
  }])
}

resource "aws_ecs_service" "backend" {
  name            = "${local.name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 8000
  }

  # Ignore task_definition drift: the GitHub Actions deploy updates the
  # service to a new revision, and we don't want `terraform apply` to
  # roll it back to whatever's in state.
  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.http]
}

# ---- Frontend task definition ----
resource "aws_ecs_task_definition" "frontend" {
  family                   = "${local.name}-frontend"
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = "256"
  memory                   = "512"
  execution_role_arn       = aws_iam_role.execution.arn

  container_definitions = jsonencode([{
    name      = "frontend"
    image     = "${aws_ecr_repository.frontend.repository_url}:latest"
    essential = true
    portMappings = [{
      containerPort = 80
      hostPort      = 80
      protocol      = "tcp"
    }]
    logConfiguration = {
      logDriver = "awslogs"
      options = {
        awslogs-group         = aws_cloudwatch_log_group.frontend.name
        awslogs-region        = data.aws_region.current.name
        awslogs-stream-prefix = "frontend"
      }
    }
  }])
}

resource "aws_ecs_service" "frontend" {
  name            = "${local.name}-frontend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.frontend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = aws_subnet.private[*].id
    security_groups  = [aws_security_group.app.id]
    assign_public_ip = false
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.frontend.arn
    container_name   = "frontend"
    container_port   = 80
  }

  lifecycle {
    ignore_changes = [task_definition, desired_count]
  }

  depends_on = [aws_lb_listener.http]
}
