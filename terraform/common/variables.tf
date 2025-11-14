variable "cloudflare_account_id" {
  description = "Cloudflare account ID for account-level resources (Bulk Redirects, Lists)"
  type        = string
}

variable "aws_region" {
  description = "AWS region"
  type        = string
  default     = "eu-west-1" # Ireland region
}

variable "project_name" {
  description = "Name of the project"
  type        = string
  default     = "trigpointing"
}

variable "vpc_cidr" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
  default     = ["eu-west-1a", "eu-west-1b"]
}

variable "private_subnet_ids" {
  description = "List of private subnet IDs"
  type        = list(string)
  default     = []
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
  default     = ""
}

variable "admin_ip_address" {
  description = "IP address allowed to connect to bastion host"
  type        = string
  default     = "86.162.34.238" # Your admin IP
}

variable "key_pair_name" {
  description = "AWS key pair name for bastion host access"
  type        = string
  default     = "trigpointing-bastion"
}

variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t4g.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage in GB (MySQL)"
  type        = number
  default     = 5
}

variable "db_max_allocated_storage" {
  description = "RDS maximum allocated storage in GB (MySQL)"
  type        = number
  default     = 10
}

variable "postgres_allocated_storage" {
  description = "PostgreSQL RDS allocated storage in GB (minimum 20 for gp3)"
  type        = number
  default     = 20
}

variable "postgres_max_allocated_storage" {
  description = "PostgreSQL RDS maximum allocated storage in GB"
  type        = number
  default     = 100
}

variable "db_performance_insights_enabled" {
  description = "Enable Performance Insights for RDS"
  type        = bool
  default     = false
}

variable "db_performance_insights_retention_period" {
  description = "Performance Insights retention period in days (7 for free tier, 465+ for advanced)"
  type        = number
  default     = 7
}

# CloudFlare SSL Configuration
variable "enable_cloudflare_ssl" {
  description = "Enable HTTPS with CloudFlare origin certificates"
  type        = bool
  default     = true
}

variable "mediawiki_db_credentials_arn" {
  description = "ARN of the MediaWiki database credentials secret in AWS Secrets Manager"
  type        = string
}

variable "phpbb_db_credentials_arn" {
  description = "ARN of the phpBB database credentials secret in AWS Secrets Manager"
  type        = string
}
