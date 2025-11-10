variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "service_name" {
  description = "Name of the ECS service (defaults to project_name-environment if not specified)"
  type        = string
  default     = null
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "container_image" {
  description = "Docker image for the application"
  type        = string
}

variable "cpu" {
  description = "CPU units for the ECS task"
  type        = number
  default     = 512
}

variable "memory" {
  description = "Memory for the ECS task"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of tasks in the ECS service"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum number of tasks for auto scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of tasks for auto scaling"
  type        = number
  default     = 10
}

variable "cpu_target_value" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70
}

variable "memory_target_value" {
  description = "Target memory utilization for auto scaling"
  type        = number
  default     = 80
}

variable "ecs_cluster_id" {
  description = "ID of the ECS cluster"
  type        = string
}

variable "ecs_cluster_name" {
  description = "Name of the ECS cluster"
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "ARN of the ECS task execution role"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ARN of the ECS task role"
  type        = string
}

variable "ecs_task_role_name" {
  description = "Name of the ECS task role (for policy attachment)"
  type        = string
}

variable "ecs_task_execution_role_name" {
  description = "Name of the ECS task execution role (for policy attachment)"
  type        = string
}

variable "ecs_security_group_id" {
  description = "ID of the ECS security group"
  type        = string
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "target_group_arn" {
  description = "ARN of the target group"
  type        = string
}

variable "alb_listener_arn" {
  description = "ARN of the ALB listener"
  type        = string
}

variable "alb_rule_priority" {
  description = "Priority for the ALB listener rule"
  type        = number
  default     = 100
}

variable "secrets_arn" {
  description = "ARN of the secrets manager secret"
  type        = string
}

variable "credentials_secret_arn" {
  description = "ARN of the database credentials secret"
  type        = string
}

variable "cloudwatch_log_group_name" {
  description = "Name of the CloudWatch log group"
  type        = string
}


variable "log_level" {
  description = "Application log level (DEBUG, INFO, WARNING, ERROR)"
  type        = string
  default     = "INFO"
}

variable "cors_origins" {
  description = "CORS allowed origins (comma-separated)"
  type        = list(string)
  default     = null
}

variable "db_pool_size" {
  description = "Database connection pool size"
  type        = number
  default     = 5
}

variable "db_pool_recycle" {
  description = "Database connection pool recycle time (seconds)"
  type        = number
  default     = 300
}

variable "profiling_enabled" {
  description = "Enable pyinstrument profiling middleware"
  type        = bool
  default     = false
}

variable "profiling_default_format" {
  description = "Default profiling output format (html or speedscope)"
  type        = string
  default     = "html"
}

variable "efs_file_system_id" {
  description = "EFS file system ID for tile caching (optional)"
  type        = string
  default     = null
}

variable "efs_access_point_id" {
  description = "EFS access point ID for tile caching (optional)"
  type        = string
  default     = null
}

variable "redis_url" {
  description = "Redis/Valkey connection URL for Auth0 token caching"
  type        = string
  default     = ""
}

variable "photos_s3_bucket" {
  description = "S3 bucket name for photo uploads"
  type        = string
}

variable "photos_server_id" {
  description = "Server ID for photo uploads (references server table)"
  type        = number
}
