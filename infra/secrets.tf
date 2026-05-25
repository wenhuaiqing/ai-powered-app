# MySQL credentials live in Secrets Manager. The ECS task role is granted
# secretsmanager:GetSecretValue on this single ARN; ECS resolves it at task
# start and injects the password as an env var (see seed_task.tf).
#
# Stored as JSON {"username":..., "password":..., "host":..., "port":...,
# "dbname":...} so the app can read one secret instead of five env vars.

resource "random_password" "db" {
  length  = 32
  special = true
  # RDS rejects some symbols; keep the alphabet conservative.
  override_special = "_!#%-"
}

resource "aws_secretsmanager_secret" "db" {
  name        = "${local.name}/mysql"
  description = "MySQL credentials for ${local.name}"
  # Demo: zero-day recovery so terraform destroy + apply on the same day works.
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = var.db_username
    password = random_password.db.result
    host     = aws_db_instance.mysql.address
    port     = aws_db_instance.mysql.port
    dbname   = var.db_name
  })
}

# ---- Runtime secrets ----
# One Secrets Manager secret per credential so the task def can reference
# individual ARNs (cleaner than packing them into a single JSON blob).

resource "aws_secretsmanager_secret" "tavily" {
  name                    = "${local.name}/tavily-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "tavily" {
  secret_id     = aws_secretsmanager_secret.tavily.id
  secret_string = var.tavily_api_key
}

