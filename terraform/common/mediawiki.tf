# MediaWiki database schema is created in terraform/mysql/
# See terraform/mysql/rds-schemas.tf for database and user configuration

# AWS Secrets Manager secret for MediaWiki application secrets
resource "aws_secretsmanager_secret" "mediawiki_app_secrets" {
  name        = "${var.project_name}-mediawiki-app-secrets"
  description = "Application secrets for MediaWiki (keys, OIDC config, etc.)"

  lifecycle {
    ignore_changes = [
      # Ignore changes to the secret value - managed manually
    ]
  }

  tags = {
    Name = "${var.project_name}-mediawiki-app-secrets"
  }
}

# Initial secret version with placeholder values
# This will be ignored after initial creation - populate manually
resource "aws_secretsmanager_secret_version" "mediawiki_app_secrets" {
  secret_id = aws_secretsmanager_secret.mediawiki_app_secrets.id
  secret_string = jsonencode({
    MW_SITENAME           = "TrigpointingUK Wiki"
    MW_SERVER             = "https://wiki.trigpointing.uk"
    MW_SECRET_KEY         = "CHANGE-ME-random-64-char-hex-string"
    MW_UPGRADE_KEY        = "CHANGE-ME-random-16-char-string"
    CACHE_TLS             = "true"
    MW_ENABLE_LOCAL_LOGIN = "false"
    OIDC_PROVIDER_URL     = "https://YOUR-AUTH0-DOMAIN.auth0.com"
    OIDC_CLIENT_ID        = "YOUR-AUTH0-CLIENT-ID"
    OIDC_CLIENT_SECRET    = "YOUR-AUTH0-CLIENT-SECRET"
    OIDC_REDIRECT_URI     = "https://wiki.trigpointing.uk/wiki/Special:PluggableAuthLogin"
    SMTP_USERNAME         = "POPULATE-FROM-TERRAFORM-OUTPUT-mediawiki_smtp_username"
    SMTP_PASSWORD         = "POPULATE-FROM-TERRAFORM-OUTPUT-mediawiki_smtp_password"
  })

  lifecycle {
    ignore_changes = [
      secret_string,
    ]
  }
}

# IAM policy to allow ECS task execution role to read MediaWiki secrets
resource "aws_iam_role_policy" "ecs_mediawiki_secrets" {
  name = "${var.project_name}-ecs-mediawiki-secrets"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "secretsmanager:GetSecretValue"
        ]
        Resource = [
          aws_secretsmanager_secret.mediawiki_app_secrets.arn,
          var.mediawiki_db_credentials_arn
        ]
      }
    ]
  })
}

# Security Group for MediaWiki ECS tasks
resource "aws_security_group" "mediawiki_ecs" {
  name        = "${var.project_name}-mediawiki-ecs-tasks-sg"
  description = "Security group for MediaWiki ECS tasks"
  vpc_id      = aws_vpc.main.id

  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
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
    Name = "${var.project_name}-mediawiki-ecs-tasks-sg"
  }
}

# Add MySQL access from MediaWiki ECS tasks to RDS security group
resource "aws_security_group_rule" "rds_from_mediawiki_ecs" {
  type                     = "ingress"
  description              = "MySQL from MediaWiki ECS tasks"
  from_port                = 3306
  to_port                  = 3306
  protocol                 = "tcp"
  security_group_id        = aws_security_group.rds.id
  source_security_group_id = aws_security_group.mediawiki_ecs.id
}

# Target Group for MediaWiki
resource "aws_lb_target_group" "mediawiki" {
  name        = "${var.project_name}-mediawiki-ecs-tg"
  port        = 80
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    enabled             = true
    healthy_threshold   = 2
    interval            = 30
    matcher             = "200"
    path                = "/api.php?action=query&meta=siteinfo&format=json"
    port                = "traffic-port"
    protocol            = "HTTP"
    timeout             = 5
    unhealthy_threshold = 3
  }

  tags = {
    Name = "${var.project_name}-mediawiki-ecs-tg"
  }
}

# Update the existing wiki listener rule to point to MediaWiki ECS service
# This replaces the existing rule in webserver-target-group.tf
resource "aws_lb_listener_rule" "mediawiki" {
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 124

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.mediawiki.arn
  }

  condition {
    host_header {
      values = ["wiki.trigpointing.uk"]
    }
  }

  tags = {
    Name = "${var.project_name}-mediawiki-listener-rule"
  }
}

# MediaWiki ECS Service
module "mediawiki" {
  source = "../modules/mediawiki"

  project_name                 = var.project_name
  environment                  = "common"
  aws_region                   = var.aws_region
  cpu                          = 256
  memory                       = 512
  desired_count                = 1
  min_capacity                 = 1
  max_capacity                 = 3
  cpu_target_value             = 70
  memory_target_value          = 80
  ecs_cluster_id               = aws_ecs_cluster.main.id
  ecs_cluster_name             = aws_ecs_cluster.main.name
  ecs_task_execution_role_arn  = aws_iam_role.ecs_task_execution_role.arn
  ecs_task_execution_role_name = aws_iam_role.ecs_task_execution_role.name
  ecs_task_role_arn            = aws_iam_role.ecs_task_role.arn
  ecs_task_role_name           = aws_iam_role.ecs_task_role.name
  ecs_security_group_id        = aws_security_group.mediawiki_ecs.id
  private_subnet_ids           = aws_subnet.private[*].id
  target_group_arn             = aws_lb_target_group.mediawiki.arn
  cloudwatch_log_group_name    = "/aws/ecs/${var.project_name}-mediawiki-common"
  image_uri                    = "ghcr.io/trigpointinguk/platform/wiki:main"
  cache_host                   = module.valkey.valkey_endpoint
  cache_port                   = module.valkey.valkey_port
  mediawiki_db_credentials_arn = var.mediawiki_db_credentials_arn
  mediawiki_app_secrets_arn    = aws_secretsmanager_secret.mediawiki_app_secrets.arn
  efs_file_system_id           = aws_efs_file_system.mediawiki.id
  efs_access_point_id          = aws_efs_access_point.mediawiki.id
  efs_access_point_arn         = aws_efs_access_point.mediawiki.arn

  depends_on = [aws_lb_listener_rule.mediawiki, module.valkey]
}
