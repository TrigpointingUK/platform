# Valkey ECS Service Deployment
module "valkey" {
  source = "../modules/valkey"

  project_name                  = var.project_name
  environment                   = "common"
  aws_region                    = var.aws_region
  vpc_id                        = aws_vpc.main.id
  ecs_cluster_id                = aws_ecs_cluster.main.id
  ecs_cluster_name              = aws_ecs_cluster.main.name
  ecs_task_execution_role_arn   = aws_iam_role.ecs_task_execution_role.arn
  ecs_task_role_arn             = aws_iam_role.ecs_task_role.arn
  private_subnet_ids            = aws_subnet.private[*].id
  valkey_security_group_id      = aws_security_group.valkey_ecs.id
  efs_security_group_id         = aws_security_group.efs_valkey.id
  service_discovery_service_arn = aws_service_discovery_service.valkey.arn

  # Resource allocation
  cpu               = 256
  memory            = 512
  valkey_cpu        = 128
  valkey_memory     = 300
  valkey_max_memory = "250mb"
  commander_cpu     = 128
  commander_memory  = 212

  # Scaling configuration
  desired_count    = 1
  min_capacity     = 1
  max_capacity     = 3
  cpu_target_value = 70

  # Logging
  log_retention_days = 7
}

# ALB Listener Rule for Redis Commander with OIDC Authentication
resource "aws_lb_listener_rule" "valkey_commander" {
  count        = var.enable_cloudflare_ssl ? 1 : 0
  listener_arn = aws_lb_listener.app_https[0].arn
  priority     = 150

  # Action 1: Authenticate users via OIDC (Auth0)
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

  # Action 2: Forward to target group
  action {
    type             = "forward"
    order            = 2
    target_group_arn = module.valkey.valkey_commander_target_group_arn
  }

  condition {
    host_header {
      values = ["cache.trigpointing.uk"]
    }
  }

  tags = {
    Name = "${var.project_name}-valkey-commander-rule"
  }

  depends_on = [aws_secretsmanager_secret_version.alb_oidc]
}