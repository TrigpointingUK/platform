gs# Database Cleanup Summary - Audit Tables and GC Columns

**Date**: 2025-11-30  
**Migration ID**: 726a21695c73

## Overview

Successfully removed legacy database elements that are no longer used in the modern Auth0-based system:
- `audit` table (1 row)
- `audit_simple` table (0 rows)  
- All `gc_*` columns from the `user` table (Geocaching.com integration)

## Changes Made

### 1. Database Migration (Alembic)

**File**: `alembic/versions/726a21695c73_remove_audit_tables_and_gc_columns.py`

Created migration that:
- Drops the `audit` and `audit_simple` tables
- Removes 7 columns from the `user` table:
  - `gc_licence_ind`, `gc_licence_timestamp`
  - `gc_auth_ind`, `gc_auth_challenge`, `gc_auth_timestamp`
  - `gc_premium_ind`, `gc_premium_timestamp`

Includes complete downgrade function for rollback safety.

### 2. Code Changes

**api/crud/user.py**
- Removed `has_gc_auth()` function
- Removed `has_gc_premium()` function

**api/crud/trig.py**
- Updated comments: "admin audit trail" → "admin tracking fields"
- Clarified that these refer to trig table's admin_* columns, not the audit table

**api/api/v1/endpoints/admin.py**
- Updated comments similarly to clarify admin tracking vs audit table

### 3. Documentation Updates

**docs/database/schema_documentation.md**
- Removed audit table section
- Removed audit_simple table section
- Removed gc_* columns from user table definition
- Removed gc_* fields from all user sample data entries
- Updated table count from 38 to 36 tables

**docs/database/schema_complete.json**
- Removed all gc_* field definitions (70 occurrences)
- Automated removal using Python script

**docs/database/schema_complete.yaml**
- Removed all gc_* field definitions (82 occurrences)
- Automated removal using Python script

**api/migrations/ALEMBIC_GUIDE.md**
- Added migration entry to history section

## Testing

✅ All tests pass (398/398)
✅ No linter errors
✅ Migration file properly formatted

## Next Steps

To apply this migration:

### Staging
```bash
# Option 1: Via SSH tunnel
make postgres-tunnel-staging-ssm-start
export SECRET_JSON=$(aws --region eu-west-1 secretsmanager get-secret-value \
  --secret-id fastapi-staging-postgres-credentials \
  --query SecretString --output text)
export DB_HOST=localhost DB_PORT=5433
export DB_USER=$(echo "$SECRET_JSON" | jq -r '.username')
export DB_PASSWORD=$(echo "$SECRET_JSON" | jq -r '.password')
export DB_NAME=$(echo "$SECRET_JSON" | jq -r '.dbname')
source venv/bin/activate
alembic upgrade head

# Option 2: On bastion
ssh bastion.trigpointing.uk
cd ~/platform
git pull origin develop
source venv/bin/activate
alembic upgrade head
```

### Production
```bash
ssh bastion.trigpointing.uk
cd ~/platform-production
git pull origin main
source venv/bin/activate
alembic upgrade head
```

## Rollback Plan

If issues occur:
```bash
alembic downgrade -1
```

Note: Rollback will recreate table structure but NOT restore the 1 row of data from the audit table.

## Reusable Template

For future database cleanups, use this checklist:

1. **Search for references:**
   - Grep for table/column names in Python code
   - Check models, schemas, CRUD, API endpoints, tests
   - Search documentation files

2. **Create Alembic migration:**
   - `make migration-create MSG="remove [description]"`
   - Include upgrade() and downgrade() functions

3. **Update code:**
   - Remove model definitions
   - Remove CRUD functions
   - Remove utility functions
   - Update tests

4. **Update documentation:**
   - schema_documentation.md
   - schema_complete.json/yaml
   - ALEMBIC_GUIDE.md

5. **Test and deploy:**
   - Run `make ci` locally
   - Apply to staging
   - Verify functionality
   - Apply to production

## Notes

- The admin tracking fields (admin_user_id, admin_timestamp, admin_ip_addr) on the `trig` table are UNAFFECTED by this change
- The removed features were legacy Geocaching.com integration that predates the Auth0 migration
- No functional impact on current system
