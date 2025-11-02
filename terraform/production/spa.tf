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
  alb_listener_arn  = data.terraform_remote_state.common.outputs.https_listener_arn
  alb_rule_priority = 55 # After API priority (200) but before legacy
  host_headers      = ["preview.trigpointing.uk"]
  path_patterns     = null # Match all paths (serves from root like staging)

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

