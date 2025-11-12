# Auth0 Module - Manages Auth0 resources for a single environment
#
# This module creates:
# - Database connection for user authentication
# - API resource server with scopes
# - M2M client for API access
# - SPA client for Swagger UI
# - Regular web application client
# - Native Android client
# - Admin role with permissions
# - Post User Registration Action (optional)

terraform {
  required_providers {
    auth0 = {
      source  = "auth0/auth0"
      version = "~> 1.0"
    }
    cloudflare = {
      source  = "cloudflare/cloudflare"
      version = "~> 5.0"
    }
    aws = {
      source  = "hashicorp/aws"
      version = "~> 6.0"
    }
  }
}

# Handle resource renames (prevents destroy/create cycles)
moved {
  from = auth0_client.swagger_ui
  to   = auth0_client.swagger
}

moved {
  from = auth0_client.web_app
  to   = auth0_client.website
}

# ============================================================================
# DATABASE CONNECTION
# ============================================================================
# Note: The default 'Username-Password-Authentication' connection should be
# manually deleted in the Auth0 dashboard to avoid confusion.

resource "auth0_connection" "database" {
  name     = var.database_connection_name
  strategy = "auth0"

  # Ensure Identifier First is enabled before passkeys
  depends_on = [auth0_prompt.identifier_first]

  options {
    # Relax password requirements to allow weak and previously used passwords
    password_policy = "none"
    password_history {
      enable = false
      size   = 0
    }
    password_no_personal_info {
      enable = false
    }
    password_dictionary {
      enable = false
    }
    password_complexity_options {
      min_length = 1
    }
    brute_force_protection = true

    # Configuration settings
    disable_signup    = var.disable_signup
    requires_username = false # Use nickname instead (allows spaces, special chars)

    # Validation
    import_mode          = false
    non_persistent_attrs = []

    # Passkey/WebAuthn configuration
    authentication_methods {
      password {
        enabled = true
      }
      passkey {
        enabled = true
      }
    }
  }

  # Workaround for provider/API drift: Auth0 may return password_policy as null,
  # which causes perpetual diffs. Ignore just this attribute.
  lifecycle {
    ignore_changes = [
      options[0].password_policy
    ]
  }
}

# Enable connection for all our clients
resource "auth0_connection_clients" "database_clients" {
  connection_id = auth0_connection.database.id

  enabled_clients = concat(
    [
      auth0_client.m2m_api.id,
      auth0_client.swagger.id,
      auth0_client.web_spa.id,
      auth0_client.website.id,
      auth0_client.android.id,
      auth0_client.alb.id,
      auth0_client.legacy.id,
    ],
    var.enable_forum ? [auth0_client.forum[0].id] : [],
    var.enable_wiki ? [auth0_client.wiki[0].id] : [],
  )
}

# ============================================================================
# API RESOURCE SERVER
# ============================================================================

resource "auth0_resource_server" "api" {
  name       = var.api_name
  identifier = var.api_identifier

  # Token settings
  token_lifetime = 86400 # 24 hours
  signing_alg    = "RS256"

  # RBAC
  enforce_policies                                = true
  token_dialect                                   = "access_token_authz"
  skip_consent_for_verifiable_first_party_clients = true
}

# Define API scopes/permissions
resource "auth0_resource_server_scopes" "api_scopes" {
  resource_server_identifier = auth0_resource_server.api.identifier

  scopes {
    name        = "api:admin"
    description = "Full administrative access to API"
  }
  scopes {
    name        = "api:write"
    description = "Create and update own logs, photos, trigs"
  }
  scopes {
    name        = "api:read-pii"
    description = "Read and write sensitive PII (email) for self"
  }
}

# ============================================================================
# APPLICATIONS (CLIENTS)
# ============================================================================

# M2M Application for API access
resource "auth0_client" "m2m_api" {
  name        = "${var.name_prefix}-api"
  description = "Machine to Machine application for ${var.environment} API"
  app_type    = "non_interactive"

  grant_types = [
    "client_credentials",
  ]

  jwt_configuration {
    alg = "RS256"
  }
}

