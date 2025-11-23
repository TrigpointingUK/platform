# PostgreSQL Migration: Nullable Fields Issue

## Problem
During the MySQL→PostgreSQL migration, the `create_postgres_schema.py` script made **all non-auto-increment columns nullable** to handle MySQL's lenient NULL handling. However, the SQLAlchemy models and Pydantic schemas still declare many fields as `nullable=False` and non-`Optional`, causing validation errors when the API encounters NULL values in the migrated data.

## Root Cause
MySQL allows NULL values in `NOT NULL` columns under certain conditions (e.g., `0000-00-00` dates, empty strings in strict mode). The migration script pragmatically made all columns nullable to ensure data could be imported without `NotNullViolation` errors.

## Fixes Applied
### 1. TLog Model & Schema ✅
- **Files**: `api/models/user.py`, `api/schemas/tlog.py`
- **Issue**: `/v1/logs` endpoint failing with validation errors for `date` and `comment` fields
- **Fix**: Made all TLog fields nullable in both model and schema
- **Status**: ✅ Fixed - endpoint now returns data successfully

### 2. User Model & Schema ✅
- **Files**: `api/models/user.py`, `api/schemas/user.py`
- **Issue**: `/v1/users` endpoint failing with validation errors for `firstname` and `surname` fields
- **Fix**: Made all User fields (except `id` and `name`) nullable in both model and schema
- **Status**: ✅ Fixed - endpoint now returns data successfully (including users with NULL surnames)

## Potential Issues in Other Models
The following models also have `nullable=False` declarations and may encounter similar issues:

### High Priority (User-Facing Endpoints)
- **User** (`api/models/user.py`): Core identity fields, timestamps
- **Trig** (`api/models/trig.py`): Identifiers, coordinates, location info
- **TPhoto** (`api/models/tphoto.py`): Photo metadata
- **TPhotoVote**, **TQuery**, **TQuizScores**: Less critical but may fail

### Lower Priority (Reference Data)
- **Status**, **Server**, **TrigStats**, **Location** models: Likely pre-populated with valid data

## Recommended Approach
1. **Monitor logs** for `ValidationError` exceptions mentioning specific fields
2. **Update models incrementally** as issues are discovered in production/staging
3. **Consider a bulk update** if issues become widespread:
   - Add a mixin or base class that makes fields nullable by default
   - Use reflection to compare SQLAlchemy models with actual PostgreSQL schema

## Long-term Solution
Once all legacy MySQL data is confirmed clean, consider:
1. Running a data quality audit on PostgreSQL
2. Adding NOT NULL constraints back for critical fields where appropriate
3. Backfilling NULL values with sensible defaults
4. Updating models to match the final schema
