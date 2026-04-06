# Hasura GraphQL engine for third-party developer API
# Self-hosted on ECS Fargate, with split ALB routing:
#   - /v1/* endpoints: JWT passthrough (Hasura validates tokens)
#   - Console (everything else): OIDC authenticated via Auth0

# Security Group for Hasura ECS tasks
resource "aws_security_group" "hasura_ecs" {
  name        = "${var.project_name}-hasura-ecs-tasks-sg"
  description = "Security group for Hasura ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 8080
    to_port         = 8080
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
    Name = "${var.project_name}-hasura-ecs-tasks-sg"
  }
}

# Allow Hasura to connect to the PostgreSQL RDS instance
resource "aws_security_group_rule" "hasura_to_rds" {
  type                     = "ingress"
  from_port                = aws_db_instance.postgres.port
  to_port                  = aws_db_instance.postgres.port
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.hasura_ecs.id
  description              = "Hasura ECS tasks to PostgreSQL RDS"
}

# Fetch Hasura credentials from Secrets Manager
data "aws_secretsmanager_secret" "hasura_credentials" {
  name = "hasura-production-postgres-credentials"
}

data "aws_secretsmanager_secret_version" "hasura_credentials" {
  secret_id = data.aws_secretsmanager_secret.hasura_credentials.id
}

locals {
  hasura_credentials = jsondecode(data.aws_secretsmanager_secret_version.hasura_credentials.secret_string)
  hasura_rds_host    = split(":", aws_db_instance.postgres.endpoint)[0]
  hasura_rds_port    = aws_db_instance.postgres.port

  hasura_database_url = "postgres://${local.hasura_credentials.username}:${local.hasura_credentials.password}@${local.hasura_rds_host}:${local.hasura_rds_port}/${local.hasura_credentials.dbname}?options=-c%%20search_path%%3Danalytics"
  hasura_metadata_url = "postgres://${local.hasura_credentials.username}:${local.hasura_credentials.password}@${local.hasura_rds_host}:${local.hasura_rds_port}/hasura"

  hasura_jwt_secret = jsonencode({
    type    = "RS256"
    jwk_url = "https://auth.trigpointing.uk/.well-known/jwks.json"
    issuer  = "https://auth.trigpointing.uk/"
    claims_map = {
      "x-hasura-default-role"  = { "default" = "user" }
      "x-hasura-allowed-roles" = { "default" = ["user", "anonymous"] }
      "x-hasura-user-id"       = { "path" = "$$.sub" }
    }
  })
}

# Admin secret for Hasura console and metadata API
resource "random_password" "hasura_admin_secret" {
  length  = 32
  special = false
}

# Hasura ECS Service
module "hasura" {
  source = "../modules/hasura"

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
  ecs_security_group_id       = aws_security_group.hasura_ecs.id
  private_subnet_ids          = aws_subnet.private[*].id
  target_group_arn            = aws_lb_target_group.hasura.arn
  metadata_database_url       = local.hasura_metadata_url
  database_url                = local.hasura_database_url
  admin_secret                = random_password.hasura_admin_secret.result
  jwt_secret                  = local.hasura_jwt_secret

  depends_on = [aws_lb_listener_rule.hasura_api]
}

# Target Group for Hasura
resource "aws_lb_target_group" "hasura" {
  name        = "${var.project_name}-hasura-ecs-tg"
  port        = 8080
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/healthz"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 10
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.project_name}-hasura-ecs-tg"
  }
}

# --- Production listener rules ---

# Rule A: API endpoints - JWT passthrough (Hasura validates tokens itself)
resource "aws_lb_listener_rule" "hasura_api" {
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 118

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.hasura.arn
  }

  condition {
    host_header {
      values = ["graphql.trigpointing.uk"]
    }
  }

  condition {
    path_pattern {
      values = ["/v1/*", "/healthz"]
    }
  }

  tags = {
    Name = "${var.project_name}-hasura-api-listener-rule"
  }
}

# Rule B: Console - OIDC authenticated (for admin/developer browser access)
resource "aws_lb_listener_rule" "hasura_console" {
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 119

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
    target_group_arn = aws_lb_target_group.hasura.arn
  }

  condition {
    host_header {
      values = ["graphql.trigpointing.uk"]
    }
  }

  tags = {
    Name = "${var.project_name}-hasura-console-listener-rule"
  }

  depends_on = [aws_secretsmanager_secret_version.alb_oidc]
}

# --- Staging listener rules ---

# Rule A: API endpoints - JWT passthrough
resource "aws_lb_listener_rule" "hasura_api_staging" {
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 116

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.hasura.arn
  }

  condition {
    host_header {
      values = ["graphql.trigpointing.me"]
    }
  }

  condition {
    path_pattern {
      values = ["/v1/*", "/healthz"]
    }
  }

  tags = {
    Name = "${var.project_name}-hasura-api-staging-listener-rule"
  }
}

# Rule B: Console - OIDC authenticated
resource "aws_lb_listener_rule" "hasura_console_staging" {
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 117

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
    target_group_arn = aws_lb_target_group.hasura.arn
  }

  condition {
    host_header {
      values = ["graphql.trigpointing.me"]
    }
  }

  tags = {
    Name = "${var.project_name}-hasura-console-staging-listener-rule"
  }

  depends_on = [aws_secretsmanager_secret_version.alb_oidc]
}

# --- Cloudflare DNS ---

resource "cloudflare_dns_record" "hasura_production" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "graphql"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true
  ttl     = 1

  comment = "Hasura GraphQL developer API for TrigpointingUK - managed by Terraform"
}

resource "cloudflare_dns_record" "hasura_staging" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "graphql"
  content = aws_lb.main.dns_name
  type    = "CNAME"
  proxied = true
  ttl     = 1

  comment = "Hasura GraphQL developer API for TrigpointingUK staging - managed by Terraform"
}
