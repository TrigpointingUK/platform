terraform {
  required_version = ">= 1.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
    auth0 = {
      source  = "auth0/auth0"
      version = "~> 1.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    # Backend configuration will be provided via backend.conf
  }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = var.project_name
      Environment = var.environment
      ManagedBy   = "terraform"
    }
  }
}

provider "auth0" {
  domain        = var.auth0_tenant_domain
  client_id     = var.auth0_terraform_client_id
  client_secret = var.auth0_terraform_client_secret
  # Credentials can also be set via environment variables:
  # AUTH0_DOMAIN, AUTH0_CLIENT_ID, AUTH0_CLIENT_SECRET
}

# Data source for common infrastructure
data "terraform_remote_state" "common" {
  backend = "s3"
  config = {
    bucket = "tuk-terraform-state"
    key    = "fastapi-common-eu-west-1/terraform.tfstate"
    region = "eu-west-1"
  }
}

# Data source for PostgreSQL credentials secret
data "aws_secretsmanager_secret" "postgres_credentials" {
  name = "fastapi-staging-postgres-credentials"
}