# Note: Client secret must be rotated manually in Auth0 dashboard if needed
# then provided via var.auth0_m2m_client_secret

# Single Page Application (Swagger)
resource "auth0_client" "swagger" {
  name        = "${var.name_prefix}-swagger"
  description = "SPA for Swagger/OpenAPI documentation OAuth2 authentication"
  app_type    = "spa"

  callbacks           = var.swagger_callback_urls
  allowed_origins     = var.swagger_allowed_origins
  web_origins         = var.swagger_allowed_origins
  allowed_logout_urls = [for url in var.swagger_callback_urls : replace(url, "/oauth2-redirect", "")]

  grant_types = [
    "authorization_code",
    "refresh_token",
  ]

  jwt_configuration {
    alg = "RS256"
  }

  oidc_conformant = true
}

# Single Page Application (Web App)
resource "auth0_client" "web_spa" {
  name        = "${var.name_prefix}-web"
  description = "React SPA for TrigpointingUK (${var.environment})"
  app_type    = "spa"

  callbacks           = var.web_spa_callback_urls
  allowed_origins     = var.web_spa_allowed_origins
  web_origins         = var.web_spa_allowed_origins
  allowed_logout_urls = var.web_spa_callback_urls

  grant_types = [
    "authorization_code",
    "refresh_token",
  ]

  jwt_configuration {
    alg = "RS256"
  }

  oidc_conformant = true

  # Token settings for security
  refresh_token {
    rotation_type                = "rotating"
    expiration_type              = "expiring"
    leeway                       = 0
    token_lifetime               = 2592000 # 30 days
    infinite_token_lifetime      = false
    infinite_idle_token_lifetime = false
    idle_token_lifetime          = 1296000 # 15 days
  }
}

# Regular Web Application (Website)
resource "auth0_client" "website" {
  name        = "${var.name_prefix}-website"
  description = "Main website for ${var.environment}"
  app_type    = "regular_web"

  callbacks           = var.website_callback_urls
  allowed_logout_urls = [] # Empty - forum and wiki have their own clients now
  web_origins         = [] # Empty - website doesn't need CORS

  grant_types = [
    "authorization_code",
    "refresh_token",
  ]

  jwt_configuration {
    alg = "RS256"
  }

  oidc_conformant = true
}

# Regular Web Application (Forum) - Optional
resource "auth0_client" "forum" {
  count = var.enable_forum ? 1 : 0

  name        = "${var.name_prefix}-forum"
  description = "Forum (phpBB) for ${var.environment}"
  app_type    = "regular_web"

  callbacks           = var.forum_callback_urls
  allowed_logout_urls = var.forum_logout_urls

  grant_types = [
    "authorization_code",
    "refresh_token",
  ]

  jwt_configuration {
    alg = "RS256"
  }

  oidc_conformant = true
}

# Regular Web Application (Wiki) - Optional
resource "auth0_client" "wiki" {
  count = var.enable_wiki ? 1 : 0

  name        = "${var.name_prefix}-wiki"
  description = "Wiki (MediaWiki) for ${var.environment}"
  app_type    = "regular_web"

  callbacks           = var.wiki_callback_urls
  allowed_logout_urls = var.wiki_logout_urls

  grant_types = [
    "authorization_code",
    "refresh_token",
  ]

  jwt_configuration {
    alg = "RS256"
  }

  oidc_conformant = true
}

# Native Application (Android)
resource "auth0_client" "android" {
  name        = "${var.name_prefix}-android"
  description = "Android mobile application for ${var.environment}"
  app_type    = "native"

  callbacks           = var.android_callback_urls
  allowed_logout_urls = var.android_logout_urls
  web_origins         = var.android_web_origins

  grant_types = [
    "authorization_code",
    "refresh_token",
  ]

  jwt_configuration {
    alg = "RS256"
  }

  oidc_conformant = true
}

