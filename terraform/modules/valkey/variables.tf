variable "project_name" {
  description = "Name of the project"
  type        = string
}

variable "environment" {
  description = "Environment name (staging/production)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID where Valkey will be deployed"
  type        = string
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

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
}

variable "valkey_security_group_id" {
  description = "Security group ID for Valkey"
  type        = string
}

variable "efs_security_group_id" {
  description = "Security group ID for EFS mount targets"
  type        = string
}

variable "service_discovery_service_arn" {
  description = "ARN of the service discovery service"
  type        = string
}

variable "cpu" {
  description = "Total CPU units for the ECS task"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Total memory for the ECS task"
  type        = number
  default     = 512
}

variable "valkey_cpu" {
  description = "CPU units for Valkey container"
  type        = number
  default     = 128
}

variable "valkey_memory" {
  description = "Memory for Valkey container"
  type        = number
  default     = 256
}

variable "valkey_max_memory" {
  description = "Maximum memory for Valkey"
  type        = string
  default     = "200mb"
}

variable "commander_cpu" {
  description = "CPU units for Redis Commander container"
  type        = number
  default     = 128
}

variable "commander_memory" {
  description = "Memory for Redis Commander container"
  type        = number
  default     = 256
}

variable "desired_count" {
  description = "Desired number of tasks in the ECS service"
  type        = number
  default     = 1
}

variable "min_capacity" {
  description = "Minimum number of tasks for auto scaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum number of tasks for auto scaling"
  type        = number
  default     = 3
}

variable "cpu_target_value" {
  description = "Target CPU utilization for auto scaling"
  type        = number
  default     = 70
}

variable "log_retention_days" {
  description = "CloudWatch log retention in days"
  type        = number
  default     = 7
}
