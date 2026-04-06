variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "cpu" {
  description = "CPU units for Hasura ECS task"
  type        = number
  default     = 512
}

variable "memory" {
  description = "Memory (MB) for Hasura ECS task"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of Hasura tasks"
  type        = number
  default     = 1
}

variable "ecs_cluster_id" {
  description = "ECS cluster ID"
  type        = string
}

variable "ecs_cluster_name" {
  description = "ECS cluster name"
  type        = string
}

variable "ecs_task_execution_role_arn" {
  description = "ECS task execution role ARN"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "ecs_security_group_id" {
  description = "Security group ID for the ECS tasks"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "target_group_arn" {
  description = "Target group ARN for the ALB"
  type        = string
}

variable "min_capacity" {
  description = "Minimum number of tasks for auto scaling"
  type        = number
  default     = 0
}

variable "max_capacity" {
  description = "Maximum number of tasks for auto scaling"
  type        = number
  default     = 1
}

variable "cpu_target_value" {
  description = "Target CPU utilisation percentage for auto scaling"
  type        = number
  default     = 70
}

# Hasura metadata database connection
variable "metadata_database_url" {
  description = "PostgreSQL connection URL for Hasura metadata storage (postgres://user:pass@host:port/dbname)"
  type        = string
  sensitive   = true
}

# Hasura data source (analytics schema)
variable "database_url" {
  description = "PostgreSQL connection URL for the analytics data source (postgres://user:pass@host:port/dbname)"
  type        = string
  sensitive   = true
}

variable "admin_secret" {
  description = "Admin secret for Hasura console and metadata API access"
  type        = string
  sensitive   = true
}

variable "jwt_secret" {
  description = "JWT secret configuration JSON for Auth0 token validation"
  type        = string
  sensitive   = true
}