# Regular Web Application (AWS ALB OIDC)
# Used for ALB OIDC authentication to admin tools and preview sites
resource "auth0_client" "alb" {
  name        = "${var.name_prefix}-aws-alb"
  description = "AWS ALB OIDC authentication for admin tools and preview sites (${var.environment})"
  app_type    = "regular_web"

  callbacks = concat(
    [
      "https://cache.${var.environment == "production" ? "trigpointing.uk" : "trigpointing.me"}/oauth2/idpresponse",
      "https://phpmyadmin.${var.environment == "production" ? "trigpointing.uk" : "trigpointing.me"}/oauth2/idpresponse",
    ],
    # Preview site only exists in production
    var.environment == "production" ? ["https://preview.trigpointing.uk/oauth2/idpresponse"] : []
  )

  allowed_logout_urls = concat(
    [
      "https://cache.${var.environment == "production" ? "trigpointing.uk" : "trigpointing.me"}",
      "https://phpmyadmin.${var.environment == "production" ? "trigpointing.uk" : "trigpointing.me"}",
    ],
    # Preview site only exists in production
    var.environment == "production" ? ["https://preview.trigpointing.uk"] : []
  )

  grant_types = [
    "authorization_code",
    "refresh_token",
  ]

  jwt_configuration {
    alg = "RS256"
  }

  oidc_conformant = true
}

# Legacy Application (manually created, imported into Terraform)
# This application was created before Terraform and needs to remain connected to the database
resource "auth0_client" "legacy" {
  name        = "Trigpointing UK"
  description = "Trigpointing UK application (${var.environment})"
  app_type    = "regular_web"

  callbacks = [
    "https://trigpointing.uk/auth0/callback.php",
  ]

  allowed_logout_urls = [
    "https://trigpointing.uk/",
    "https://trigpointing.uk/logout.php",
  ]

  web_origins = [
    "https://login.trigpointing.uk",
    "https://trigpointing.uk",
  ]

  initiate_login_uri = "https://trigpointing.uk/auth0/login.php"

  grant_types = [
    "authorization_code",
    "implicit",
    "refresh_token",
  ]

  jwt_configuration {
    alg = "RS256"
  }

  oidc_conformant = true

  # Lifecycle: This is an imported resource - prevent accidental changes
  lifecycle {
    # Prevent accidental destruction
    prevent_destroy = false # Set to true in production if needed

    # Ignore changes to these fields - they're managed manually or by the legacy app
    ignore_changes = [
      callbacks,
      allowed_logout_urls,
      web_origins,
      initiate_login_uri,
      grant_types,
    ]
  }
}

# ============================================================================
# CLIENT GRANTS (M2M Authorizations)
# ============================================================================

# Grant M2M client access to API
resource "auth0_client_grant" "m2m_to_api" {
  client_id = auth0_client.m2m_api.id
  audience  = auth0_resource_server.api.identifier

  scopes = [
    "api:admin",
    "api:write",
    "api:read-pii",
  ]
}

# Grant Web SPA client access to API
# Note: SPAs use user-context authorization (not M2M), so scopes are filtered by user's role permissions
resource "auth0_client_grant" "web_spa_to_api" {
  client_id = auth0_client.web_spa.id
  audience  = auth0_resource_server.api.identifier

  scopes = [
    "api:admin",
    "api:write",
    "api:read-pii",
  ]
}

# Grant M2M client access to Management API (for user provisioning sync)
resource "auth0_client_grant" "m2m_to_mgmt_api" {
  client_id = auth0_client.m2m_api.id
  audience  = "https://${data.auth0_tenant.current.domain}/api/v2/"

  scopes = [
    "read:users",
    "update:users",
    "create:users",
  ]
}

# ============================================================================
# ROLES
# ============================================================================

# API Admin Role - Full FastAPI administrative access
resource "auth0_role" "api_admin" {
  name        = var.api_admin_role_name
  description = "Full administrative access to FastAPI"
}

# Assign permissions to API admin role
resource "auth0_role_permissions" "api_admin_perms" {
  role_id = auth0_role.api_admin.id

  dynamic "permissions" {
    for_each = ["api:admin", "api:write", "api:read-pii"]
    content {
      resource_server_identifier = auth0_resource_server.api.identifier
      name                       = permissions.value
    }
  }
}

