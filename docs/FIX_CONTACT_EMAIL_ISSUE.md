# Contact Form Email Failure - Root Cause Analysis and Fix

**Date**: 30 November 2025  
**Status**: Fixed  
**Issue**: Contact form API returning "Failed to send email. Please try again later."

## Problem Summary

The contact form endpoint (`POST /v1/admin/contact`) was failing to send emails, returning a 500 error with the message:
```json
{"detail":"Failed to send email. Please try again later."}
```

## Root Cause

The contact form was configured to send emails to `contact@teasel.org`, but this email address was **not verified** in AWS SES.

### AWS SES Verification Requirements

AWS SES requires email addresses to be verified before they can:
- Send emails (FROM address)
- Receive emails sent via SES (TO address)

While accounts can move to "production mode" to remove the requirement for recipient verification, this project keeps sender and recipient verification for security.

### Verified Identities in SES (eu-west-1)

Before the fix:
- ✅ `trigpointing@teasel.org` - **Verified**
- ✅ `ian@teasel.org` - **Verified**
- ✅ `admin@trigpointing.uk` - **Verified**
- ✅ `trigpointing.uk` (domain) - **Verified**
- ✅ `trigpointing.me` (domain) - **Verified**
- ❌ `contact@teasel.org` - **NOT Verified**

### Investigation Commands

```bash
# List all verified identities
aws ses list-identities --region eu-west-1

# Check specific email verification status
aws ses get-identity-verification-attributes \
  --identities contact@teasel.org trigpointing@teasel.org \
  --region eu-west-1
```

Results showed `contact@teasel.org` had no verification status, while `trigpointing@teasel.org` was successfully verified.

## Solution

Changed the recipient email address in the contact form endpoint from `contact@teasel.org` to `trigpointing@teasel.org`.

### Files Modified

1. **`api/api/v1/endpoints/admin.py`** (line 292)
   - Changed `to_email="contact@teasel.org"` → `to_email="trigpointing@teasel.org"`

2. **`api/tests/test_contact.py`** (line 59)
   - Updated test assertion to expect `trigpointing@teasel.org`

### Code Changes

```python
# Before (admin.py line 290-300)
success = email_service.send_contact_email(
    to_email="contact@teasel.org",  # ❌ Not verified
    reply_to=contact_request.email,
    ...
)

# After
success = email_service.send_contact_email(
    to_email="trigpointing@teasel.org",  # ✅ Verified
    reply_to=contact_request.email,
    ...
)
```

## Testing

All tests passed after the fix:
```bash
# Run contact form tests
pytest api/tests/test_contact.py -v
# Result: 6 passed (authenticated tests require test DB)

# Run full CI suite
make ci
# Result: All checks passed ✅
```

## Alternative Solutions Considered

### Option 1: Verify contact@teasel.org in SES (Not chosen)
This would require:
1. Adding `contact@teasel.org` to Terraform SES configuration
2. Verifying the email address through AWS SES verification email
3. Updating DNS records if needed

**Why not chosen**: `trigpointing@teasel.org` is already verified and serves the same purpose.

### Option 2: Use a verified domain (Not needed)
While `teasel.org` isn't a verified domain in SES, `trigpointing@teasel.org` is individually verified, which is sufficient.

## Email Flow

### Contact Form Submission
```
User submits contact form
    ↓
POST /v1/admin/contact
    ↓
email_service.send_contact_email()
    ↓
AWS SES (eu-west-1)
    ↓
FROM: contact@trigpointing.uk (verified domain)
TO: trigpointing@teasel.org (verified email)
REPLY-TO: [user's email from form]
    ↓
Delivered to trigpointing@teasel.org
```

### Key Points
- **FROM address**: `contact@trigpointing.uk` (configured in `email_service.py`, verified via domain)
- **TO address**: `trigpointing@teasel.org` (now verified)
- **REPLY-TO**: User's email from the form (allows easy response)

## Deployment

This fix can be deployed directly to both staging and production:
- No infrastructure changes required
- No environment variable changes required
- No database migrations required
- Code change only

## Related Files

- Contact endpoint: `api/api/v1/endpoints/admin.py`
- Email service: `api/services/email_service.py`
- Contact tests: `api/tests/test_contact.py`
- Contact schema: `api/schemas/contact.py`
- SES Terraform: `terraform/common/ses.tf`

## Monitoring

To monitor contact form emails going forward:

```bash
# Check email service logs
# Look for events: contact_email_sent, contact_email_failed, contact_email_error

# Verify SES sending statistics
aws ses get-send-statistics --region eu-west-1

# Check SES account sending status
aws ses get-account-sending-enabled --region eu-west-1
```

## Prevention

To prevent similar issues in the future:
1. When adding new email endpoints, verify the recipient address is in SES
2. Consider adding SES email identity checks to CI/CD pipeline
3. Document all verified SES identities in `terraform/common/ses.tf`

## References

- AWS SES Documentation: https://docs.aws.amazon.com/ses/
- SES Email Verification: https://docs.aws.amazon.com/ses/latest/dg/verify-email-addresses.html
- Project SES Configuration: `terraform/common/ses.tf`
