# Email Merge API - User Migration Guide

## Overview

This API provides administrative tools to identify and merge users with duplicate email addresses, preparing the database for a unique constraint on `user.email` to support Auth0 email-based authentication.

## Prerequisites

- Admin access with `api:admin` scope
- Auth0 authentication token
- Database backup (recommended before bulk operations)

## Endpoints

### 1. Analyse Duplicate Emails

**GET** `/v1/legacy/email-duplicates`

Identifies all email addresses with multiple user accounts and provides detailed activity analysis.

#### Parameters

| Parameter | Type   | Required | Default | Description                           |
|-----------|--------|----------|---------|---------------------------------------|
| `email`   | string | No       | -       | Filter for specific email address     |

#### Response

```json
{
  "total_duplicate_emails": 2,
  "duplicates": [
    {
      "email": "user@example.com",
      "user_count": 2,
      "users": [
        {
          "user_id": 123,
          "username": "user1",
          "email": "user@example.com",
          "last_activity": "2024-10-15T14:30:00Z",
          "activity_counts": {
            "logs": 45,
            "photos": 12,
            "photo_votes": 8,
            "queries": 23,
            "quiz_scores": 3
          }
        },
        {
          "user_id": 456,
          "username": "user2",
          "email": "user@example.com",
          "last_activity": "2022-03-20T09:15:00Z",
          "activity_counts": {
            "logs": 2,
            "photos": 0,
            "photo_votes": 0,
            "queries": 5,
            "quiz_scores": 0
          }
        }
      ]
    }
  ]
}
```

#### Example Usage

```bash
# Get all duplicate emails
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/v1/legacy/email-duplicates

# Get specific email
curl -H "Authorization: Bearer $TOKEN" \
  "https://api.example.com/v1/legacy/email-duplicates?email=user@example.com"
```

### 2. Merge Users

**POST** `/v1/legacy/merge_users`

Merges secondary users into the primary user (most recent activity). By default runs in dry-run mode.

#### Request Body

```json
{
  "email": "user@example.com",
  "activity_threshold_days": 180,
  "dry_run": true
}
```

| Field                      | Type    | Required | Default | Description                                  |
|----------------------------|---------|----------|---------|----------------------------------------------|
| `email`                    | string  | Yes      | -       | Email address to merge users for             |
| `activity_threshold_days`  | integer | No       | 180     | Days threshold for conflict detection (1-3650)|
| `dry_run`                  | boolean | No       | true    | Preview only, no actual changes              |

#### Success Response (Dry Run)

```json
{
  "dry_run": true,
  "email": "user@example.com",
  "primary_user_id": 123,
  "primary_username": "user1",
  "users_to_merge": [456],
  "usernames_to_merge": ["user2"],
  "estimated_records": {
    "tlog": 2,
    "tphoto": 0,
    "tphotovote": 0,
    "tquery": 5,
    "tquizscores": 0
  },
  "profile_updates": {
    "firstname": "John",
    "surname": "Doe",
    "homepage": "http://example.com",
    "about": "Bio text"
  }
}
```

#### Success Response (Executed)

```json
{
  "success": true,
  "email": "user@example.com",
  "primary_user_id": 123,
  "primary_username": "user1",
  "merged_user_ids": [456],
  "merged_usernames": ["user2"],
  "updated_records": {
    "tlog": 2,
    "tphoto": 0,
    "tphotovote": 0,
    "tquery": 5,
    "tquizscores": 0
  },
  "profile_updated": true
}
```

#### Conflict Response (409)

When users have activity within the threshold:

```json
{
  "detail": {
    "error": "merge_conflict",
    "message": "Cannot merge: 1 user(s) have activity within 180 days of primary user",
    "email": "user@example.com",
    "primary_user": {
      "user_id": 123,
      "username": "user1",
      "last_activity": "2024-10-15T14:30:00Z",
      "days_since_primary": null
    },
    "conflicting_users": [
      {
        "user_id": 456,
        "username": "user2",
        "last_activity": "2024-09-01T10:20:00Z",
        "days_since_primary": 44.0
      }
    ],
    "threshold_days": 180
  }
}
```

#### Example Usage

```bash
# Dry run (preview)
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","dry_run":true}' \
  https://api.example.com/v1/legacy/merge_users

# Execute merge
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","dry_run":false}' \
  https://api.example.com/v1/legacy/merge_users

# Custom threshold (30 days)
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","activity_threshold_days":30,"dry_run":true}' \
  https://api.example.com/v1/legacy/merge_users
```

## Merge Process

### How Primary User is Selected

The user with the **most recent activity** becomes the primary user:
1. Check last activity across all tables: tlog, tphoto, tphotovote, tquery, tquizscores
2. User with most recent timestamp is selected
3. If no activity, use account creation date

### What Gets Merged

1. **Activity Records** - All records reassigned to primary user:
   - `tlog` entries
   - `tphotovote` entries
   - `tquery` entries
   - `tquizscores` entries
   - `tphoto` entries (via tlog relationship)