# Wiki Admin Role - MediaWiki sysop access
resource "auth0_role" "wiki_admin" {
  name        = var.wiki_admin_role_name
  description = "MediaWiki sysop (administrator) access"
}

# Wiki admins don't need API permissions - role is for wiki access only

# Forum Admin Role - phpBB administrator access
resource "auth0_role" "forum_admin" {
  name        = var.forum_admin_role_name
  description = "phpBB forum administrator access"
}

# Forum admins don't need API permissions - role is for forum access only

# ============================================================================
# POST USER REGISTRATION ACTION
# ============================================================================

resource "auth0_action" "post_user_registration" {
  count = var.enable_post_registration_action ? 1 : 0

  name    = "${var.name_prefix}-post-user-registration"
  runtime = "node22"
  deploy  = true

  supported_triggers {
    id      = "post-user-registration"
    version = "v2"
  }

  code = templatefile("${path.module}/actions/post-user-registration.js.tpl", {
    environment = var.environment
  })

  dependencies {
    name    = "axios"
    version = "1.7.9"
  }

  secrets {
    name  = "FASTAPI_URL"
    value = var.fastapi_url
  }

  secrets {
    name  = "M2M_CLIENT_ID"
    value = auth0_client.m2m_api.client_id
  }

  secrets {
    name  = "M2M_CLIENT_SECRET"
    value = var.auth0_m2m_client_secret
  }

  secrets {
    name  = "AUTH0_DOMAIN"
    value = data.auth0_tenant.current.domain
  }

  secrets {
    name  = "API_AUDIENCE"
    value = auth0_resource_server.api.identifier
  }

  secrets {
    name  = "WEBHOOK_SHARED_SECRET"
    value = var.webhook_shared_secret
  }
}

# Bind Action to trigger
resource "auth0_trigger_actions" "post_user_registration" {
  count = var.enable_post_registration_action ? 1 : 0

  trigger = "post-user-registration"

  actions {
    id           = auth0_action.post_user_registration[0].id
    display_name = auth0_action.post_user_registration[0].name
  }
}

# Post-Login Action: Add roles to tokens
resource "auth0_action" "post_login" {
  count = var.enable_post_login_action ? 1 : 0

  name    = "${var.name_prefix}-post-login"
  runtime = "node22"
  deploy  = true

  supported_triggers {
    id      = "post-login"
    version = "v3"
  }

  code = templatefile("${path.module}/actions/post-login.js.tpl", {
    namespace = var.custom_claims_namespace
  })
}


# Post-Login Action: Block Non-Admin Users from ALB OIDC Application
resource "auth0_action" "alb_admin_only" {
  count = var.enable_alb_admin_only_action ? 1 : 0

  name    = "${var.name_prefix}-alb-admin-only"
  runtime = "node22"
  deploy  = true

  supported_triggers {
    id      = "post-login"
    version = "v3"
  }

  code = templatefile("${path.module}/actions/alb-admin-only.js.tpl", {
    namespace     = var.custom_claims_namespace
    alb_client_id = auth0_client.alb.client_id
  })

  depends_on = [auth0_client.alb]
}

# Bind Post-Login Actions to trigger
# This includes both the role assignment action and the ALB admin-only action
resource "auth0_trigger_actions" "post_login" {
  count = var.enable_post_login_action ? 1 : 0

  trigger = "post-login"

  # Action 1: Add roles to tokens (must run first)
  actions {
    id           = auth0_action.post_login[0].id
    display_name = auth0_action.post_login[0].name
  }

  # Action 2: Block non-admin users from ALB application (runs after roles are set)
  dynamic "actions" {
    for_each = var.enable_alb_admin_only_action ? [1] : []
    content {
      id           = auth0_action.alb_admin_only[0].id
      display_name = auth0_action.alb_admin_only[0].name
    }
  }
}

# ============================================================================
# DATA SOURCES
# ============================================================================

data "auth0_tenant" "current" {}

# Get Cloudflare zone information
data "cloudflare_zones" "domain" {
  name = var.cloudflare_zone_name
}

