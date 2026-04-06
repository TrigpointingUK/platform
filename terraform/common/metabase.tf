# Metabase data exploration platform
# Self-hosted on ECS Fargate, authenticated via ALB OIDC (Auth0)
# Connects to the analytics schema for data exploration

# Security Group for Metabase ECS tasks
resource "aws_security_group" "metabase_ecs" {
  name        = "${var.project_name}-metabase-ecs-tasks-sg"
  description = "Security group for Metabase ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 3000
    to_port         = 3000
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-metabase-ecs-tasks-sg"
  }
}

# Allow Metabase to connect to the PostgreSQL RDS instance
resource "aws_security_group_rule" "metabase_to_rds" {
  type                     = "ingress"
  from_port                = aws_db_instance.postgres.port
  to_port                  = aws_db_instance.postgres.port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.metabase_ecs.id
  description              = "Metabase ECS tasks to PostgreSQL RDS"
}

# Metabase ECS Service
module "metabase" {
  source = "../modules/metabase"

  project_name                = var.project_name
  environment                 = "common"
  aws_region                  = var.aws_region
  cpu                         = 512
  memory                      = 1024
  desired_count               = 1
  min_capacity                = 0
  max_capacity                = 1
  cpu_target_value            = 70
  ecs_cluster_id              = aws_ecs_cluster.main.id
  ecs_cluster_name            = aws_ecs_cluster.main.name
  ecs_task_execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  ecs_task_role_arn           = aws_iam_role.ecs_task_role.arn
  ecs_security_group_id       = aws_security_group.metabase_ecs.id
  private_subnet_ids          = aws_subnet.private[*].id
  target_group_arn            = aws_lb_target_group.metabase.arn
  mb_db_host                  = split(":", aws_db_instance.postgres.endpoint)[0]
  mb_db_port                  = aws_db_instance.postgres.port
  mb_db_dbname                = "metabase"
  mb_db_user                  = local.metabase_credentials.username
  mb_db_pass                  = local.metabase_credentials.password

  depends_on = [aws_lb_listener_rule.metabase]
}

# Fetch Metabase credentials from Secrets Manager
data "aws_secretsmanager_secret" "metabase_credentials" {
  name = "metabase-production-postgres-credentials"
}

data "aws_secretsmanager_secret_version" "metabase_credentials" {
  secret_id = data.aws_secretsmanager_secret.metabase_credentials.id
}

locals {
  metabase_credentials = jsondecode(data.aws_secretsmanager_secret_version.metabase_credentials.secret_string)
}

# Target Group for Metabase
resource "aws_lb_target_group" "metabase" {
  name        = "${var.project_name}-metabase-ecs-tg"
  port        = 3000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/api/health"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.project_name}-metabase-ecs-tg"
  }
}

# Listener rule for Metabase (production) with OIDC Authentication
resource "aws_lb_listener_rule" "metabase" {
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 127

  action {
    type  = "authenticate-oidc"
    order = 1

    authenticate_oidc {
      issuer                              = local.alb_oidc_config.issuer
      authorization_endpoint              = local.alb_oidc_config.authorization_endpoint
      token_endpoint                      = local.alb_oidc_config.token_endpoint
      user_info_endpoint                  = local.alb_oidc_config.user_info_endpoint
      client_id                           = local.alb_oidc_config.client_id
      client_secret                       = local.alb_oidc_config.client_secret
      session_cookie_name                 = "AWSELBAuthSessionCookie"
      session_timeout                     = 3600
      scope                               = "openid profile email"
      on_unauthenticated_request          = "authenticate"
      authentication_request_extra_params = {}
    }
  }

  action {
    type             = "forward"
    order            = 2
    target_group_arn = aws_lb_target_group.metabase.arn
  }

  condition {
    host_header {
      values = ["data.trigpointing.uk"]
    }
  }

  tags = {
    Name = "${var.project_name}-metabase-listener-rule"
  }

  depends_on = [aws_secretsmanager_secret_version.alb_oidc]
}

# Listener rule for Metabase (staging) with OIDC Authentication
resource "aws_lb_listener_rule" "metabase_staging" {
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 128

  action {
    type  = "authenticate-oidc"
    order = 1

    authenticate_oidc {
      issuer                              = local.alb_oidc_config.issuer
      authorization_endpoint              = local.alb_oidc_config.authorization_endpoint
      token_endpoint                      = local.alb_oidc_config.token_endpoint
      user_info_endpoint                  = local.alb_oidc_config.user_info_endpoint
      client_id                           = local.alb_oidc_config.client_id
      client_secret                       = local.alb_oidc_config.client_secret
      session_cookie_name                 = "AWSELBAuthSessionCookie"
      session_timeout                     = 3600
      scope                               = "openid profile email"
      on_unauthenticated_request          = "authenticate"
      authentication_request_extra_params = {}
    }
  }

  action {
    type             = "forward"
    order            = 2
    target_group_arn = aws_lb_target_group.metabase.arn
  }

  condition {
    host_header {
      values = ["data.trigpointing.me"]
    }
  }

  tags = {
    Name = "${var.project_name}-metabase-staging-listener-rule"
  }

  depends_on = [aws_secretsmanager_secret_version.alb_oidc]
}
