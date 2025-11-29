# Staging Site OIDC Protection

## Overview

The staging site (`trigpointing.me`) is now protected by Auth0 OIDC authentication using the **production Auth0 tenant** (`auth.trigpointing.uk`). This replaces the previous Cloudflare IP-based security rule with proper OAuth2 authentication.

## Architecture

- **Auth0 Tenant**: Production (`auth.trigpointing.uk`)
- **Auth0 Application**: `tuk-aws-alb` (shared with other admin tools)
- **Required Role**: `api-admin`
- **ALB OIDC Config**: Uses existing `trigpointing-alb-oidc-config` secret
- **Protected Domain**: `trigpointing.me`

## Benefits

✅ No need to maintain IP whitelists
✅ Proper authentication instead of IP-based restrictions
✅ Anyone with `api-admin` role can access staging
✅ Consistent security model with other admin tools (cache, phpmyadmin, preview)
✅ No additional secrets or configuration needed

## Implementation Details

### 1. Auth0 Configuration

The production `tuk-aws-alb` Auth0 application now includes:

**Callback URLs:**
- `https://cache.trigpointing.uk/oauth2/idpresponse`
- `https://phpmyadmin.trigpointing.uk/oauth2/idpresponse`
- `https://pgadmin.trigpointing.uk/oauth2/idpresponse`
- `https://preview.trigpointing.uk/oauth2/idpresponse`
- `https://trigpointing.me/oauth2/idpresponse` ← **NEW**

**Logout URLs:**
- `https://cache.trigpointing.uk`
- `https://phpmyadmin.trigpointing.uk`
- `https://pgadmin.trigpointing.uk`
- `https://preview.trigpointing.uk`
- `https://trigpointing.me` ← **NEW**

### 2. ALB Listener Rule

The staging SPA now uses a custom ALB listener rule with two actions:
1. **Authenticate via OIDC** (order 1) - redirects to Auth0 for login
2. **Forward to target group** (order 2) - serves the SPA after authentication

Priority: 50 (same as configured in the SPA module)

### 3. Auth0 Post-Login Action

The existing "ALB Admin Only" Action automatically checks:
- If the request is for the `tuk-aws-alb` application
- If the user has the `api-admin` role
- Denies access if the role is missing

## Deployment Steps

### Step 1: Apply Production Auth0 Changes

First, update the production Auth0 configuration to add the staging callback:

```bash
cd terraform/production
terraform plan  # Review that tuk-aws-alb client will be updated
terraform apply
```

**Expected changes:**
- `auth0_client.alb` will be updated in-place
- Callbacks will include `https://trigpointing.me/oauth2/idpresponse`
- Logout URLs will include `https://trigpointing.me`

### Step 2: Apply Staging Changes

Next, update the staging environment to add OIDC protection:

```bash
cd ../staging
terraform plan  # Review that new listener rule will be created
terraform apply
```

**Expected changes:**
- `aws_lb_listener_rule.spa_staging_oidc` will be created
- Priority 50 with authenticate-oidc action

### Step 3: Remove Cloudflare Security Rule

Once the OIDC protection is active and tested, you can remove the Cloudflare IP restriction rule for `trigpointing.me`.

### Step 4: Test Access

1. **Test as admin**:
   - Visit `https://trigpointing.me`
   - Should redirect to `https://auth.trigpointing.uk` for login
   - Login with a production account that has `api-admin` role
   - Should be granted access to the staging site

2. **Test as non-admin** (optional):
   - Login with an account without `api-admin` role
   - Should see "Access to admin tools requires api-admin role" error

## Troubleshooting

### Issue: "Invalid callback URL"

**Cause**: Auth0 callback URL not configured
**Solution**: Ensure Step 1 (production terraform) was applied successfully

### Issue: "Access denied - api-admin role required"

**Cause**: User doesn't have the required role
**Solution**: Assign `api-admin` role to the user in Auth0 Dashboard

### Issue: Redirect loop

**Cause**: OIDC config secret might be incorrect
**Solution**: Verify `trigpointing-alb-oidc-config` secret in AWS Secrets Manager

## Files Modified

1. `terraform/modules/auth0/main.tf` - Added staging callbacks to ALB application
2. `terraform/staging/spa.tf` - Added OIDC listener rule
3. `terraform/common/alb-oidc-secrets.tf` - Updated description

## Security Considerations

- **Environment Mixing**: Staging uses production Auth0 tenant
  - This is acceptable since access is restricted to admins only
  - Staging users don't exist - only production admin accounts can access
  
- **Role Requirement**: Only users with `api-admin` role can access
  - Same restriction as cache.trigpointing.uk and preview.trigpointing.uk
  - Enforced by Auth0 Post-Login Action
  
- **Session Management**: ALB manages OAuth2 sessions
  - Session timeout: 3600 seconds (1 hour)
  - Cookie name: `AWSELBAuthSessionCookie`

## Related Documentation

- [ALB OIDC Setup Guide](./ALB_OIDC_SETUP.md)
- [ALB OIDC Deployment](./ALB_OIDC_DEPLOYMENT.md)
- [Auth0 Module README](../modules/auth0/README.md)

