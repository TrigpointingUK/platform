# Database Cleanup Summary - Legacy Tables and User Columns (Batch 2)

**Date**: 2025-11-30  
**Migration ID**: 6b9cf6a8d304

## Overview

Successfully removed 6 additional legacy database tables and 3 user columns. This continues the database cleanup from migration bb808d64115f. The TQuizScores model and all related code in the user merge functionality were also removed.

## Changes Made

### 1. Database Migration (Alembic)

**File**: `alembic/versions/6b9cf6a8d304_remove_legacy_tables_and_user_columns_.py`

Created migration that:

#### Tables Removed (6 total)

| Table | Rows | Purpose | Reason for Removal |
|-------|------|---------|-------------------|
| `barrytools` | 76 | Legacy "Barry's Tools" feature | No code references |
| `coord2county` | 35,247 | Coordinate-to-county lookup | No code references |
| `trigdata` | 7,314 | Extended trigpoint data | No code references |
| `trigdatafields` | 32 | Field definitions for trigdata | No code references, meta-table |
| `tphotoclass` | 5,292 | Photo classification | No code references |
| `tquizscores` | 3,277 | Quiz scores feature | User confirmed OK to remove |

**Total data removed**: ~48,000 rows

#### User Columns Removed (3 total)

| Column | Type | Purpose | Reason for Removal |
|--------|------|---------|-------------------|
| `admin_ind` | CHAR(1) | Admin flag | Replaced by Auth0 roles/scopes |
| `disclaimer_ind` | CHAR(1) | Terms acceptance flag | No code references |
| `disclaimer_timestamp` | TIMESTAMP | Terms acceptance time | No code references |

**Note**: `email_ind` was kept - still in use for email notification preferences.

### 2. Code Changes - TQuizScores Removal

**api/models/user.py**
- Removed `TQuizScores` class definition (lines 138-150)

**api/models/__init__.py**
- Removed `TQuizScores` from imports
- Removed `TQuizScores` from `__all__` export list

**api/crud/user_merge.py**
- Removed `TQuizScores` import (line 13)
- Removed from `get_user_last_activity()` function - removed tquizscores timestamp check (lines 83-90)
- Removed from `get_user_activity_counts()` function - removed quiz_scores count (lines 130-133)
- Removed from `count_records_for_users()` function - removed tquizscores count (lines 287-290)
- Removed from `merge_users()` function - removed tquizscores update (lines 356-363)

**api/schemas/user_merge.py**
- Removed `tquizscores: int = 0` field from `RecordCounts` schema (line 92)

**api/api/v1/endpoints/legacy.py**
- Updated docstring to remove `tquizscores` from merge list (line 575)

### 3. Comment Cleanup

**api/crud/user.py**
- Updated `is_admin()` function docstring to clarify Auth0 scopes usage (removed inline comment)

**api/tests/test_auth0_username_mapping.py**
- Removed outdated comment about `auth0_username` field (line 286)

### 4. Documentation Updates

**docs/database/schema_documentation.md**
- Removed 6 table sections (barrytools, coord2county, trigdata, trigdatafields, tphotoclass, tquizscores)
- Removed 3 user column definitions (admin_ind, disclaimer_ind, disclaimer_timestamp)
- Updated table count from 27 to 21 (-6 tables)

**docs/database/schema_complete.json**
- Programmatically removed 6 table definitions
- Removed 3 user columns from user table definition and sample data

**docs/database/schema_complete.yaml**
- Programmatically removed 6 table definitions
- Removed 3 user columns from user table definition

**api/migrations/ALEMBIC_GUIDE.md**
- Added migration entry documenting this cleanup in the Migration History section

---

## Testing

All tests passing:
```
474 passed, 11 skipped, 548 warnings
```

No failures after removing TQuizScores model and code references.

---

## Deployment Order

1. ✅ **Code Changes**: Committed to develop branch
2. ⏳ **Staging Migration**: `make postgres-tunnel`, then `make migrate-staging`
3. ⏳ **Staging Verification**: Test application functionality
4. ⏳ **Production Migration**: `make postgres-tunnel`, then `make migrate-production`

---

## Rollback Plan

Migration includes complete `downgrade()` function that:
- Recreates all 6 tables with their structures
- Recreates all 3 user columns with appropriate defaults

**WARNING**: Downgrade recreates structures only, not data. The following data would be permanently lost:
- coord2county: 35,247 rows of coordinate mappings
- trigdata: 7,314 rows of extended trig data
- tphotoclass: 5,292 rows of photo classifications
- tquizscores: 3,277 rows of quiz scores
- barrytools: 76 rows of tool definitions
- trigdatafields: 32 rows of field definitions

---

## Impact Assessment

### No Functional Impact

These features were already not in use:
- ✅ No code references to dropped tables (except tquizscores which was removed from user merge)
- ✅ `admin_ind` column already disabled (using Auth0 instead)
- ✅ No API endpoints return the deleted user columns
- ✅ Modern system uses different mechanisms

### User Merge Functionality

**Before**: Tracked quiz scores during user merges  
**After**: Quiz scores no longer tracked (user confirmed acceptable)

The `RecordCounts` schema now only tracks:
- `tlog` - Trig logs
- `tphoto` - Photos
- `tphotovote` - Photo votes
- `tquery` - Saved queries

### Schema Simplification

**Before**: 27 tables, user table with 26 columns  
**After**: 21 tables (-22%), user table with 23 columns (-3 columns)

**Combined cleanup totals (both migrations)**:
- Tables: 38 → 21 (-17 tables, -45%)
- User columns: 55 → 23 (-32 columns, -58%)

### Benefits

1. **Reduced complexity** - Fewer legacy features to maintain
2. **Clearer codebase** - Removed unused models and CRUD operations
3. **Smaller backups** - 48k+ rows removed
4. **Simplified user merge** - No quiz score tracking
5. **Less confusion** - Admin functionality clearly Auth0-based

---

## Verification Checklist

- [x] Migration file created with upgrade and downgrade
- [x] TQuizScores model removed
- [x] TQuizScores removed from all imports
- [x] User merge code updated (4 locations)
- [x] RecordCounts schema updated
- [x] Endpoint docstring updated
- [x] Comment cleanup completed
- [x] Tests updated and passing (474 passed)
- [x] Documentation updated (markdown, JSON, YAML)
- [x] ALEMBIC_GUIDE.md updated with migration entry
- [x] Committed to develop branch

---

## Related Cleanups

This is the second database cleanup:

1. **First cleanup** (bb808d64115f) - [DATABASE_CLEANUP_LEGACY_TABLES_COLUMNS.md](DATABASE_CLEANUP_LEGACY_TABLES_COLUMNS.md)
   - Removed 11 tables (audit, gc_columns, sms, etc.)
   - Removed 25 user columns
   
2. **This cleanup** (6b9cf6a8d304) - DATABASE_CLEANUP_BATCH2.md
   - Removed 6 tables (barrytools, tquizscores, coord2county, etc.)
   - Removed 3 user columns

**Combined**: Removed 17 tables and 28 user columns from the legacy database.

---

## Notes

- coord2county table had 35k+ rows but zero code references - coordinate lookup likely superseded
- trigdata/trigdatafields stored extended trigpoint metadata never exposed via API
- tphotoclass stored photo classifications but no classification feature exists
- barrytools was a legacy toolbox feature no longer in use
- User merge functionality simplified - quiz scores no longer tracked (user confirmed acceptable)
- Email notification preference (`email_ind`) preserved as requested
