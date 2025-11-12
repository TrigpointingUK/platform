# SPA ECS Service for Production Environment
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
# Production: serves on preview.trigpointing.uk subdomain for smoke testing
# Main trigpointing.uk domain continues to serve legacy site
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
  alb_rule_priority    = 55 # After API priority (200) but before legacy
  host_headers         = ["preview.trigpointing.uk"]
  path_patterns        = null  # Match all paths (serves from root like staging)
  create_listener_rule = false # Create custom rule with OIDC auth below

  # Container Configuration
  image_uri = var.spa_container_image

  # Resource Allocation
  cpu    = 256
  memory = 512

  # Scaling
  desired_count    = 1
  min_capacity     = 1
  max_capacity     = 10
  cpu_target_value = 70
}

# Custom ALB Listener Rule with OIDC Authentication for preview.trigpointing.uk
# Protected by Auth0 with api-admin role requirement (same as cache and phpmyadmin)
resource "aws_lb_listener_rule" "spa_preview" {
  listener_arn = data.terraform_remote_state.common.outputs.https_listener_arn
  priority     = 55 # Same priority as configured in module

  # Action 1: Authenticate users via OIDC (Auth0)
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
      values = ["preview.trigpointing.uk"]
    }
  }

  tags = {
    Name = "${var.project_name}-spa-preview-listener-rule"
  }

  depends_on = [data.terraform_remote_state.common]
}

