# PostgreSQL Terraform Configuration for TrigpointingUK
# This creates PostgreSQL database infrastructure for FastAPI backend
# MediaWiki and phpBB continue to use MySQL (separate RDS instance)

terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
    postgresql = {
      source  = "cyrilgdn/postgresql"
      version = "~> 1.22"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.6"
    }
  }

  backend "s3" {
    # Configuration will be loaded from backend.conf
  }
}

provider "aws" {
  region = var.aws_region
}

# Data source for common infrastructure state
data "terraform_remote_state" "common" {
  backend = "s3"
  config = {
    bucket = "trigpointing-terraform-state"
    key    = "common/terraform.tfstate"
    region = var.aws_region
  }
}

# Get current AWS caller identity for ARN construction
data "aws_caller_identity" "current" {}

# PostgreSQL provider configuration
# This will be used for database and user management
provider "postgresql" {
  host     = split(":", data.terraform_remote_state.common.outputs.postgres_rds_endpoint)[0]
  port     = data.terraform_remote_state.common.outputs.postgres_rds_port
  username = "postgres"
  # Password is retrieved from AWS Secrets Manager by the RDS master user password rotation
  password = jsondecode(data.aws_secretsmanager_secret_version.postgres_master.secret_string)["password"]
  sslmode  = "require"
  # Don't use superuser mode - we want to ensure proper permissions
  superuser = false
}

# Fetch master password from Secrets Manager
data "aws_secretsmanager_secret" "postgres_master" {
  arn = data.terraform_remote_state.common.outputs.postgres_rds_master_secret_arn
}

data "aws_secretsmanager_secret_version" "postgres_master" {
  secret_id = data.aws_secretsmanager_secret.postgres_master.id
}

