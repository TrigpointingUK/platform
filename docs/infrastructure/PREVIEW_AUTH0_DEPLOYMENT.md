# Adding Auth0 Protection to preview.trigpointing.uk

This document explains how to deploy Auth0 OIDC authentication for the `preview.trigpointing.uk` domain.

## Overview

The `preview.trigpointing.uk` domain now sits behind Auth0 authentication in the ALB, similar to `cache.trigpointing.uk` and `phpmyadmin.trigpointing.uk`. This ensures that only users with the `api-admin` role can access the production preview environment.

## Changes Made

### Terraform Changes

1. **Module Updates** (`terraform/modules/spa-ecs-service/`)
   - Added `create_listener_rule` variable to optionally skip listener rule creation
   - Made the ALB listener rule conditional based on this variable

2. **Production SPA Configuration** (`terraform/production/spa.tf`)
   - Set `create_listener_rule = false` to disable module's default listener rule
   - Created custom `aws_lb_listener_rule.spa_preview` with OIDC authentication
   - Uses the same Auth0 configuration as cache and phpmyadmin

3. **Common Infrastructure** (`terraform/common/`)
   - Added `alb_oidc_config` output to expose OIDC configuration to production
   - Updated ALB OIDC secret description to include preview.trigpointing.uk

4. **Documentation** (`docs/infrastructure/ALB_OIDC_SETUP.md`)
   - Updated to include preview.trigpointing.uk in the list of protected domains
   - Updated callback and logout URLs

## Deployment Steps

### Step 1: Update Auth0 Application Callback URLs

1. Go to [Auth0 Dashboard](https://manage.auth0.com)
2. Navigate to **Applications** → **aws-alb**
3. Update **Allowed Callback URLs** to include:
   ```
   https://cache.trigpointing.uk/oauth2/idpresponse
   https://phpmyadmin.trigpointing.uk/oauth2/idpresponse
   https://preview.trigpointing.uk/oauth2/idpresponse
   ```

4. Update **Allowed Logout URLs** to include:
   ```
   https://cache.trigpointing.uk
   https://phpmyadmin.trigpointing.uk
   https://preview.trigpointing.uk
   ```

5. Click **Save Changes**

### Step 2: Apply Terraform Changes

#### 2a. Common Infrastructure

```bash
cd terraform/common
terraform plan
# Review the changes - should see:
# - Modified: aws_secretsmanager_secret.alb_oidc (description updated)
# - New output: alb_oidc_config
terraform apply
```

#### 2b. Production Environment

```bash
cd terraform/production
terraform plan
# Review the changes - should see:
# - Modified: module.spa_ecs_service (create_listener_rule = false)
# - Destroyed: module.spa_ecs_service.aws_lb_listener_rule.spa[0] (conditional)
# - Created: aws_lb_listener_rule.spa_preview (with OIDC auth)
terraform apply
```

### Step 3: Verify Configuration

1. **Check ALB Listener Rules**:
   ```bash
   aws elbv2 describe-rules \
     --listener-arn $(aws elbv2 describe-listeners \
       --load-balancer-arn $(aws elbv2 describe-load-balancers \
         --names trigpointing-alb --query 'LoadBalancers[0].LoadBalancerArn' --output text) \
       --query 'Listeners[?Port==`443`].ListenerArn' --output text) \
     --query 'Rules[?Priority==`55`]' \
     --region eu-west-1
   ```

   You should see a rule with:
   - Priority: 55
   - Actions: `authenticate-oidc`, then `forward`
   - Condition: host-header = preview.trigpointing.uk

2. **Test Authentication Flow**:
   ```bash
   # Visit in a browser (will redirect to Auth0)
   open https://preview.trigpointing.uk
   ```

   Expected behavior:
   - Redirects to Auth0 login (auth.trigpointing.uk)
   - After login, if you have `api-admin` role, you'll be redirected back to preview.trigpointing.uk
   - If you don't have `api-admin` role, Auth0 Post-Login Action will deny access

3. **Check CloudWatch Logs**:
   ```bash
   # Monitor for authentication events
   aws logs tail /aws/elasticloadbalancing/trigpointing-alb --follow --region eu-west-1
   ```

## Architecture

```
User → CloudFlare (HTTPS) → ALB (port 443)
  ├─ Host: preview.trigpointing.uk (priority 55)
  │   ├─ Action 1 (order=1): Authenticate OIDC (Auth0)
  │   │   ├─ Issuer: https://auth.trigpointing.uk/
  │   │   ├─ Client: aws-alb application
  │   │   └─ Scope: openid profile email
  │   └─ Action 2 (order=2): Forward to SPA target group
  │       └─ ECS Service: trigpointing-spa-production
  ├─ Host: cache.trigpointing.uk (priority 150)
  │   └─ [Same OIDC pattern]
  └─ Host: phpmyadmin.trigpointing.uk (priority 125)
      └─ [Same OIDC pattern]
```

## Security Considerations

1. **Same Auth0 Application**: All three domains use the same Auth0 `aws-alb` application
2. **Same Role Requirement**: All require `api-admin` role via Auth0 Post-Login Action
3. **Session Management**: ALB manages session cookies with 1-hour timeout
4. **HTTPS Only**: All communication over TLS via CloudFlare
5. **Network Isolation**: SPA ECS tasks run in private subnets

## Rollback Procedure

If you need to remove Auth0 protection and restore direct access:

1. **Update `terraform/production/spa.tf`**:
   ```hcl
   # In module.spa_ecs_service
   create_listener_rule = true  # Change from false to true
   
   # Comment out or remove the custom listener rule
   # resource "aws_lb_listener_rule" "spa_preview" { ... }
   ```

2. **Apply Terraform**:
   ```bash
   cd terraform/production
   terraform apply
   ```

This will restore the simple forwarding rule without OIDC authentication.

## Testing Checklist

- [ ] Auth0 aws-alb application has preview.trigpointing.uk callbacks configured
- [ ] Common infrastructure applied successfully
- [ ] Production infrastructure applied successfully
- [ ] ALB listener rule priority 55 exists with OIDC action
- [ ] Visiting preview.trigpointing.uk redirects to Auth0 login
- [ ] User with `api-admin` role can successfully access after login
- [ ] User without `api-admin` role is denied access
- [ ] Session persists for 1 hour (no re-authentication required)
- [ ] Logout redirects work correctly

## Related Documentation

- [ALB OIDC Setup Guide](./ALB_OIDC_SETUP.md) - General setup guide for ALB OIDC
- [Auth0 Actions](../../terraform/modules/auth0/actions/) - Post-Login Action code

## Troubleshooting

### Issue: "No matching host configured" error

**Cause**: Listener rule not created or wrong priority

**Solution**:
```bash
# Check listener rules
aws elbv2 describe-rules --listener-arn <LISTENER_ARN> --region eu-west-1
```

### Issue: Infinite redirect loop

**Cause**: Callback URL not configured in Auth0

**Solution**: Verify callback URLs in Auth0 Dashboard → aws-alb application settings

### Issue: Access denied after login

**Cause**: User doesn't have `api-admin` role

**Solution**: 
1. Check Auth0 Dashboard → Users → [Your User] → Roles
2. Assign `api-admin` role if needed
3. Check Auth0 Logs to see why Action denied access

### Issue: "Invalid client" error

**Cause**: OIDC secret misconfigured in Secrets Manager

**Solution**:
```bash
# Check current secret value
aws secretsmanager get-secret-value \
  --secret-id trigpointing-alb-oidc-config \
  --region eu-west-1 \
  --query SecretString --output text | jq .

# Verify client_id and client_secret match Auth0 application
```

