# Auth0 Configuration for Staging Environment
#
# This uses the auth0 module to create a complete Auth0 setup
# for the staging environment with its own tenant.

# ============================================================================
# SES DOMAIN IDENTITY
# ============================================================================

# Verify ownership of the entire staging domain
# This allows sending from any email address @trigpointing.me
resource "aws_ses_domain_identity" "trigpointing_me" {
  domain = "trigpointing.me"
}

# DKIM tokens for domain verification (improves deliverability)
resource "aws_ses_domain_dkim" "trigpointing_me" {
  domain = aws_ses_domain_identity.trigpointing_me.domain
}

# Add DNS records to Cloudflare for domain verification
resource "cloudflare_dns_record" "ses_verification" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "_amazonses.trigpointing.me"
  content = aws_ses_domain_identity.trigpointing_me.verification_token
  type    = "TXT"
  ttl     = 600

  comment = "SES domain verification for trigpointing.me"
}

# DKIM DNS records (3 records for email authentication)
resource "cloudflare_dns_record" "ses_dkim" {
  count = 3

  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "${aws_ses_domain_dkim.trigpointing_me.dkim_tokens[count.index]}._domainkey.trigpointing.me"
  content = "${aws_ses_domain_dkim.trigpointing_me.dkim_tokens[count.index]}.dkim.amazonses.com"
  type    = "CNAME"
  ttl     = 600

  comment = "SES DKIM record ${count.index + 1} for trigpointing.me"
}

# Custom MAIL FROM domain for SPF alignment
# This ensures the envelope sender (Return-Path) uses trigpointing.me domain
# which allows SPF to align with DMARC requirements
resource "aws_ses_domain_mail_from" "trigpointing_me" {
  domain           = aws_ses_domain_identity.trigpointing_me.domain
  mail_from_domain = "mail.trigpointing.me"
}

# MX record for custom MAIL FROM domain (required by SES)
resource "cloudflare_dns_record" "ses_mail_from_mx" {
  zone_id  = data.cloudflare_zones.staging.result[0].id
  name     = "mail"
  content  = "feedback-smtp.eu-west-1.amazonses.com"
  type     = "MX"
  priority = 10
  ttl      = 600

  comment = "MX record for SES custom MAIL FROM domain"
}

# SPF record for custom MAIL FROM subdomain
resource "cloudflare_dns_record" "ses_mail_from_spf" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "mail"
  content = "\"v=spf1 include:amazonses.com ~all\""
  type    = "TXT"
  ttl     = 600

  comment = "SPF record for SES custom MAIL FROM domain"
}

# SPF record for root domain
# Authorizes only AWS SES to send emails from @trigpointing.me addresses
resource "cloudflare_dns_record" "root_spf" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "@"
  content = "\"v=spf1 include:amazonses.com -all\""
  type    = "TXT"
  ttl     = 600

  comment = "SPF record for root domain - only AWS SES authorized"
}

# DMARC policy record for email authentication and reporting
# Configures quarantine policy to prevent email spoofing
resource "cloudflare_dns_record" "dmarc" {
  zone_id = data.cloudflare_zones.staging.result[0].id
  name    = "_dmarc"
  content = "\"v=DMARC1; p=quarantine; rua=mailto:dmarc-reports@trigpointing.me; ruf=mailto:dmarc-forensics@trigpointing.me; pct=100; adkim=r; aspf=r\""
  type    = "TXT"
  ttl     = 600

  comment = "DMARC policy - quarantine suspicious emails and send reports"
}

# Get Cloudflare zone info
data "cloudflare_zones" "staging" {
  name = "trigpointing.me"
}

# ============================================================================
# AUTH0 MODULE
# ============================================================================

module "auth0" {
  source = "../modules/auth0"

  environment = "staging"
  name_prefix = "tme"

  # Auth0 Domains
  auth0_custom_domain = var.auth0_custom_domain

  # Cloudflare Configuration
  cloudflare_zone_name = "trigpointing.me"

  # Database Connection
  database_connection_name = "tme-users"
  disable_signup           = false # Allow public signup in staging for testing

