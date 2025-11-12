# ALB OIDC Authentication Setup Guide

This guide explains how to set up OIDC authentication for admin tools (Redis Commander and phpMyAdmin) using AWS ALB and Auth0.

## Overview

The following admin tools and preview sites are now protected by Auth0 OIDC authentication via AWS ALB:
- **cache.trigpointing.uk** - Redis Commander (Valkey management interface)
- **phpmyadmin.trigpointing.uk** - phpMyAdmin (MySQL database management)
- **preview.trigpointing.uk** - Production SPA preview/smoke testing environment

Only users with the `api-admin` role can access these tools.

## Architecture

1. User attempts to access `cache.trigpointing.uk`, `phpmyadmin.trigpointing.uk`, or `preview.trigpointing.uk`
2. AWS ALB intercepts the request and redirects to Auth0 for authentication
3. User logs in with Auth0
4. Auth0 Post-Login Action checks if user has `api-admin` role
5. If user lacks `api-admin` role, access is denied
6. If user has `api-admin` role, Auth0 returns OIDC token to ALB
7. ALB forwards authenticated request to backend service

## Prerequisites

- Auth0 tenant with custom domain configured
- AWS Secrets Manager access
- Terraform access to common infrastructure
- `api-admin` role assigned to yourself in Auth0 for testing

## Setup Steps

### 1. Create Auth0 Application for ALB

1. Go to Auth0 Dashboard → Applications → Create Application
2. Name: `aws-alb`
3. Type: **Regular Web Application**
4. Click "Create"

### 2. Configure Application Settings

In the application settings:

**Allowed Callback URLs:**
```
https://cache.trigpointing.uk/oauth2/idpresponse
https://phpmyadmin.trigpointing.uk/oauth2/idpresponse
https://preview.trigpointing.uk/oauth2/idpresponse
```

**Allowed Logout URLs:**
```
https://cache.trigpointing.uk
https://phpmyadmin.trigpointing.uk
https://preview.trigpointing.uk
```

**Allowed Web Origins:** (leave empty)

**Grant Types:**
- Authorization Code
- Refresh Token

**Advanced Settings → Grant Types:**
- Ensure "Authorization Code" and "Refresh Token" are checked

**Advanced Settings → OAuth:**
- JsonWebToken Signature Algorithm: `RS256`

**Save Changes**

### 3. Note Application Credentials

From the Auth0 application settings page, note:
- **Client ID** (e.g., `ABC123xyz...`)
- **Client Secret** (click "Show" to reveal)

### 4. Get Auth0 OIDC Endpoints

Your Auth0 custom domain is: `https://auth.trigpointing.uk`

The OIDC endpoints are:
- **Issuer**: `https://auth.trigpointing.uk`
- **Authorization Endpoint**: `https://auth.trigpointing.uk/authorize`
- **Token Endpoint**: `https://auth.trigpointing.uk/oauth/token`
- **User Info Endpoint**: `https://auth.trigpointing.uk/userinfo`

### 5. Update AWS Secrets Manager

Update the AWS Secrets Manager secret `trigpointing-alb-oidc-config` with the following JSON:

```bash
aws secretsmanager put-secret-value \
  --secret-id trigpointing-alb-oidc-config \
  --secret-string '{
    "issuer": "https://auth.trigpointing.uk",
    "authorization_endpoint": "https://auth.trigpointing.uk/authorize",
    "token_endpoint": "https://auth.trigpointing.uk/oauth/token",
    "user_info_endpoint": "https://auth.trigpointing.uk/userinfo",
    "client_id": "YOUR_CLIENT_ID_HERE",
    "client_secret": "YOUR_CLIENT_SECRET_HERE"
  }' \
  --region eu-west-1
```

**Replace:**
- `YOUR_CLIENT_ID_HERE` with the actual Client ID from step 3
- `YOUR_CLIENT_SECRET_HERE` with the actual Client Secret from step 3

