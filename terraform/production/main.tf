resource "aws_cloudwatch_log_group" "app" {
  name              = "/ecs/${var.project_name}-${var.environment}"
  retention_in_days = 7

  tags = {
    Name = "${var.project_name}-${var.environment}-logs"
  }
}

module "cloudflare" {
  source = "../modules/cloudflare"

  project_name          = var.project_name
  environment           = var.environment
  vpc_id                = data.terraform_remote_state.common.outputs.vpc_id
  enable_cloudflare_ssl = var.enable_cloudflare_ssl
  alb_security_group_id = data.terraform_remote_state.common.outputs.alb_security_group_id
}

# Allow FastAPI ECS tasks to access Valkey
resource "aws_security_group_rule" "fastapi_to_valkey" {
  type                     = "ingress"
  from_port                = 6379
  to_port                  = 6379
  protocol                 = "tcp"
  source_security_group_id = module.cloudflare.ecs_security_group_id
  security_group_id        = data.terraform_remote_state.common.outputs.valkey_security_group_id
  description              = "Valkey from FastAPI ${var.environment} ECS tasks"
}

# Allow FastAPI ECS tasks to access Tiles EFS
resource "aws_security_group_rule" "fastapi_to_tiles_efs" {
  type                     = "ingress"
  from_port                = 2049
  to_port                  = 2049
  protocol                 = "tcp"
  source_security_group_id = module.cloudflare.ecs_security_group_id
  security_group_id        = data.terraform_remote_state.common.outputs.tiles_efs_security_group_id
  description              = "NFS from FastAPI ${var.environment} ECS tasks"
}

# ElastiCache security group rule (COMMENTED OUT - ElastiCache removed)
# resource "aws_security_group_rule" "fastapi_to_elasticache" {
#   type                     = "ingress"
#   from_port                = 6379
#   to_port                  = 6379
#   protocol                 = "tcp"
#   source_security_group_id = module.cloudflare.ecs_security_group_id
#   security_group_id        = data.terraform_remote_state.common.outputs.elasticache_security_group_id
#   description              = "Valkey from FastAPI ${var.environment} ECS tasks"
# }

module "target_group" {
  source = "../modules/target-group"

  project_name      = var.project_name
  environment       = var.environment
  vpc_id            = data.terraform_remote_state.common.outputs.vpc_id
  alb_listener_arn  = data.terraform_remote_state.common.outputs.https_listener_arn
  domain_name       = var.domain_name
  priority          = 200
  health_check_path = "/health"
}

module "certificate" {
  source = "../modules/certificate"

  project_name           = var.project_name
  environment            = var.environment
  listener_arn           = data.terraform_remote_state.common.outputs.https_listener_arn
  domain_name            = var.domain_name
  enable_cloudflare_ssl  = var.enable_cloudflare_ssl
  cloudflare_origin_cert = var.cloudflare_origin_cert
  cloudflare_origin_key  = var.cloudflare_origin_key
}

module "secrets" {
  source = "../modules/secrets"

  project_name                 = var.project_name
  environment                  = var.environment
  ecs_task_role_name           = data.terraform_remote_state.common.outputs.ecs_task_role_name
  ecs_task_execution_role_name = data.terraform_remote_state.common.outputs.ecs_task_execution_role_name
}

# ECS Service module
module "ecs_service" {
  source = "../modules/ecs-service"

  project_name                 = var.project_name
  environment                  = var.environment
  service_name                 = "fastapi-${var.environment}-service"
  aws_region                   = var.aws_region
  container_image              = var.container_image
  cpu                          = var.cpu
  memory                       = var.memory
  desired_count                = var.desired_count
  min_capacity                 = var.min_capacity
  max_capacity                 = var.max_capacity
  cpu_target_value             = var.cpu_target_value
  memory_target_value          = var.memory_target_value
  ecs_cluster_id               = data.terraform_remote_state.common.outputs.ecs_cluster_id
  ecs_cluster_name             = data.terraform_remote_state.common.outputs.ecs_cluster_name
  ecs_task_execution_role_arn  = data.terraform_remote_state.common.outputs.ecs_task_execution_role_arn
  ecs_task_execution_role_name = data.terraform_remote_state.common.outputs.ecs_task_execution_role_name
  ecs_task_role_arn            = data.terraform_remote_state.common.outputs.ecs_task_role_arn
  ecs_task_role_name           = data.terraform_remote_state.common.outputs.ecs_task_role_name
  ecs_security_group_id        = module.cloudflare.ecs_security_group_id
  private_subnet_ids           = data.terraform_remote_state.common.outputs.private_subnet_ids
  target_group_arn             = module.target_group.target_group_arn
  alb_listener_arn             = data.terraform_remote_state.common.outputs.https_listener_arn
  alb_rule_priority            = 201
  secrets_arn                  = module.secrets.secrets_arn
  credentials_secret_arn       = "arn:aws:secretsmanager:eu-west-1:534526983272:secret:fastapi-legacy-credentials-p9KGQI"
  cloudwatch_log_group_name    = aws_cloudwatch_log_group.app.name
  log_level                    = var.log_level
  cors_origins                 = var.cors_origins
  db_pool_size                 = var.db_pool_size
  db_pool_recycle              = var.db_pool_recycle
  profiling_enabled            = var.profiling_enabled
  profiling_default_format     = var.profiling_default_format
  redis_url                    = "redis://${data.terraform_remote_state.common.outputs.valkey_endpoint}:${data.terraform_remote_state.common.outputs.valkey_port}"
  efs_file_system_id           = data.terraform_remote_state.common.outputs.tiles_efs_file_system_id
  efs_access_point_id          = data.terraform_remote_state.common.outputs.tiles_efs_access_point_id
}

module "monitoring" {
  source = "../monitoring"

  project_name       = var.project_name
  environment        = var.environment
  aws_region         = var.aws_region
  log_retention_days = 14
}

# Test rule: route /health on main domain to FastAPI
# This allows testing FastAPI under the production domain before full DNS cutover
resource "aws_lb_listener_rule" "test_health" {
  listener_arn = data.terraform_remote_state.common.outputs.https_listener_arn
  priority     = 300

  action {
    type             = "forward"
    target_group_arn = module.target_group.target_group_arn
  }

  condition {
    host_header {
      values = ["trigpointing.uk"]
    }
  }

  condition {
    path_pattern {
      values = ["/health"]
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-test-health-rule"
  }
}

# Legacy migration admin endpoint: route /legacy-migration on main domain to web SPA
# This allows admins to access the migration UI from the main domain
resource "aws_lb_listener_rule" "legacy_migration" {
  listener_arn = data.terraform_remote_state.common.outputs.https_listener_arn
  priority     = 301

  action {
    type             = "forward"
    target_group_arn = module.spa_ecs_service.target_group_arn
  }

  condition {
    host_header {
      values = ["trigpointing.uk"]
    }
  }

  condition {
    path_pattern {
      values = ["/legacy-migration*"]
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-legacy-migration-rule"
  }
}

# Assets path: route /assets/* on main domain to web SPA
# Required for SPA to load JavaScript, CSS, and other static assets
resource "aws_lb_listener_rule" "assets" {
  listener_arn = data.terraform_remote_state.common.outputs.https_listener_arn
  priority     = 302

  action {
    type             = "forward"
    target_group_arn = module.spa_ecs_service.target_group_arn
  }

  condition {
    host_header {
      values = ["trigpointing.uk"]
    }
  }

  condition {
    path_pattern {
      values = ["/assets/*"]
    }
  }

  tags = {
    Name = "${var.project_name}-${var.environment}-assets-rule"
  }
}
