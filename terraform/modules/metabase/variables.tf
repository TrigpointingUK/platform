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
  description = "CPU units for Metabase ECS task"
  type        = number
  default     = 512
}

variable "memory" {
  description = "Memory (MB) for Metabase ECS task"
  type        = number
  default     = 1024
}

variable "desired_count" {
  description = "Desired number of Metabase tasks"
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

# Metabase metadata database connection
variable "mb_db_host" {
  description = "Hostname of the PostgreSQL RDS instance for Metabase metadata"
  type        = string
}

variable "mb_db_port" {
  description = "Port of the PostgreSQL RDS instance"
  type        = number
  default     = 5432
}

variable "mb_db_dbname" {
  description = "Database name for Metabase internal metadata"
  type        = string
  default     = "metabase"
}

variable "mb_db_user" {
  description = "Database user for Metabase metadata"
  type        = string
}

variable "mb_db_pass" {
  description = "Database password for Metabase metadata"
  type        = string
  sensitive   = true
}

variable "java_timezone" {
  description = "JVM timezone for Metabase"
  type        = string
  default     = "Europe/London"
}