  # API Configuration
  api_name       = "tme-api"
  api_identifier = "https://api.trigpointing.me/"

  # FastAPI Configuration
  fastapi_url           = "https://api.trigpointing.me"
  webhook_shared_secret = var.webhook_shared_secret

  # Swagger UI Callbacks
  swagger_callback_urls = [
    "https://api.trigpointing.me/docs/oauth2-redirect",
    "http://localhost:8000/docs/oauth2-redirect",
  ]

  swagger_allowed_origins = [
    "https://api.trigpointing.me",
    "http://localhost:8000",
  ]

  # Web SPA Callbacks
  # Staging uses root path (/) for the SPA
  web_spa_callback_urls = [
    "https://trigpointing.me/",
    "https://trigpointing.me/app/",
    "http://localhost:5173", # Vite dev server (uses root for local development)
    "http://localhost:5173/app/",
  ]

  web_spa_allowed_origins = [
    "https://trigpointing.me",
    "http://localhost:5173",
  ]

  # Website Callbacks
  website_callback_urls = [
    "https://www.trigpointing.me/auth/callback",
    "http://localhost:3000/auth/callback", # Local development
  ]

  # Android Callbacks
  android_callback_urls = [
    "uk.trigpointing.android.debug://auth.trigpointing.me/android/uk.trigpointing.android.debug/callback",
  ]

  android_logout_urls = [
    "uk.trigpointing.android.debug://auth.trigpointing.me/android/uk.trigpointing.android.debug/callback",
  ]

  # Optional Apps (disabled for staging)
  enable_forum = false
  enable_wiki  = false

  # Role Configuration - uses module defaults: api-admin, wiki-admin, forum-admin

  # Email Provider (SES) - SMTP user created per environment
  smtp_host  = "email-smtp.eu-west-1.amazonaws.com"
  smtp_port  = 587
  from_email = "noreply@trigpointing.me"
  from_name  = "TrigpointingUK (Staging)"

  # Branding
  logo_url              = "https://trigpointing.uk/pics/tuk_logo.gif"
  primary_color         = "#005f00"
  page_background_color = "#ffffff"

  # Actions
  enable_post_registration_action = true
  enable_post_login_action        = true
  enable_alb_admin_only_action    = true
  custom_claims_namespace         = "https://trigpointing.uk/"

  # M2M Client Secret for Auth0 Actions
  auth0_m2m_client_secret = var.auth0_m2m_client_secret
}

# ============================================================================
# OUTPUTS
# ============================================================================

output "auth0_connection_id" {
  description = "Auth0 database connection ID"
  value       = module.auth0.connection_id
}

output "auth0_api_identifier" {
  description = "Auth0 API identifier (for FastAPI AUTH0_API_AUDIENCE)"
  value       = module.auth0.api_identifier
}

output "auth0_swagger_client_id" {
  description = "Swagger OAuth2 client ID"
  value       = module.auth0.swagger_client_id
}

output "auth0_web_spa_client_id" {
  description = "Web SPA client ID (for React application)"
  value       = module.auth0.web_spa_client_id
}

output "auth0_website_client_id" {
  description = "Website client ID"
  value       = module.auth0.website_client_id
  sensitive   = true
}

output "auth0_m2m_client_id" {
  description = "M2M client ID (for FastAPI AUTH0_M2M_CLIENT_ID)"
  value       = module.auth0.m2m_client_id
  sensitive   = true
}

output "auth0_tenant_domain" {
  description = "Auth0 tenant domain"
  value       = module.auth0.tenant_domain
}

output "auth0_smtp_user_name" {
  description = "IAM username for Auth0 SMTP"
  value       = module.auth0.smtp_user_name
}

output "auth0_smtp_username" {
  description = "Auth0 SMTP username (AWS Access Key ID)"
  value       = module.auth0.smtp_username
  sensitive   = true
}

output "auth0_smtp_password" {
  description = "Auth0 SMTP password"
  value       = module.auth0.smtp_password
  sensitive   = true
}

