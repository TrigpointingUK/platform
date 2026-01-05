# Auth0 Configuration for Staging (trigpointing.me)
#
# Copy this file to auth0.auto.tfvars and fill in the actual values
# DO NOT COMMIT auth0.auto.tfvars - it's gitignored

# Auth0 Tenant Domain (for Management API)
# This is the default Auth0 domain, e.g., trigpointing-staging.eu.auth0.com
auth0_tenant_domain = "your-staging-tenant.eu.auth0.com"

# Auth0 Custom Domain (for user-facing authentication)
# This is your branded domain, e.g., auth.trigpointing.me
auth0_custom_domain = "auth.trigpointing.me"

# Auth0 Provider Credentials (for Terraform to manage Auth0)
# These are for the "terraform-provider" M2M application
# These can be set here or via environment variables
auth0_terraform_client_id     = "YOUR_TERRAFORM_PROVIDER_CLIENT_ID"
auth0_terraform_client_secret = "YOUR_TERRAFORM_PROVIDER_CLIENT_SECRET"

# Environment variables alternative:
#   export AUTH0_DOMAIN="your-staging-tenant.eu.auth0.com"
#   export AUTH0_CLIENT_ID="your_terraform_provider_client_id"
#   export AUTH0_CLIENT_SECRET="your_terraform_provider_client_secret"

# Auth0 M2M Client Secret (tme-api application)
# This is the client secret for the "tme-api" M2M application that Auth0 Actions use
# to authenticate to your FastAPI API.
# 
# To rotate this secret:
#   1. Go to Auth0 Dashboard > Applications > tme-api
#   2. Click "Settings" tab
#   3. Scroll to "Application Credentials" and click "Rotate"
#   4. Copy the new secret and paste it here
auth0_m2m_client_secret = "YOUR_M2M_API_CLIENT_SECRET"

slack_webhook_url = "https://hooks.slack.com/services/blah/blah/blah"
