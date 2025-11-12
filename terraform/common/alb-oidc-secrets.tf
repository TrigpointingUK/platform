# AWS Secrets Manager Secret for ALB OIDC Configuration
# This secret stores Auth0 OIDC parameters for ALB authentication
# Manual update required after creation with actual Auth0 values

resource "aws_secretsmanager_secret" "alb_oidc" {
  name        = "${var.project_name}-alb-oidc-config"
  description = "Auth0 OIDC configuration for ALB authentication (cache.trigpointing.uk, phpmyadmin.trigpointing.uk, preview.trigpointing.uk)"

  tags = {
    Name        = "${var.project_name}-alb-oidc-config"
    Environment = "common"
    Purpose     = "ALB OIDC Authentication"
  }
}

# Initial placeholder secret version
# IMPORTANT: Update this manually in AWS Secrets Manager with actual Auth0 values:
# - issuer: https://auth.trigpointing.uk/ (MUST include trailing slash!)
# - authorization_endpoint: https://auth.trigpointing.uk/authorize
# - token_endpoint: https://auth.trigpointing.uk/oauth/token
# - user_info_endpoint: https://auth.trigpointing.uk/userinfo
# - client_id: Your Auth0 aws-alb application client ID
# - client_secret: Your Auth0 aws-alb application client secret
resource "aws_secretsmanager_secret_version" "alb_oidc" {
  secret_id = aws_secretsmanager_secret.alb_oidc.id
  secret_string = jsonencode({
    issuer                 = "https://auth.trigpointing.uk/"
    authorization_endpoint = "https://auth.trigpointing.uk/authorize"
    token_endpoint         = "https://auth.trigpointing.uk/oauth/token"
    user_info_endpoint     = "https://auth.trigpointing.uk/userinfo"
    client_id              = "placeholder-update-manually"
    client_secret          = "placeholder-update-manually"
  })

  # Ignore changes after initial creation to allow manual updates
  lifecycle {
    ignore_changes = [secret_string]
  }
}

# Data source to read the OIDC configuration
data "aws_secretsmanager_secret_version" "alb_oidc" {
  secret_id  = aws_secretsmanager_secret.alb_oidc.id
  depends_on = [aws_secretsmanager_secret_version.alb_oidc]
}

# Decode the secret for use in listener rules
locals {
  alb_oidc_config = jsondecode(data.aws_secretsmanager_secret_version.alb_oidc.secret_string)
}