2. **Profile Data** - Best values selected:
   - `firstname` - most recent non-empty value
   - `surname` - most recent non-empty value
   - `homepage` - most recent non-empty value
   - `about` - most recent non-empty value

3. **User Deletion** - Secondary users are hard deleted

### Conflict Detection

Merges are blocked when multiple users have been active within the threshold period. This prevents accidentally merging accounts that may be legitimately separate users.

**Default threshold**: 180 days (6 months)

**Example conflict scenario:**
- User A: last activity 10 days ago
- User B: last activity 50 days ago
- Result: Blocked (50 days < 180 days threshold)

**Non-conflict scenario:**
- User A: last activity 10 days ago
- User B: last activity 200 days ago
- Result: Merge allowed (200 days > 180 days threshold)

## Workflow Recommendations

### Step 1: Analyse the Situation

```bash
# Get all duplicates
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/v1/legacy/email-duplicates > duplicates.json
```

Review the output to understand:
- How many duplicate emails exist
- Activity patterns for each user
- Which merges will be straightforward vs. conflicted

### Step 2: Handle Simple Cases

For users with clear activity separation (>6 months):

```bash
# Preview merge
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","dry_run":true}' \
  https://api.example.com/v1/legacy/merge_users

# If preview looks good, execute
curl -X POST -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","dry_run":false}' \
  https://api.example.com/v1/legacy/merge_users
```

### Step 3: Handle Conflicts

For conflicts, you have several options:

1. **Adjust threshold** - Try shorter period if activity patterns warrant:
   ```bash
   curl -X POST -H "Authorization: Bearer $TOKEN" \
     -H "Content-Type: application/json" \
     -d '{"email":"user@example.com","activity_threshold_days":30,"dry_run":true}' \
     https://api.example.com/v1/legacy/merge_users
   ```

2. **Manual intervention** - Contact user to determine which account to keep

3. **Wait** - If one account is becoming inactive, wait until it exceeds threshold

### Step 4: Bulk Processing

For processing many duplicates, create a script:

```bash
#!/bin/bash

# Get list of duplicate emails
curl -H "Authorization: Bearer $TOKEN" \
  https://api.example.com/v1/legacy/email-duplicates | \
  jq -r '.duplicates[].email' > emails.txt

# Process each email
while read email; do
  echo "Processing: $email"
  
  # Try merge in dry-run mode
  response=$(curl -s -X POST \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d "{\"email\":\"$email\",\"dry_run\":true}" \
    https://api.example.com/v1/legacy/merge_users)
  
  # Check if successful (no conflicts)
  if echo "$response" | jq -e '.dry_run == true' > /dev/null; then
    echo "  ✓ Can merge (no conflicts)"
    
    # Execute merge
    curl -s -X POST \
      -H "Authorization: Bearer $TOKEN" \
      -H "Content-Type: application/json" \
      -d "{\"email\":\"$email\",\"dry_run\":false}" \
      https://api.example.com/v1/legacy/merge_users | jq .
      
    echo "  ✓ Merged successfully"
  else
    echo "  ✗ Conflict detected, skipping"
    echo "$response" | jq '.detail'
  fi
  
  sleep 1
done < emails.txt
```

## Safety Features

1. **Dry Run Default**: Always previews changes unless explicitly disabled
2. **Transaction-based**: All changes are atomic with automatic rollback on error
3. **Admin-only**: Requires `api:admin` scope
4. **Conflict Detection**: Prevents merging accounts with overlapping activity
5. **Comprehensive Logging**: All operations logged for audit trail

## Troubleshooting

### "No users found with email"

**Cause**: Email doesn't exist in database or has no users

**Solution**: Verify email spelling, check if users actually exist

### "Only one user found"

**Cause**: Email is not duplicated

**Solution**: No action needed, email is already unique

### "Cannot merge: conflict detected"

**Cause**: Multiple users have recent activity

**Solutions**:
1. Review activity patterns - may be legitimate separate accounts
2. Adjust `activity_threshold_days` if appropriate
3. Contact users to determine correct account
4. Wait until one account becomes inactive

### "Merge failed: [error]"

**Cause**: Database error or constraint violation

**Solutions**:
1. Check logs for detailed error
2. Verify database connectivity
3. Ensure transaction wasn't interrupted
4. Database automatically rolled back, safe to retry

## Database Backup

**IMPORTANT**: Before performing bulk merge operations:

```bash
# Backup user table
mysqldump -u user -p database_name user > user_backup.sql

# Backup activity tables
mysqldump -u user -p database_name \
  tlog tphoto tphotovote tquery tquizscores > activity_backup.sql
```

## Next Steps

After resolving all duplicate emails:

1. Add unique constraint to `user.email` column via database migration
2. Update Auth0 configuration to enforce email uniqueness
3. Monitor for any new duplicates via the analysis endpoint

## Support

For issues or questions:
- Check application logs for detailed error messages
- Review conflict details in 409 responses
- Contact development team with specific email addresses and error messages

