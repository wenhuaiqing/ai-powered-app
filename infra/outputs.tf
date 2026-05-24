output "region" {
  value = var.region
}

output "vpc_id" {
  value = aws_vpc.main.id
}

output "private_subnet_id_a" {
  value = aws_subnet.private[0].id
}

output "private_subnet_id_b" {
  value = aws_subnet.private[1].id
}

output "public_subnet_id_a" {
  value = aws_subnet.public[0].id
}

output "public_subnet_id_b" {
  value = aws_subnet.public[1].id
}

output "app_security_group_id" {
  value = aws_security_group.app.id
}

output "rds_endpoint" {
  value     = aws_db_instance.mysql.address
  sensitive = false
}

output "rds_port" {
  value = aws_db_instance.mysql.port
}

output "db_secret_arn" {
  value       = aws_secretsmanager_secret.db.arn
  description = "Inject as MYSQL_PASSWORD via ECS `secrets`."
}

output "ecs_cluster_name" {
  value = aws_ecs_cluster.main.name
}

output "seed_task_family" {
  value = aws_ecs_task_definition.seed.family
}

output "execution_role_arn" {
  value = aws_iam_role.execution.arn
}

output "task_role_arn" {
  value = aws_iam_role.task.arn
}

# ---- ALB + ECS service identifiers (consumed by the GitHub Action) ----

output "alb_dns_name" {
  value       = aws_lb.main.dns_name
  description = "Public URL of the deployed app. Paste into a browser after the first deploy completes."
}

output "ecr_backend_repository_url" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_frontend_repository_url" {
  value = aws_ecr_repository.frontend.repository_url
}

output "ecs_backend_service_name" {
  value = aws_ecs_service.backend.name
}

output "ecs_frontend_service_name" {
  value = aws_ecs_service.frontend.name
}

output "ecs_backend_task_family" {
  value = aws_ecs_task_definition.backend.family
}

output "ecs_frontend_task_family" {
  value = aws_ecs_task_definition.frontend.family
}

# ---- GitHub Actions OIDC ----

output "github_actions_role_arn" {
  value       = aws_iam_role.github_actions_deploy.arn
  description = "Paste into the AWS_DEPLOY_ROLE_ARN GitHub Actions variable."
}
