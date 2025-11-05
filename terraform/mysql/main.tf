terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    random = {
      source  = "hashicorp/random"
      version = "~> 3.0"
    }
    mysql = {
      source  = "petoju/mysql"
      version = "~> 3.0"
    }
  }

  backend "s3" {
    # Backend configuration will be provided via backend.conf files
    # Use: terraform init -backend-config=backend.conf
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = "mysql"
      ManagedBy   = "terraform"
    }
  }
}

# Data sources for remote state
data "terraform_remote_state" "common" {
  backend = "s3"
  config = {
    bucket = "tuk-terraform-state"
    key    = "fastapi-common-eu-west-1/terraform.tfstate"
    region = "eu-west-1"
  }
}

# Data source to get RDS master user password from Secrets Manager
data "aws_secretsmanager_secret_version" "rds_master_password" {
  secret_id = data.terraform_remote_state.common.outputs.master_user_secret_arn
}

# Parse the secret JSON to get the password
locals {
  rds_master_credentials = jsondecode(data.aws_secretsmanager_secret_version.rds_master_password.secret_string)
}

# MySQL provider for database management
# Uses the RDS master user credentials from common infrastructure
provider "mysql" {
  endpoint = split(":", data.terraform_remote_state.common.outputs.rds_endpoint)[0]
  username = "admin"
  password = local.rds_master_credentials.password
}
