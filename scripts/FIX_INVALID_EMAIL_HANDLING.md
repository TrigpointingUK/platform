# Fix: Invalid Email Addresses - Set auth0_user_id to NULL

## Problem

Some users in the database have invalid or malformed email addresses:
- "none"
- "null"  
- "n/a"
- Other non-email values

When the script tries to create Auth0 users for these, Auth0's API returns:
```
400 Bad Request: Payload validation error: 'Object didn't pass validation for format email: none'
```

## Solution

Added **email validation** before attempting Auth0 operations:

1. Check if email is valid before processing
2. If invalid, set `auth0_user_id` to `NULL` in database
3. Skip to next user (counted as "skipped")

## Email Validation

The script detects these as invalid:

### Invalid Literal Values
- `none`
- `null`
- `n/a`
- `na`
- `-`
- `unknown`
- Empty string

### Invalid Format
- Must match pattern: `user@domain.tld`
- Basic regex: `^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$`

## Example Output

```
Processing user 541: charlie d (none)
  Current auth0_user_id: ERROR-96808230
  ⚠️  Invalid or missing email address: none
    📝 Setting auth0_user_id to NULL...
    ✓ Set auth0_user_id to NULL
  ⊘ Skipped: User 541 (charlie d) - Invalid email - set to NULL
```

## Database Changes

For users with invalid emails:

**Before:**
```sql
id: 541
name: "charlie d"
email: "none"
auth0_user_id: "ERROR-96808230"
```

**After:**
```sql
id: 541
name: "charlie d"
email: "none"  -- unchanged
auth0_user_id: NULL  -- cleared
```

## Summary Report

Skipped users are counted separately:

```
Total users processed: 10
Successful: 7
  - Fixed with new Auth0 users: 6
  - Marked as duplicates: 1
Failed: 1
Skipped: 2  ← Includes invalid email users
```

## Manual Intervention Required

Users with `auth0_user_id = NULL` need:
1. Update their email address in the database to a valid email
2. Either:
   - Have them register normally with Auth0 (creates new account)
   - Run this script again to migrate them properly

## Code Changes

### New Functions

1. `is_valid_email(email: str) -> bool`
   - Validates email format
   - Checks against common invalid values
   - Returns True/False

2. `set_auth0_id_to_null(db: Session, user_id: int) -> bool`
   - Updates database to set `auth0_user_id = NULL`
   - Includes transaction commit
   - Returns success status

### Modified Logic

In `fix_user()`:
- Added email validation as first check
- If invalid, sets to NULL and skips
- Otherwise continues with normal flow

## Files Modified

1. ✅ `scripts/fix_error_auth0_users.py` - Added validation and NULL handling
2. ✅ `scripts/README_FIX_ERROR_AUTH0_USERS.md` - Documented invalid email handling

## Testing

✅ All tests passing
✅ No linter errors
✅ Email validation working correctly

---

**Date**: 2025-11-15
**Issue**: Invalid email addresses causing Auth0 API errors
**Solution**: Validate emails, set to NULL if invalid
**Status**: ✅ Fixed

