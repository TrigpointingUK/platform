# Auth0 Module Variables

variable "environment" {
  description = "Environment name (staging or production)"
  type        = string
  validation {
    condition     = contains(["staging", "production"], var.environment)
    error_message = "Environment must be either 'staging' or 'production'."
  }
}

variable "name_prefix" {
  description = "Prefix for Auth0 resource names (e.g., tme, tuk)"
  type        = string
}

variable "auth0_m2m_client_secret" {
  description = "M2M client secret for Auth0 Actions (sensitive - rotate manually in Auth0 if needed)"
  type        = string
  sensitive   = true
}

variable "auth0_custom_domain" {
  description = "Auth0 custom domain for user-facing authentication (e.g., auth.trigpointing.me)"
  type        = string
}

variable "cloudflare_zone_name" {
  description = "Cloudflare zone name for DNS records (e.g., trigpointing.me)"
  type        = string
}

variable "database_connection_name" {
  description = "Name of the Auth0 database connection"
  type        = string
}

variable "disable_signup" {
  description = "Whether to disable public signup on the database connection"
  type        = bool
  default     = false
}

variable "api_name" {
  description = "Name of the API resource server"
  type        = string
}

variable "api_identifier" {
  description = "API identifier (audience)"
  type        = string
}

variable "fastapi_url" {
  description = "FastAPI base URL for webhook"
  type        = string
}

variable "webhook_shared_secret" {
  description = "Shared secret for Auth0 webhook fallback authentication (when M2M quota exhausted)"
  type        = string
  default     = ""
  sensitive   = true
}

variable "swagger_callback_urls" {
  description = "List of Swagger OAuth2 callback URLs"
  type        = list(string)
  default     = []
}

variable "swagger_allowed_origins" {
  description = "List of allowed origins for Swagger UI"
  type        = list(string)
  default     = []
}

variable "web_spa_callback_urls" {
  description = "List of web SPA callback URLs"
  type        = list(string)
  default     = []
}

variable "web_spa_allowed_origins" {
  description = "List of allowed origins for web SPA"
  type        = list(string)
  default     = []
}

variable "website_callback_urls" {
  description = "List of website callback URLs"
  type        = list(string)
  default     = []
}

variable "forum_callback_urls" {
  description = "List of forum callback URLs"
  type        = list(string)
  default     = []
}

variable "forum_logout_urls" {
  description = "List of forum logout URLs"
  type        = list(string)
  default     = []
}

variable "wiki_callback_urls" {
  description = "List of wiki callback URLs"
  type        = list(string)
  default     = []
}

variable "wiki_logout_urls" {
  description = "List of wiki logout URLs"
  type        = list(string)
  default     = []
}

variable "android_callback_urls" {
  description = "List of Android app callback URLs"
  type        = list(string)
  default     = []
}

variable "android_logout_urls" {
  description = "List of Android app logout URLs"
  type        = list(string)
  default     = []
}

variable "android_web_origins" {
  description = "List of Android app web origins"
  type        = list(string)
  default     = []
}

variable "enable_forum" {
  description = "Whether to create the forum application"
  type        = bool
  default     = false
}

variable "enable_wiki" {
  description = "Whether to create the wiki application"
  type        = bool
  default     = false
}

variable "enable_post_registration_action" {
  description = "Whether to enable the post-registration Action"
  type        = bool
  default     = true
}

variable "enable_post_login_action" {
  description = "Whether to enable the post-login Action for adding roles to tokens"
  type        = bool
  default     = true
}

variable "custom_claims_namespace" {
  description = "Namespace for custom claims in tokens (must be a valid URI)"
  type        = string
  default     = "https://trigpointing.uk/"
}

variable "enable_alb_admin_only_action" {
  description = "Whether to enable the post-login Action to block non-admin users from ALB OIDC application"
  type        = bool
  default     = true
}

variable "api_admin_role_name" {
  description = "Name of the API admin role"
  type        = string
  default     = "api-admin"
}

variable "wiki_admin_role_name" {
  description = "Name of the wiki admin role"
  type        = string
  default     = "wiki-admin"
}

variable "forum_admin_role_name" {
  description = "Name of the forum admin role"
  type        = string
  default     = "forum-admin"
}

# Email Provider Configuration
variable "smtp_host" {
  description = "SMTP server hostname (e.g., email-smtp.eu-west-1.amazonaws.com)"
  type        = string
}

variable "smtp_port" {
  description = "SMTP server port (587 for TLS)"
  type        = number
  default     = 587
}

variable "from_email" {
  description = "From email address for Auth0 emails"
  type        = string
}

variable "from_name" {
  description = "From name for Auth0 emails"
  type        = string
  default     = "Trigpointing UK"
}

# Branding Configuration
variable "logo_url" {
  description = "URL to the company logo for Auth0 branding (must be HTTPS)"
  type        = string
}

variable "primary_color" {
  description = "Primary color for Auth0 branding (hex format)"
  type        = string
  default     = "#005f00"
}

variable "page_background_color" {
  description = "Page background color for Auth0 branding (hex format)"
  type        = string
  default     = "#ffffff"
}

