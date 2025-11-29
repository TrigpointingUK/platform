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

variable "pgcron_database_name" {
  description = "Database where pg_cron extension should be installed (ONLY ONE per RDS instance)"
  type        = string
  default     = "tuk_production"
}

