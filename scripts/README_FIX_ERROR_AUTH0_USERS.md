# Fix ERROR- Prefixed Auth0 Users

## Overview

This script fixes users in the production MySQL database who have `auth0_user_id` values like `ERROR-12345678`. These error markers were created during legacy migration when Auth0 user creation failed.

## What It Does

For each user with an ERROR- prefixed `auth0_user_id`:

1. **Check for duplicates**: Query the database to see if another user exists with the same email and a valid Auth0 ID (prefix `auth0|`)
2. **If duplicate found**:
   - Mark the ERROR- user as `DUPLICATE-{valid_user_id}-{random_8_digits}` where `valid_user_id` is the ID of the user with the working Auth0 account
   - Do NOT touch Auth0 (the other user already has a valid Auth0 account)
   - Skip to next user
3. **If no duplicate found**, proceed with normal fix:
   - Search Auth0 for an existing user with the matching email address
   - Delete the incorrect Auth0 user if found
   - Create a new Auth0 user with proper configuration including:
     - `manual_migration.trigger = "admin"` flag to suppress Post-Registration Action
     - Proper `app_metadata` with database user ID linkage
     - Random password (user will need to reset)
   - Update the database with the new Auth0 user ID

## Prerequisites

### Required Environment Variables

```bash
# Auth0 Configuration (always required)
export AUTH0_TENANT_DOMAIN="trigpointing.eu.auth0.com"
export AUTH0_M2M_CLIENT_ID="your_m2m_client_id"
export AUTH0_M2M_CLIENT_SECRET="your_m2m_client_secret"
export AUTH0_CONNECTION="tuk-users"  # or your connection name

# Database Configuration (Option 1: Manual)
export DB_HOST="your-rds-endpoint"
export DB_PORT="3306"
export DB_USER="fastapi_production"
export DB_PASSWORD="your_password"
export DB_NAME="tuk_production"

# AWS Configuration (Option 2: For --fetch-from-secrets)
export AWS_DEFAULT_REGION="eu-west-2"
```

### Required Python Packages

Install dependencies:

```bash
pip install pymysql sqlalchemy boto3
```

Or use the migration requirements:

```bash
pip install -r requirements-migration.txt
```

## Usage

### Dry Run (Recommended First)

Test the script without making any changes:

```bash
python scripts/fix_error_auth0_users.py --dry-run --limit 5
```

### Process Single User

Process just one user to verify everything works:

```bash
python scripts/fix_error_auth0_users.py --limit 1
```

### Process Multiple Users

Process a batch of users:

```bash
python scripts/fix_error_auth0_users.py --limit 10
```

### Process All Users

Process all users with ERROR- prefixed auth0_user_id:

```bash
python scripts/fix_error_auth0_users.py --limit 999999
```

### Using AWS Secrets Manager

Fetch database credentials from AWS Secrets Manager:

```bash
python scripts/fix_error_auth0_users.py --fetch-from-secrets --limit 10
```

### Staging Environment

To run against staging:

```bash
python scripts/fix_error_auth0_users.py --environment staging --limit 5
```

## Command-Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--limit` | 1 | Number of users to process |
| `--dry-run` | false | Preview changes without making them |
| `--environment` | production | Target environment (production/staging) |
| `--fetch-from-secrets` | false | Fetch DB credentials from AWS Secrets Manager |
| `--region` | eu-west-2 | AWS region for Secrets Manager |

## Output

The script provides detailed output for each user:

### Example 1: Duplicate User Found

```
Processing user 12345: johndoe (john@example.com)
  Current auth0_user_id: ERROR-98765432
  🔍 Checking for duplicate user with email: john@example.com
    ⚠️  Found duplicate user: 54321 (johndoe_old)
    Valid Auth0 ID: auth0|abc123xyz
    → This user (ID 12345) is a duplicate and should be marked
    📝 Marking as duplicate: DUPLICATE-54321-87654321
    ✓ Marked as duplicate successfully
  🔗 Duplicate: User 12345 (john@example.com) -> DUPLICATE-54321-87654321
```

Note: The marker `DUPLICATE-54321-87654321` contains the ID of the **valid user** (54321), making it easy to trace which account is the correct one.

### Example 2: Invalid Email Address

```
Processing user 541: charlie d (none)
  Current auth0_user_id: ERROR-96808230
  ⚠️  Invalid or missing email address: none
    📝 Setting auth0_user_id to NULL...
    ✓ Set auth0_user_id to NULL
  ⊘ Skipped: User 541 (charlie d) - Invalid email - set to NULL
```

Note: Users with invalid emails like "none", "null", "n/a", or malformed addresses have their `auth0_user_id` set to NULL and require manual intervention.

### Example 3: Normal Fix (No Duplicate)

