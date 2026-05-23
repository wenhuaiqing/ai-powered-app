# db.t4g.micro MySQL 8 in the private subnets. No public access, no inbound
# rules from outside the VPC. The seed task (and later the backend service)
# reach it via the application security group.

resource "aws_db_subnet_group" "mysql" {
  name       = "${local.name}-mysql"
  subnet_ids = aws_subnet.private[*].id
  tags = { Name = "${local.name}-mysql-subnet-group" }
}

resource "aws_security_group" "mysql" {
  name        = "${local.name}-mysql-sg"
  description = "MySQL — inbound from app SG only"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port       = 3306
    to_port         = 3306
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
    description     = "App tasks -> MySQL"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-mysql-sg" }
}

resource "aws_db_instance" "mysql" {
  identifier             = "${local.name}-mysql"
  engine                 = "mysql"
  engine_version         = var.db_engine_version
  instance_class         = var.db_instance_class
  allocated_storage      = var.db_allocated_storage_gb
  storage_type           = "gp3"
  db_name                = var.db_name
  username               = var.db_username
  password               = random_password.db.result
  db_subnet_group_name   = aws_db_subnet_group.mysql.name
  vpc_security_group_ids = [aws_security_group.mysql.id]
  publicly_accessible    = false
  multi_az               = false
  backup_retention_period = 7
  deletion_protection    = false   # demo
  skip_final_snapshot    = true    # demo
  apply_immediately      = true
  storage_encrypted      = true
  parameter_group_name   = aws_db_parameter_group.mysql.name

  tags = { Name = "${local.name}-mysql" }
}

# Force utf8mb4 + slow-query log for parity with the docker-compose dev DB.
resource "aws_db_parameter_group" "mysql" {
  name        = "${local.name}-mysql"
  family      = "mysql8.0"
  description = "${local.name} MySQL 8 parameters"

  parameter {
    name  = "character_set_server"
    value = "utf8mb4"
  }
  parameter {
    name  = "collation_server"
    value = "utf8mb4_unicode_ci"
  }
  parameter {
    name  = "slow_query_log"
    value = "1"
  }
  parameter {
    name  = "long_query_time"
    value = "1"
  }
}
