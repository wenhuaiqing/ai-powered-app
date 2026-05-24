# Application Load Balancer.
#
# Single ALB in the public subnets. One listener on :80 (HTTP). Two
# target groups -- one per service. Path-based routing:
#   /api/*, /orb/*, /health  -> backend target group
#   everything else          -> frontend target group (catches /)
#
# Production posture would add an HTTPS listener with an ACM cert, HTTP->
# HTTPS redirect, and WAF in front. Skipped here for demo cost; trivial
# to add once a custom domain is wired up.

resource "aws_security_group" "alb" {
  name        = "${local.name}-alb-sg"
  description = "Public ALB -- HTTP inbound"
  vpc_id      = aws_vpc.main.id

  ingress {
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
    description = "HTTP from anywhere"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = { Name = "${local.name}-alb-sg" }
}

# Allow the ALB to reach the Fargate tasks on each service's port. The
# app SG already permits all egress; this rule is the inbound complement.
resource "aws_security_group_rule" "app_ingress_from_alb_backend" {
  type                     = "ingress"
  from_port                = 8000
  to_port                  = 8000
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.app.id
  description              = "ALB to backend tasks"
}

resource "aws_security_group_rule" "app_ingress_from_alb_frontend" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = aws_security_group.alb.id
  security_group_id        = aws_security_group.app.id
  description              = "ALB to frontend tasks (nginx)"
}

resource "aws_lb" "main" {
  name               = substr("${local.name}-alb", 0, 32)
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id

  enable_deletion_protection = false  # demo
  idle_timeout               = 180     # match SSE proxy_read_timeout

  tags = { Name = "${local.name}-alb" }
}

resource "aws_lb_target_group" "backend" {
  name        = substr("${local.name}-be", 0, 32)
  port        = 8000
  protocol    = "HTTP"
  target_type = "ip"   # Fargate tasks are IPs, not instances
  vpc_id      = aws_vpc.main.id

  health_check {
    enabled             = true
    path                = "/health"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }

  # Allows ECS to drain in-flight SSE streams before killing a task.
  deregistration_delay = 30
}

resource "aws_lb_target_group" "frontend" {
  name        = substr("${local.name}-fe", 0, 32)
  port        = 80
  protocol    = "HTTP"
  target_type = "ip"
  vpc_id      = aws_vpc.main.id

  health_check {
    enabled             = true
    path                = "/"
    protocol            = "HTTP"
    matcher             = "200"
    interval            = 15
    timeout             = 5
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  # Default: send everything to the frontend (catches /, /properties,
  # /pipeline, etc. -- the SPA). Specific paths get peeled off below.
  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.frontend.arn
  }
}

# Backend takes /api/*, /orb/*, and exact /health. Higher priority means
# it's evaluated before the listener default.
resource "aws_lb_listener_rule" "backend_paths" {
  listener_arn = aws_lb_listener.http.arn
  priority     = 10

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }

  condition {
    path_pattern {
      values = ["/api/*", "/orb/*", "/health"]
    }
  }
}
