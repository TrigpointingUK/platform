# VPC Outputs
output "vpc_id" {
  description = "ID of the VPC"
  value       = aws_vpc.main.id
}

output "vpc_cidr_block" {
  description = "CIDR block of the VPC"
  value       = aws_vpc.main.cidr_block
}

output "public_subnet_ids" {
  description = "IDs of the public subnets"
  value       = aws_subnet.public[*].id
}

output "private_subnet_ids" {
  description = "IDs of the private subnets"
  value       = aws_subnet.private[*].id
}

# ECS Outputs
output "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  value       = aws_ecs_cluster.main.id
}

output "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  value       = aws_ecs_cluster.main.name
}

output "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution_role.arn
}

output "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  value       = aws_iam_role.ecs_task_role.arn
}

output "ecs_task_role_name" {
  description = "Name of the ECS task role"
  value       = aws_iam_role.ecs_task_role.name
}

output "ecs_task_execution_role_name" {
  description = "Name of the ECS task execution role"
  value       = aws_iam_role.ecs_task_execution_role.name
}

# RDS Outputs
output "rds_endpoint" {
  description = "RDS instance endpoint"
  value       = aws_db_instance.main.endpoint
  sensitive   = true
}

output "rds_port" {
  description = "RDS instance port"
  value       = aws_db_instance.main.port
}

output "rds_db_name" {
  description = "RDS database name"
  value       = aws_db_instance.main.db_name
}

output "rds_identifier" {
  description = "RDS instance identifier"
  value       = aws_db_instance.main.identifier
}

output "rds_arn" {
  description = "RDS instance ARN"
  value       = aws_db_instance.main.arn
}

# Note: admin_password output removed - use master_user_secret_arn instead

output "master_user_secret_arn" {
  description = "ARN of the RDS master user secret (for password rotation)"
  value       = length(aws_db_instance.main.master_user_secret) > 0 ? aws_db_instance.main.master_user_secret[0].secret_arn : null
  sensitive   = true
}

output "rds_security_group_id" {
  description = "ID of the RDS security group"
  value       = aws_security_group.rds.id
}


# Bastion Outputs
output "bastion_public_ip" {
  description = "Public IP of the bastion host"
  value       = aws_eip.bastion.public_ip
}

output "bastion_security_group_id" {
  description = "ID of the bastion security group"
  value       = aws_security_group.bastion.id
}

# ALB Outputs
output "alb_arn" {
  description = "ARN of the Application Load Balancer"
  value       = aws_lb.main.arn
}

output "alb_dns_name" {
  description = "DNS name of the Application Load Balancer"
  value       = aws_lb.main.dns_name
}

output "alb_zone_id" {
  description = "Zone ID of the Application Load Balancer"
  value       = aws_lb.main.zone_id
}

output "alb_security_group_id" {
  description = "Security group ID of the ALB"
  value       = aws_security_group.alb.id
}

# Note: ALB listener ARNs are now managed by individual environment modules
# (staging and production) for their respective HTTPS listeners

# Note: RDS user credentials and database schemas are now managed in the mysql/ directory

# DynamoDB Table
output "dynamodb_table_name" {
  description = "Name of the DynamoDB table for state locking"
  value       = aws_dynamodb_table.terraform_state_lock.name
}

# CloudFlare DNS Records
output "api_staging_domain" {
  description = "Staging API domain (api.trigpointing.me)"
  value       = "api.trigpointing.me"
}

output "api_production_domain" {
  description = "Production API domain (api.trigpointing.uk)"
  value       = "api.trigpointing.uk"
}

output "api_staging_record_id" {
  description = "CloudFlare record ID for staging API"
  value       = cloudflare_dns_record.api_staging.id
}

output "api_production_record_id" {
  description = "CloudFlare record ID for production API"
  value       = cloudflare_dns_record.api_production.id
}

