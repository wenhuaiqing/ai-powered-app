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
  value       = try(aws_ecs_task_definition.seed[0].family, "")
  description = "Empty until var.seed_image_uri is set (after Phase 2 step 2)."
}

output "execution_role_arn" {
  value = aws_iam_role.execution.arn
}

output "task_role_arn" {
  value = aws_iam_role.task.arn
}