```
Processing user 67890: janedoe (jane@example.com)
  Current auth0_user_id: ERROR-11223344
  🔍 Checking for duplicate user with email: jane@example.com
    No duplicate user found - proceeding with normal fix
  🔍 Searching Auth0 for user with email: jane@example.com
    Found existing Auth0 user: auth0|old123
    🗑️  Deleting existing Auth0 user: auth0|old123
    ✓ Deleted Auth0 user
    ⏱️  Waiting 3 seconds for Auth0 deletion to propagate...
    🔨 Creating new Auth0 user...
    ✓ Created Auth0 user: auth0|new789
    New auth0_user_id: auth0|new789
    💾 Updating database...
  ✓ Success: User 67890 (jane@example.com) -> auth0|new789
```

**Note**: The 3-second delay after deletion is necessary to avoid Auth0's internal caching causing race conditions. Auth0's deletion takes a moment to propagate across their systems.

### Summary Report

At the end, you'll see a summary:

```
================================================================================
MIGRATION SUMMARY
================================================================================
Total users processed: 10
Successful: 7
  - Fixed with new Auth0 users: 6
  - Marked as duplicates: 1
Failed: 1
Skipped: 2

ERRORS:
  - User 12346 (bob@example.com): Failed to create new Auth0 user
================================================================================
```

**Note**: Skipped users include those with invalid/missing email addresses (set to NULL) and other issues.

## Safety Features

1. **Confirmation prompt**: Before making changes, you must confirm with "yes"
2. **Per-user commits**: Database updates are committed after each successful migration
3. **Error handling**: Individual failures don't stop the entire batch
4. **Detailed logging**: Every step is logged for audit purposes
5. **Dry-run mode**: Test without making changes

## Troubleshooting

### Error: Missing Auth0 credentials

Ensure you've set:
- `AUTH0_TENANT_DOMAIN`
- `AUTH0_M2M_CLIENT_ID`
- `AUTH0_M2M_CLIENT_SECRET`
- `AUTH0_CONNECTION`

### Error: Cannot connect to database

If using manual credentials:
- Check `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME`
- Ensure you have network access (may need bastion/VPN)

If using `--fetch-from-secrets`:
- Check AWS credentials are configured
- Verify secret name exists: `fastapi-production-credentials`
- Check IAM permissions for Secrets Manager

### Auth0 API Rate Limits

The script processes users one at a time with appropriate API calls. If you hit rate limits:
- Reduce `--limit` to process fewer users at once
- Wait a few minutes between batches

### Race Condition: "User already exists" After Deletion

If you see an error like "Auth0 user already exists with email" immediately after successful deletion:
- This is an Auth0 internal caching/replication issue
- The script now includes a 3-second delay after deletion to prevent this
- If you still see this error, Auth0 may need more time (rare)
- The Auth0 logs will show successful deletion (status 204) but creation fails
- Simply re-run the script for that user after a minute

### User Has No Email

Users without email addresses are skipped with a message. These need manual intervention.

### Invalid Email Address

Users with invalid or malformed email addresses (like "none", "null", "n/a", or non-email format):
- Their `auth0_user_id` is set to `NULL` in the database
- They are counted as "skipped" in the summary
- These users need manual intervention to fix their email address
- Common invalid values detected: `none`, `null`, `n/a`, `na`, `-`, `unknown`
- Email format validation: Must match pattern `user@domain.tld`

### Duplicate Users

If a user with ERROR- prefix has the same email as another user with a valid `auth0|` ID:
- The ERROR- user is marked as `DUPLICATE-{valid_user_id}-{random}`
- The marker contains the **valid user's ID** (not the ERROR- user's ID)
- Example: User 8 (ERROR-) is duplicate of user 164 (valid) → marked as `DUPLICATE-164-12345678`
- No Auth0 operations are performed
- This is the correct behavior - it prevents overwriting a valid Auth0 account
- These duplicate users may need manual cleanup or merging later

## Manual Migration Flag

The script uses `Auth0Service.create_user_for_admin_migration()` which sets:

```json
{
  "app_metadata": {
    "manual_migration": {
      "trigger": "admin",
      "timestamp": "2024-01-15T10:30:00Z"
    },
    "database_user_id": 12345,
    "original_username": "johndoe",
    "legacy_sync": "2024-01-15T10:30:00Z"
  }
}
```

This suppresses the Post-Registration Action (see `terraform/modules/auth0/actions/post-user-registration.js.tpl` lines 32-36) which would otherwise try to create a duplicate database user.

## Next Steps After Running

1. **Verify**: Check a few users in Auth0 dashboard to confirm proper creation
2. **Test login**: Have a test user try logging in
3. **Monitor**: Watch for any Auth0 webhook errors
4. **Password resets**: Affected users will need to use "Forgot Password" to set their passwords

## Files

- Script: `scripts/fix_error_auth0_users.py`
- Auth0 Service: `api/services/auth0_service.py`
- Database CRUD: `api/crud/user.py`
- Action Template: `terraform/modules/auth0/actions/post-user-registration.js.tpl`