# Note: S3 bucket is managed externally
# Bucket: tuk-terraform-state (in eu-west-1)

# HTTPS Listener ARN for environments to use
output "https_listener_arn" {
  description = "ARN of the shared HTTPS listener"
  value       = var.enable_cloudflare_ssl ? aws_lb_listener.app_https[0].arn : null
}


# EFS Outputs for phpBB
output "phpbb_efs_file_system_id" {
  description = "ID of the EFS file system for phpBB"
  value       = aws_efs_file_system.phpbb.id
}

output "phpbb_efs_access_point_arn" {
  description = "ARN of the EFS access point for phpBB"
  value       = aws_efs_access_point.phpbb.arn
}

output "phpbb_efs_security_group_id" {
  description = "Security group ID for EFS (phpBB)"
  value       = aws_security_group.efs_phpbb.id
}

output "mediawiki_efs_file_system_id" {
  description = "ID of the EFS file system for MediaWiki"
  value       = aws_efs_file_system.mediawiki.id
}

output "mediawiki_efs_access_point_arn" {
  description = "ARN of the EFS access point for MediaWiki"
  value       = aws_efs_access_point.mediawiki.arn
}

output "mediawiki_efs_access_point_id" {
  description = "ID of the EFS access point for MediaWiki"
  value       = aws_efs_access_point.mediawiki.id
}

output "phpbb_app_secrets_arn" {
  description = "ARN of the phpBB application secrets in AWS Secrets Manager"
  value       = aws_secretsmanager_secret.phpbb_app_secrets.arn
}

# ElastiCache Outputs (COMMENTED OUT - replaced with ECS Valkey)
# output "elasticache_valkey_endpoint" {
#   description = "ElastiCache Valkey serverless endpoint"
#   value       = aws_elasticache_serverless_cache.valkey.endpoint[0].address
#   sensitive   = true
# }

# output "elasticache_valkey_port" {
#   description = "ElastiCache Valkey serverless port"
#   value       = aws_elasticache_serverless_cache.valkey.endpoint[0].port
# }

# output "elasticache_security_group_id" {
#   description = "Security group ID for ElastiCache"
#   value       = aws_security_group.elasticache.id
# }

# SES SMTP Outputs for MediaWiki
output "mediawiki_smtp_username" {
  description = "SMTP username for MediaWiki (AWS Access Key ID)"
  value       = module.smtp_mediawiki.smtp_username
  sensitive   = true
}

output "mediawiki_smtp_password" {
  description = "SMTP password for MediaWiki"
  value       = module.smtp_mediawiki.smtp_password
  sensitive   = true
}

# SES SMTP Outputs for phpBB
output "phpbb_smtp_username" {
  description = "SMTP username for phpBB (AWS Access Key ID)"
  value       = module.smtp_phpbb.smtp_username
  sensitive   = true
}

output "phpbb_smtp_password" {
  description = "SMTP password for phpBB"
  value       = module.smtp_phpbb.smtp_password
  sensitive   = true
}

output "valkey_security_group_id" {
  description = "Security group ID for Valkey ECS service"
  value       = aws_security_group.valkey_ecs.id
}

# Service Discovery Outputs
output "service_discovery_namespace_id" {
  description = "Service discovery namespace ID"
  value       = aws_service_discovery_private_dns_namespace.main.id
}

output "valkey_service_discovery_arn" {
  description = "Service discovery service ARN for Valkey"
  value       = aws_service_discovery_service.valkey.arn
}

output "valkey_endpoint" {
  description = "Valkey endpoint for service discovery"
  value       = module.valkey.valkey_endpoint
}

output "valkey_port" {
  description = "Valkey port"
  value       = module.valkey.valkey_port
}

output "valkey_commander_target_group_arn" {
  description = "Target group ARN for Redis Commander"
  value       = module.valkey.valkey_commander_target_group_arn
}

# Note: Auth0 SMTP credentials are output from the auth0 module per environment
