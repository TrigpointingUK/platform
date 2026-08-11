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
      source = "cloudflare/cloudflare"
      # Pinned exactly, not "~> 5.0". Provider 5.23.0 cannot read the saved state
      # of the cloudflare_list_item resources in cloudflare.tf and fails every
      # plan with 'UpgradeResourceState ... AttributeName("redirect"): invalid
      # JSON, expected "[", got "{"'. Because .terraform.lock.hcl is gitignored,
      # a loose constraint means any fresh clone or -upgrade picks up the break.
      # Revisit when the redirect-list state upgrade is fixed upstream.
      version = "5.12.0"
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

# CloudFront requires its ACM certificates to live in us-east-1, regardless of
# where the distribution's origin is. Used only by the photo CDN certificates.
provider "aws" {
  alias  = "us_east_1"
  region = "us-east-1"

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
