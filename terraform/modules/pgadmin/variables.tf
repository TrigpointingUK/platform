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
  description = "CPU units for pgAdmin ECS task"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Memory for pgAdmin ECS task"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired number of pgAdmin tasks"
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

variable "ecs_task_execution_role_name" {
  description = "ECS task execution role name"
  type        = string
}

variable "ecs_task_role_arn" {
  description = "ECS task role ARN"
  type        = string
}

variable "ecs_task_role_name" {
  description = "ECS task role name"
  type        = string
}

variable "ecs_security_group_id" {
  description = "ECS security group ID"
  type        = string
}

variable "private_subnet_ids" {
  description = "Private subnet IDs"
  type        = list(string)
}

variable "target_group_arn" {
  description = "Target group ARN"
  type        = string
}

variable "cloudwatch_log_group_name" {
  description = "CloudWatch log group name"
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
  description = "Target CPU utilisation for auto scaling"
  type        = number
  default     = 70
}

variable "memory_target_value" {
  description = "Target memory utilisation for auto scaling"
  type        = number
  default     = 80
}

variable "pgadmin_email" {
  description = "Default email for pgAdmin login"
  type        = string
  default     = "admin@trigpointing.uk"
}

variable "pgadmin_password" {
  description = "Default password for pgAdmin login"
  type        = string
  sensitive   = true
}

