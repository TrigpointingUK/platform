# Deploy SES IAM Permissions Fix

**Date**: 30 November 2025  
**Priority**: High  
**Impact**: Contact form currently non-functional without this fix

## Issue

The contact form is failing with an IAM permissions error:
```
User 'arn:aws:sts::534526983272:assumed-role/trigpointing-ecs-task-role/...' 
is not authorized to perform 'ses:SendEmail' on resource 
'arn:aws:ses:eu-west-1:534526983272:identity/trigpointing.uk'
```

## Solution

Add SES permissions to the ECS task role via Terraform.

## Prerequisites

1. ✅ Code changes already deployed (commit `592a50f`)
2. ✅ Terraform changes committed (commit `3d8879b`)
3. 🔲 Need to apply Terraform changes to common infrastructure

## Deployment Steps

### 1. Review the Changes

The Terraform change adds SES permissions to `terraform/common/ecs.tf`:

```hcl
{
  Effect = "Allow"
  Action = [
    "ses:SendEmail",
    "ses:SendRawEmail"
  ]
  Resource = [
    "arn:aws:ses:eu-west-1:*:identity/trigpointing.uk",
    "arn:aws:ses:eu-west-1:*:identity/trigpointing.me",
    "arn:aws:ses:eu-west-1:*:identity/trigpointing@teasel.org",
    "arn:aws:ses:eu-west-1:*:identity/ian@teasel.org"
  ]
}
```

### 2. Apply Terraform Changes

```bash
# Pull latest changes
git pull origin develop

# Navigate to common infrastructure
cd terraform/common

# Initialize Terraform (if needed)
terraform init

# Review the planned changes
terraform plan

# Expected output should show:
# - aws_iam_role_policy.ecs_task_role_policy will be updated in-place
# - Only the policy document should change (SES permissions added)

# Apply the changes
terraform apply

# Type 'yes' when prompted
```

### 3. Verify the Fix

After applying, test the contact form:

```bash
# Production API
curl -X POST https://api.trigpointing.uk/v1/admin/contact \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test User",
    "email": "test@example.com",
    "subject": "Test Contact Form",
    "message": "Testing that the contact form works after IAM fix"
  }'

# Expected response:
# {
#   "success": true,
#   "message": "Your message has been sent successfully. We'll get back to you soon!"
# }
```

Check the logs for successful email send:
```bash
# Check CloudWatch logs for the FastAPI service
# Look for: "event": "contact_email_sent"
```

### 4. Check Email Delivery

Verify that the email was delivered to `trigpointing@teasel.org`.

## Rollback Plan

If issues occur, rollback is simple:

```bash
cd terraform/common
git checkout 592a50f~1 -- ecs.tf
terraform apply
```

This will remove the SES permissions from the ECS task role.

## Impact Analysis

### What Changes
- **IAM Policy**: `trigpointing-ecs-task-role` policy updated
- **Permissions Added**: `ses:SendEmail` and `ses:SendRawEmail`
- **Resources**: Access to verified SES identities

### What Doesn't Change
- No ECS service restarts required
- No application code changes required
- No environment variables changed
- No database changes

### Environments Affected
- **Common infrastructure**: All environments share the ECS task role
- **Staging**: Contact form will work after Terraform apply
- **Production**: Contact form will work after Terraform apply

### Security Considerations
- ✅ Least privilege: Only allows sending from verified identities
- ✅ No wildcard permissions on SES resources
- ✅ Limited to specific domains and email addresses
- ✅ Both staging and production domains included

## Timeline

1. **30 Nov 2025 14:02** - IAM error discovered in production
2. **30 Nov 2025 14:30** - Terraform fix committed (`3d8879b`)
3. **Pending** - Terraform apply to common infrastructure

## Post-Deployment Verification

After applying, verify:

1. ✅ Contact form works (send test message)
2. ✅ Email delivered to `trigpointing@teasel.org`
3. ✅ CloudWatch logs show "contact_email_sent" event
4. ✅ No IAM errors in logs
5. ✅ Both staging and production work

## Related Documentation

- Full fix documentation: `docs/FIX_CONTACT_EMAIL_ISSUE.md`
- Contact endpoint: `api/api/v1/endpoints/admin.py`
- Email service: `api/services/email_service.py`
- ECS IAM policy: `terraform/common/ecs.tf`

## Support

If you encounter issues:
1. Check CloudWatch logs for error details
2. Verify SES identities are verified: `aws ses list-identities --region eu-west-1`
3. Check IAM policy is attached: `aws iam get-role-policy --role-name trigpointing-ecs-task-role --policy-name trigpointing-ecs-task-policy`
