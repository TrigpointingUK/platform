# phpBB ECS Service wiring (common)

# AWS Secrets Manager secret for phpBB application secrets
resource "aws_secretsmanager_secret" "phpbb_app_secrets" {
  name        = "${var.project_name}-phpbb-app-secrets"
  description = "Application secrets for phpBB (config values, keys, etc.)"

  lifecycle {
    ignore_changes = [
      # Ignore changes to the secret value - managed manually
    ]
  }

  tags = {
    Name = "${var.project_name}-phpbb-app-secrets"
  }
}

# Initial secret version with empty placeholder
# This will be ignored after initial creation - populate manually as needed
resource "aws_secretsmanager_secret_version" "phpbb_app_secrets" {
  secret_id = aws_secretsmanager_secret.phpbb_app_secrets.id
  secret_string = jsonencode({
    # Add your phpBB application secrets here manually
    # Example keys you might need:
    # PHPBB_COOKIE_SECURE = "true"
    # PHPBB_SMTP_HOST = "..."
    # etc.
  })

  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Security Group for phpBB ECS tasks
resource "aws_security_group" "phpbb_ecs" {
  name        = "${var.project_name}-phpbb-ecs-tasks-sg"
  description = "Security group for phpBB ECS tasks"
  vpc_id      = aws_vpc.main.id

  # Ingress from ALB on HTTP
  ingress {
    description     = "HTTP from ALB"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.alb.id]
  }

  # Ingress from Bastion for debugging
  ingress {
    description     = "HTTP from Bastion"
    from_port       = 80
    to_port         = 80
    protocol        = "tcp"
    security_groups = [aws_security_group.bastion.id]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = {
    Name = "${var.project_name}-phpbb-ecs-tasks-sg"
  }
}

# Allow NFS access from phpBB ECS tasks to EFS
## NFS ingress for phpBB ECS tasks is defined inline in aws_security_group.efs

## Allow ECS task execution role to read phpBB DB secret
resource "aws_iam_role_policy" "ecs_phpbb_secrets" {
  name = "${var.project_name}-ecs-phpbb-secrets"
  role = aws_iam_role.ecs_task_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "secretsmanager:GetSecretValue"
        ],
        Resource = [
          var.phpbb_db_credentials_arn,
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:trigpointing-phpbb-credentials*",
          aws_secretsmanager_secret.phpbb_app_secrets.arn,
        ]
      }
    ]
  })
}

module "phpbb" {
  source = "../modules/phpbb"

  project_name                = var.project_name
  environment                 = "common"
  aws_region                  = var.aws_region
  cpu                         = 256
  memory                      = 512
  desired_count               = 1
  min_capacity                = 1
  max_capacity                = 3
  cpu_target_value            = 70
  memory_target_value         = 80
  ecs_cluster_id              = aws_ecs_cluster.main.id
  ecs_cluster_name            = aws_ecs_cluster.main.name
  ecs_task_execution_role_arn = aws_iam_role.ecs_task_execution_role.arn
  ecs_task_role_arn           = aws_iam_role.ecs_task_role.arn
  ecs_security_group_id       = aws_security_group.phpbb_ecs.id
  private_subnet_ids          = aws_subnet.private[*].id
  target_group_arn            = aws_lb_target_group.phpbb.arn
  image_uri                   = "ghcr.io/trigpointinguk/platform/forum:main"

  # Database config
  db_credentials_arn = var.phpbb_db_credentials_arn
  db_host            = split(":", aws_db_instance.main.endpoint)[0]
  db_name            = "phpbb_db"
  db_user            = "phpbb_user"
  table_prefix       = "phpbb_"

  # Secrets config
  phpbb_secrets_arn = aws_secretsmanager_secret.phpbb_app_secrets.arn

  # EFS config
  efs_file_system_id  = aws_efs_file_system.phpbb.id
  efs_access_point_id = aws_efs_access_point.phpbb.id
}

resource "aws_lb_listener_rule" "forum" {
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 120

  action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.phpbb.arn
  }

  condition {
    host_header {
      values = ["forum.trigpointing.uk"]
    }
  }

  tags = {
    Name = "${var.project_name}-forum-listener-rule"
  }
}