### 6. Update Terraform Variables

Add the ALB client ID to your terraform variables:

**For Production** (`terraform/production/production.auto.tfvars` or similar):
```hcl
auth0_alb_client_id = "YOUR_CLIENT_ID_HERE"
```

**For Staging** (`terraform/staging/staging.auto.tfvars` or similar):
```hcl
auth0_alb_client_id = "YOUR_CLIENT_ID_HERE"
```

### 7. Apply Terraform Changes

#### Common Infrastructure (Redis Commander, phpMyAdmin, Secrets)
```bash
cd terraform/common
terraform plan
# Review the changes - should see:
# - aws_secretsmanager_secret.alb_oidc (create)
# - aws_lb_listener_rule.valkey_commander (modify - add OIDC action)
# - aws_lb_listener_rule.phpmyadmin (modify - add OIDC action)
terraform apply
```

#### Production (Auth0 Action)
```bash
cd terraform/production
terraform plan
# Review the changes - should see:
# - auth0_action.alb_admin_only (create)
# - auth0_trigger_actions.post_login (modify - add action)
terraform apply
```

#### Staging (Auth0 Action)
```bash
cd terraform/staging
terraform plan
terraform apply
```

## Testing

### 1. Test Access Without Admin Role

1. Create a test user in Auth0 (or use an existing non-admin user)
2. **Do NOT** assign `api-admin` role to this user
3. Navigate to `https://cache.trigpointing.uk`
4. You should be redirected to Auth0 login
5. After logging in, you should see an error: "Access to admin tools requires api-admin role."

### 2. Test Access With Admin Role

1. Assign `api-admin` role to your user in Auth0:
   - Auth0 Dashboard → User Management → Users
   - Find your user → Roles tab → Assign Roles
   - Select `api-admin` → Assign
2. Log out from `cache.trigpointing.uk` (clear cookies or use incognito)
3. Navigate to `https://cache.trigpointing.uk`
4. You should be redirected to Auth0 login
5. After logging in, you should be redirected back and see Redis Commander interface
6. Repeat for `https://phpmyadmin.trigpointing.uk`

## Troubleshooting

### Error: "Authorization Required" (after successful Auth0 login)

**Cause:** The issuer in Secrets Manager doesn't match Auth0's issuer format (missing trailing slash).

**Solution:**
1. Check Auth0's actual issuer: `curl https://auth.trigpointing.uk/.well-known/openid-configuration | jq .issuer`
2. The issuer **MUST** have a trailing slash: `https://auth.trigpointing.uk/` (not `https://auth.trigpointing.uk`)
3. Update the secret with the correct format:
```bash
aws secretsmanager put-secret-value \
  --secret-id trigpointing-alb-oidc-config \
  --secret-string '{
    "issuer": "https://auth.trigpointing.uk/",
    "authorization_endpoint": "https://auth.trigpointing.uk/authorize",
    "token_endpoint": "https://auth.trigpointing.uk/oauth/token",
    "user_info_endpoint": "https://auth.trigpointing.uk/userinfo",
    "client_id": "YOUR_CLIENT_ID",
    "client_secret": "YOUR_CLIENT_SECRET"
  }' \
  --region eu-west-1
```

### Error: "Invalid redirect_uri"

**Cause:** The callback URL in Auth0 doesn't match what ALB is sending.

**Solution:** 
1. Check Auth0 application settings → Allowed Callback URLs
2. Ensure exact match: `https://cache.trigpointing.uk/oauth2/idpresponse`

### Error: "Unauthorized_client"

**Cause:** Grant types not enabled in Auth0 application.

**Solution:**
1. Auth0 Dashboard → Applications → aws-alb
2. Advanced Settings → Grant Types
3. Enable "Authorization Code" and "Refresh Token"

### Error: "Access denied" after successful login

**Cause:** User doesn't have `api-admin` role.

**Solution:**
1. Auth0 Dashboard → User Management → Users → Your User
2. Roles tab → Assign Roles → Select `api-admin`

