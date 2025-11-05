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
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
    tls = {
      source  = "hashicorp/tls"
      version = "~> 4.0"
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
      Environment = "common"
      ManagedBy   = "terraform"
    }
  }
}

provider "cloudflare" {
  # API token will be read from CLOUDFLARE_API_TOKEN environment variable
  # or from ~/.cloudflare/credentials file
}

# Data sources
data "aws_caller_identity" "current" {}
data "aws_availability_zones" "available" {
  state = "available"
}

# Note: S3 bucket and DynamoDB table are managed externally
# Using existing tuk-terraform-state bucket in eu-west-1
