# Auth0 Configuration for Production Environment
#
# This uses the auth0 module to create a complete Auth0 setup
# for the production environment with its own tenant.

# ============================================================================
# SES DOMAIN IDENTITY
# ============================================================================

# Verify ownership of the entire production domain
# This allows sending from any email address @trigpointing.uk
resource "aws_ses_domain_identity" "trigpointing_uk" {
  domain = "trigpointing.uk"
}

# DKIM tokens for domain verification (improves deliverability)
resource "aws_ses_domain_dkim" "trigpointing_uk" {
  domain = aws_ses_domain_identity.trigpointing_uk.domain
}

# Add DNS records to Cloudflare for domain verification
resource "cloudflare_dns_record" "ses_verification" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "_amazonses.trigpointing.uk"
  content = "\"${aws_ses_domain_identity.trigpointing_uk.verification_token}\""
  type    = "TXT"
  ttl     = 600

  comment = "SES domain verification for trigpointing.uk"
}

# DKIM DNS records (3 records for email authentication)
resource "cloudflare_dns_record" "ses_dkim" {
  count = 3

  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "${aws_ses_domain_dkim.trigpointing_uk.dkim_tokens[count.index]}._domainkey.trigpointing.uk"
  content = "${aws_ses_domain_dkim.trigpointing_uk.dkim_tokens[count.index]}.dkim.amazonses.com"
  type    = "CNAME"
  ttl     = 600

  comment = "SES DKIM record ${count.index + 1} for trigpointing.uk"
}

# Custom MAIL FROM domain for SPF alignment
# This ensures the envelope sender (Return-Path) uses trigpointing.uk domain
# which allows SPF to align with DMARC requirements
resource "aws_ses_domain_mail_from" "trigpointing_uk" {
  domain           = aws_ses_domain_identity.trigpointing_uk.domain
  mail_from_domain = "mail.trigpointing.uk"
}

# MX record for custom MAIL FROM domain (required by SES)
resource "cloudflare_dns_record" "ses_mail_from_mx" {
  zone_id  = data.cloudflare_zones.production.result[0].id
  name     = "mail"
  content  = "feedback-smtp.eu-west-1.amazonses.com"
  type     = "MX"
  priority = 10
  ttl      = 600

  comment = "MX record for SES custom MAIL FROM domain"
}

# SPF record for custom MAIL FROM subdomain
resource "cloudflare_dns_record" "ses_mail_from_spf" {
  zone_id = data.cloudflare_zones.production.result[0].id
  name    = "mail"
  content = "v=spf1 include:amazonses.com ~all"
  type    = "TXT"
  ttl     = 600

  comment = "SPF record for SES custom MAIL FROM domain"
}

# Get Cloudflare zone info
data "cloudflare_zones" "production" {
  name = "trigpointing.uk"
}

# ============================================================================
# AUTH0 MODULE
# ============================================================================

module "auth0" {
  source = "../modules/auth0"

  environment = "production"
  name_prefix = "tuk"

  # Auth0 Domains
  auth0_custom_domain = var.auth0_custom_domain

  # M2M Client Secret (for Actions)
  auth0_m2m_client_secret = var.auth0_m2m_client_secret

  # Cloudflare Configuration
  cloudflare_zone_name = "trigpointing.uk"

  # Database Connection
  database_connection_name = "tuk-users"
  disable_signup           = var.disable_signup

  # API Configuration
  api_name       = "tuk-api"
  api_identifier = "https://api.trigpointing.uk/"

  # FastAPI Configuration
  fastapi_url = "https://api.trigpointing.uk"

  # Swagger UI Callbacks
  swagger_callback_urls = [
    "https://api.trigpointing.uk/docs/oauth2-redirect",
  ]

  swagger_allowed_origins = [
    "https://api.trigpointing.uk",
  ]

  # Web SPA Callbacks
  web_spa_callback_urls = [
    "https://preview.trigpointing.uk/",
  ]

  web_spa_allowed_origins = [
    "https://preview.trigpointing.uk",
  ]

  # Website Callbacks
  website_callback_urls = [
    "https://www.trigpointing.uk/auth/callback",
  ]

  # Forum Callbacks
  forum_callback_urls = [
    "https://forum.trigpointing.uk/ucp.php?mode=login&login=external&oauth_service=auth.provider.oauth.service.auth0",
  ]
  forum_logout_urls = [
    "https://forum.trigpointing.uk/*",
  ]

  # Wiki Callbacks
  wiki_callback_urls = [
    "https://wiki.trigpointing.uk/Special:PluggableAuthLogin",
  ]
  wiki_logout_urls = [
    "https://wiki.trigpointing.uk",
    "https://wiki.trigpointing.uk/TrigpointingUK",
    "https://wiki.trigpointing.uk/*",
  ]

  # Android Callbacks
  android_callback_urls = [
    "uk.trigpointing.android://callback",
  ]
  android_logout_urls = [
    "uk.trigpointing.android://trigpointing.eu.auth0.com/android/uk.trigpointing.android/callback",
    "uk.trigpointing.android.debug://trigpointing.eu.auth0.com/android/uk.trigpointing.android.debug/callback",
  ]
  android_web_origins = [
    "https://fastapi.trigpointing.uk",
    "https://api.trigpointing.uk",
  ]

  # Optional Apps (enabled for production)
  enable_forum = true
  enable_wiki  = true

  # Role Configuration - uses module defaults: api-admin, wiki-admin, forum-admin

  # Email Provider (SES) - SMTP user created per environment
  smtp_host  = "email-smtp.eu-west-1.amazonaws.com"
  smtp_port  = 587
  from_email = "noreply@trigpointing.uk"
  from_name  = "TrigpointingUK"

  # Branding
  logo_url              = "https://trigpointing.uk/pics/tuk_logo.gif"
  primary_color         = "#005f00"
  page_background_color = "#ffffff"

  # Actions
  enable_post_registration_action = true
  enable_post_login_action        = true
  enable_alb_admin_only_action    = true
  custom_claims_namespace         = "https://trigpointing.uk/"
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

output "auth0_forum_client_id" {
  description = "Forum client ID"
  value       = module.auth0.forum_client_id
  sensitive   = true
}

output "auth0_wiki_client_id" {
  description = "Wiki client ID"
  value       = module.auth0.wiki_client_id
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

