# SPA ECS Service for Staging Environment
# CloudWatch log group is created by the spa-ecs-service module

# Allow ALB to reach SPA on port 80
resource "aws_security_group_rule" "spa_from_alb" {
  type                     = "ingress"
  from_port                = 80
  to_port                  = 80
  protocol                 = "tcp"
  source_security_group_id = data.terraform_remote_state.common.outputs.alb_security_group_id
  security_group_id        = module.cloudflare.ecs_security_group_id
  description              = "HTTP from ALB to SPA"
}

# Deploy SPA ECS Service
# Staging: serves from root (/) - no path pattern restriction
# Protected by Auth0 OIDC via production tenant (requires api-admin role)
module "spa_ecs_service" {
  source = "../modules/spa-ecs-service"

  project_name = var.project_name
  environment  = var.environment
  aws_region   = var.aws_region

  # Networking
  vpc_id             = data.terraform_remote_state.common.outputs.vpc_id
  private_subnet_ids = data.terraform_remote_state.common.outputs.private_subnet_ids

  # ECS Configuration
  ecs_cluster_id              = data.terraform_remote_state.common.outputs.ecs_cluster_id
  ecs_cluster_name            = data.terraform_remote_state.common.outputs.ecs_cluster_name
  ecs_task_execution_role_arn = data.terraform_remote_state.common.outputs.ecs_task_execution_role_arn
  ecs_task_role_arn           = data.terraform_remote_state.common.outputs.ecs_task_role_arn
  ecs_security_group_id       = module.cloudflare.ecs_security_group_id

  # ALB Configuration
  alb_listener_arn     = data.terraform_remote_state.common.outputs.https_listener_arn
  alb_rule_priority    = 50 # High priority - serves all paths on trigpointing.me
  host_headers         = ["trigpointing.me"]
  path_patterns        = null  # Match all paths (serves from root)
  create_listener_rule = false # Create custom rule with OIDC auth below

  # Container Configuration
  image_uri = var.spa_container_image

  # Resource Allocation
  cpu    = 256
  memory = 512

  # Scaling
  desired_count    = 1
  min_capacity     = 1
  max_capacity     = 2 # Reduced for staging
  cpu_target_value = 70
}

# Custom ALB Listener Rule with OIDC Authentication for trigpointing.me
# Protected by Auth0 (production tenant) with api-admin role requirement
# Uses the same OIDC config as cache.trigpointing.uk and preview.trigpointing.uk
resource "aws_lb_listener_rule" "spa_staging_oidc" {
  listener_arn = data.terraform_remote_state.common.outputs.https_listener_arn
  priority     = 50 # Same priority as configured in module

  # Action 1: Authenticate users via OIDC (Auth0 production tenant)
  action {
    type  = "authenticate-oidc"
    order = 1

    authenticate_oidc {
      issuer                              = data.terraform_remote_state.common.outputs.alb_oidc_config.issuer
      authorization_endpoint              = data.terraform_remote_state.common.outputs.alb_oidc_config.authorization_endpoint
      token_endpoint                      = data.terraform_remote_state.common.outputs.alb_oidc_config.token_endpoint
      user_info_endpoint                  = data.terraform_remote_state.common.outputs.alb_oidc_config.user_info_endpoint
      client_id                           = data.terraform_remote_state.common.outputs.alb_oidc_config.client_id
      client_secret                       = data.terraform_remote_state.common.outputs.alb_oidc_config.client_secret
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
    target_group_arn = module.spa_ecs_service.target_group_arn
  }

  condition {
    host_header {
      values = ["trigpointing.me"]
    }
  }

  tags = {
    Name = "${var.project_name}-spa-staging-listener-rule"
  }

  depends_on = [data.terraform_remote_state.common]
}

