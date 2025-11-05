terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    archive = {
      source  = "hashicorp/archive"
      version = "~> 2.4"
    }
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
      Component   = "monitoring"
    }
  }
}

# Reference common stack for VPC/roles if needed
data "terraform_remote_state" "common" {
  backend = "s3"
  config = {
    bucket = "tuk-terraform-state"
    key    = "fastapi-common-eu-west-1/terraform.tfstate"
    region = "eu-west-1"
  }
}
