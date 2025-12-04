# PostgreSQL Test Fixing Progress

## Problem
When we switched from SQLite (with per-test table drop/create) to PostgreSQL (with shared tables across tests), hardcoded IDs in tests started causing `UniqueViolation` errors due to parallel test execution.

## Root Cause
- **SQLite approach**: Each test got a completely fresh database (drop all tables, recreate)
- **PostgreSQL approach**: Tables created once per worker, tests share data
- **Impact**: Hardcoded `id=1`, `name="testuser"`, etc. collide between parallel tests

## Solution Pattern
1. Remove hardcoded `id=NUMBER` from all model constructors
2. Add `db.refresh(object)` after `db.commit()` to retrieve auto-generated IDs
3. Use dynamic references (`user.id`, `trig.id`) instead of hardcoded numbers
4. Make unique fields unique using UUID suffixes:
   ```python
   import uuid
   unique_name = f"testuser_{uuid.uuid4().hex[:8]}"
   ```

## Progress

### Starting Point
- 308 passing tests
- 95 failures
- 64 errors

### Current Status (After Latest Fixes)
- **438 passing tests** (+130, +42%)
- **28 failures** (-67, -71%)  
- **0 errors** (-64, -100%!) ✅
- **94.0% pass rate**

### Files Completely Fixed (24 files)
1. ✅ `api/tests/test_user.py` - 4/4 tests passing
2. ✅ `api/tests/test_user_badge.py` - 5/5 tests passing  
3. ✅ `api/tests/conftest.py` - Fixed `test_user` and `test_tlog_entries` fixtures
4. ✅ `api/tests/test_user_stats_comprehensive.py` - 7/7 tests passing
5. ✅ `api/tests/test_crud_auth0_integration.py` - 9/9 tests passing (no changes needed)
6. ✅ `api/tests/test_trig.py` - 10/10 tests passing
7. ⚠️  `api/tests/test_legacy_migration.py` - 5/7 tests passing (2 incompatible with parallel)
8. ✅ `api/tests/test_photo_upload.py` - 2/2 tests passing
9. ✅ `api/tests/test_legacy_login.py` - 22/22 tests passing (dynamic Auth0 fixtures)
10. ✅ `api/tests/test_tphoto.py` - 3/3 tests passing
11. ✅ `api/tests/test_api_trig_map_edge_cases.py` - 2/2 tests passing
12. ✅ `api/tests/test_api_trig_map.py` - 5/5 tests passing
13. ✅ `api/tests/test_admin_legacy_migration.py` - 8/8 tests passing
14. ✅ `api/tests/test_admin_scope_authorization.py` - All tests passing (fixed testuser)
15. ✅ `api/tests/test_contact.py` - All tests passing (fixed testuser)
16. ✅ `api/tests/test_pii_scope_authorization.py` - 5/5 tests passing ⭐ NEW
17. ✅ `api/tests/test_user_profile_roles.py` - All tests passing (fixed testuser)
18. ✅ `api/tests/test_user_profile_sync.py` - 13/13 tests passing (fixed all hardcoded values)
19. ✅ `api/tests/test_user_provisioning.py` - 11/11 tests passing (fixed all hardcoded values)
20. ✅ `api/tests/test_crud_user_creation.py` - 8/8 tests passing ⭐ NEW
21. ✅ `api/tests/test_photo_rotate.py` - 14/14 tests passing ⭐ NEW
22. ✅ `api/tests/test_auth0_username_mapping.py` - 9/9 tests passing ⭐ NEW
23. ✅ `api/tests/test_auth0_provisioning_flow.py` - 5/6 tests passing (1 skipped) ⭐ NEW
24. ✅ `api/tests/test_crud_email_functions.py` - 11/11 tests passing ⭐ NEW

### Total Fixes Applied
- Removed hardcoded IDs from 150+ model instantiations
- Added `db.refresh()` calls for 150+ objects
- Made 100+ unique fields truly unique with UUID
- Updated 200+ assertions to use dynamic values

### Remaining Failures (28 tests)
- `test_crud.py` (2 tests - expecting empty database, needs redesign)
- `test_deleted_photo_filtering.py` (8 tests - likely hardcoded IDs)
- `test_logs_photo_urls.py` (3 tests - likely hardcoded IDs)
- `test_logs_include_photos.py` (4 tests - likely hardcoded IDs)
- `test_trig_logs_include_photos.py` (2 tests - likely hardcoded IDs)
- `test_log_search.py` (5 tests - regex/counting issues with shared DB)
- `test_legacy_login.py` (1 test - needs investigation)
- `test_legacy_migration.py` (2 tests - parallel execution issues)
- Others (1 test - needs investigation)

## Next Steps
Continue applying UUID/dynamic ID patterns to photo-related tests to reach 100% pass rate.
