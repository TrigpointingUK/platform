variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1"
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "trigpointing"
}

variable "environment" {
  description = "Environment"
  type        = string
  default     = "dev"
}

# Note: terraform_state_bucket is hardcoded to "tuk-terraform-state" in eu-west-1

variable "container_image" {
  description = "Docker image for the application"
  type        = string
}

variable "spa_container_image" {
  description = "Docker image for the SPA web application"
  type        = string
  default     = "ghcr.io/trigpointinguk/platform/web:latest"
}

variable "cpu" {
  description = "CPU units for the ECS task"
  type        = number
  default     = 1024
}

variable "memory" {
  description = "Memory for the ECS task"
  type        = number
  default     = 2048
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
  default     = 1
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

variable "enable_cloudflare_ssl" {
  description = "Enable HTTPS with CloudFlare origin certificate"
  type        = bool
}

variable "cloudflare_origin_cert" {
  description = "CloudFlare origin certificate (PEM format)"
  type        = string
  default     = null
  sensitive   = true
}

variable "cloudflare_origin_key" {
  description = "CloudFlare origin certificate private key"
  type        = string
  default     = null
  sensitive   = true
}

variable "domain_name" {
  description = "Domain name for the API"
  type        = string
}

# Auth0 Configuration (always enabled)

variable "auth0_tenant_domain" {
  description = "Auth0 tenant domain for Management API (e.g., myapp-staging.eu.auth0.com)"
  type        = string
}

variable "auth0_custom_domain" {
  description = "Auth0 custom domain for user-facing authentication (e.g., auth.trigpointing.me)"
  type        = string
}

variable "auth0_terraform_client_id" {
  description = "Auth0 Terraform provider client ID (terraform-provider application)"
  type        = string
  sensitive   = true
}

variable "auth0_terraform_client_secret" {
  description = "Auth0 Terraform provider client secret (terraform-provider application)"
  type        = string
  sensitive   = true
}

variable "auth0_m2m_client_secret" {
  description = "M2M client secret for Auth0 Actions (tme-api application)"
  type        = string
  sensitive   = true
}

variable "disable_signup" {
  description = "Whether to disable public signup on the Auth0 database connection"
  type        = bool
  default     = false
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

variable "use_ecs_valkey" {
  description = "Use ECS Valkey instead of ElastiCache Serverless"
  type        = bool
  default     = false
}

variable "profiling_default_format" {
  description = "Default profiling output format (html or speedscope)"
  type        = string
  default     = "html"
}