# ============================================================================
# CUSTOM DOMAIN
# ============================================================================

# Configure Auth0 custom domain for branded authentication
resource "auth0_custom_domain" "main" {
  domain = var.auth0_custom_domain
  type   = "auth0_managed_certs" # Auth0 manages SSL certificates

  # Auth0 will automatically verify via CNAME once DNS is configured
}

# Create CNAME record in Cloudflare pointing to Auth0
# This is DNS-only (not proxied) as required by Auth0
resource "cloudflare_dns_record" "auth0_custom_domain" {
  zone_id = data.cloudflare_zones.domain.result[0].id
  name    = split(".", var.auth0_custom_domain)[0] # Extract subdomain (e.g., "auth" from "auth.trigpointing.me")
  content = auth0_custom_domain.main.verification[0].methods[0].record
  type    = "CNAME"
  proxied = false # MUST be false for Auth0 custom domains
  ttl     = 1     # Auto TTL

  comment = "Auth0 custom domain for ${var.environment} - managed by Terraform"
}

# ============================================================================
# PROMPT CONFIGURATION (for Identifier First flow required by passkeys)
# ============================================================================

resource "auth0_prompt" "identifier_first" {
  identifier_first               = true  # Enable Identifier First flow (required for passkeys)
  webauthn_platform_first_factor = false # Use standard passkey flow, not enterprise biometrics
}

# ============================================================================
# SES SMTP USER (per environment)
# ============================================================================

# IAM user for SES SMTP access (dedicated per environment)
resource "aws_iam_user" "smtp_auth0" {
  name = "${var.name_prefix}-smtp-auth0"

  tags = {
    Name        = "${var.name_prefix}-smtp-auth0"
    Environment = var.environment
    Purpose     = "Auth0 SES SMTP access"
  }
}

# IAM policy to allow SES sending
resource "aws_iam_user_policy" "smtp_auth0_policy" {
  name = "${var.name_prefix}-smtp-auth0-ses-policy"
  user = aws_iam_user.smtp_auth0.name

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "ses:SendEmail",
          "ses:SendRawEmail"
        ]
        Resource = "*"
        Condition = {
          StringEquals = {
            "ses:FromAddress" = var.from_email
          }
        }
      }
    ]
  })
}

# Generate SMTP credentials
resource "aws_iam_access_key" "smtp_auth0_credentials" {
  user = aws_iam_user.smtp_auth0.name
}

# ============================================================================
# EMAIL PROVIDER
# ============================================================================

# Configure custom SMTP email provider (AWS SES)
resource "auth0_email_provider" "ses" {
  name                 = "smtp"
  enabled              = true
  default_from_address = var.from_email

  credentials {
    smtp_host = var.smtp_host
    smtp_port = var.smtp_port
    smtp_user = aws_iam_access_key.smtp_auth0_credentials.id
    smtp_pass = aws_iam_access_key.smtp_auth0_credentials.ses_smtp_password_v4
  }
}

# ============================================================================
# BRANDING
# ============================================================================

# Configure Auth0 Universal Login branding
# NOTE: Branding is a PAID Auth0 feature. Free/developer plans cannot manage
# branding via API (even read operations fail). Configure branding manually
# in the Auth0 dashboard for free tier tenants.
#
# resource "auth0_branding" "main" {
#   logo_url = var.logo_url
#
#   colors {
#     primary         = var.primary_color
#     page_background = var.page_background_color
#   }
# }

# ============================================================================
# TENANT CONFIGURATION
# ============================================================================

# Configure tenant to use custom domain for emails and notifications
resource "auth0_tenant" "main" {
  # Friendly name
  friendly_name = "Trigpointing UK - ${title(var.environment)}"

  # Picture URL
  picture_url = var.logo_url

  # Support contact
  support_email = var.from_email
  support_url   = var.environment == "production" ? "https://www.trigpointing.uk" : "https://www.trigpointing.me"

  # Flags for custom domain usage
  flags {
    # Use custom domain in emails instead of tenant domain
    enable_custom_domain_in_emails = true
  }
}