### ALB returns 500 Internal Server Error

**Cause:** OIDC configuration in Secrets Manager is incorrect.

**Solution:**
1. Verify secret exists: `aws secretsmanager get-secret-value --secret-id trigpointing-alb-oidc-config --region eu-west-1`
2. Check JSON is valid and all fields are correct
3. Update secret if needed (step 5 above)

### Redis Commander shows blank page

**Cause:** This is normal after removing HTTP auth - the OIDC authentication happens at ALB level.

**Solution:** No action needed - ALB handles authentication before request reaches Redis Commander.

## Security Notes

### What Changed

**Before:**
- Redis Commander protected by plaintext password in Terraform
- phpMyAdmin accessible via plain HTTP (protected only by CloudFlare)

**After:**
- Redis Commander has no authentication (relies on ALB)
- phpMyAdmin has no authentication (relies on ALB)
- ALB OIDC intercepts ALL requests before they reach services
- Only `api-admin` users can authenticate

### Security Considerations

1. **Secrets Management**: OIDC credentials stored in AWS Secrets Manager (encrypted at rest)
2. **Network Security**: Services only accessible via ALB, not directly
3. **Role-Based Access**: Auth0 Action enforces `api-admin` role requirement
4. **Session Management**: ALB manages session cookies (1 hour timeout)
5. **HTTPS Only**: All communication over TLS via CloudFlare

### Credential Rotation

To rotate Auth0 credentials:

1. Generate new client secret in Auth0 Dashboard
2. Update Secrets Manager with new secret
3. No Terraform changes needed (secret is ignored after creation)
4. Old sessions remain valid until expiry (1 hour)

## Monitoring

### CloudWatch Logs

ALB authentication logs:
```bash
aws logs tail /aws/elasticloadbalancing/trigpointing-alb --follow --region eu-west-1
```

Auth0 Action logs:
- Auth0 Dashboard → Monitoring → Logs
- Filter by Action: "alb-admin-only"

### Access Audit

To see who accessed admin tools:
- Auth0 Dashboard → Monitoring → Logs
- Filter by Application: "aws-alb"
- Filter by Success: "Success Logins"

## Reverting Changes (Emergency)

If OIDC authentication causes issues and you need immediate access:

### Temporary Bypass (NOT RECOMMENDED for production)

1. Comment out the `authenticate-oidc` action in terraform:
```hcl
# In terraform/common/valkey.tf and phpmyadmin.tf
resource "aws_lb_listener_rule" "valkey_commander" {
  # action {
  #   type = "authenticate-oidc"
  #   ...
  # }
  
  action {
    type             = "forward"
    target_group_arn = module.valkey.valkey_commander_target_group_arn
  }
}
```

2. Apply terraform:
```bash
cd terraform/common
terraform apply
```

### Restore HTTP Auth to Redis Commander (Better option)

1. Add back password to `terraform/modules/valkey/main.tf`:
```hcl
command = [
  "node", "./bin/redis-commander",
  "--redis-host", "localhost",
  "--redis-port", "6379",
  "--http-auth-username", "admin",
  "--http-auth-password", "TEMPORARY-PASSWORD-HERE"
]
```

2. Apply changes:
```bash
cd terraform/common
terraform apply
```

3. Force ECS task recreation to pick up new password

## Additional Resources

- [AWS ALB OIDC Authentication Docs](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/listener-authenticate-users.html)
- [Auth0 OIDC Documentation](https://auth0.com/docs/authenticate/protocols/openid-connect-protocol)
- [Auth0 Actions Documentation](https://auth0.com/docs/customize/actions)

## Support

For issues with this setup:
1. Check CloudWatch logs for ALB errors
2. Check Auth0 logs for authentication failures  
3. Verify Secrets Manager secret is correctly formatted
4. Test with a known admin user
5. Open an issue on GitHub with logs (redact sensitive info)

