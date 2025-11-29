# Remaining Test Failures Analysis

## Overview
**69 failing tests** across 13 test files, categorized into 4 main issues.

---

## Issue #1: Hardcoded Usernames (Most Common - ~20 tests)

### Affected Files:
1. **`test_crud_user_creation.py`** (8 tests) - All failing with `ValueError: Username 'X' already exists`
2. **`test_auth0_username_mapping.py`** (7 tests) - Hardcoded usernames
3. **`test_crud_email_functions.py`** (7 tests) - Hardcoded emails/usernames
4. **`test_auth0_provisioning_flow.py`** (4 tests) - Hardcoded usernames

### Root Cause:
Tests use hardcoded usernames like:
- `testuser`, `randomtest`, `emptyname`, `duplicateuser`
- `user1`, `user2`, `defaultuser`, `retrieveuser`

### Solution:
Apply the same UUID suffix pattern we've been using:
```python
import uuid
unique_name = f"testuser_{uuid.uuid4().hex[:8]}"
```

### Estimated Effort: 
**Medium** - 4 files, ~20-30 hardcoded values to fix. Similar to what we just did.

---

## Issue #2: Hardcoded IDs in Photo/TLog Tests (~15 tests)

### Affected Files:
1. **`test_photo_rotate.py`** (13 tests) - All failing with duplicate key on `tlog_pkey` or `user_pkey`
2. **`test_deleted_photo_filtering.py`** (8 tests) - Likely same issue
3. **`test_logs_photo_urls.py`** (3 tests) - Likely same issue

### Root Cause:
Tests have hardcoded IDs like `id=3001` for TLog, causing `UniqueViolation`:
```python
E   psycopg2.errors.UniqueViolation: duplicate key value violates unique constraint "tlog_pkey"
E   DETAIL:  Key (id)=(3001) already exists.
```

### Solution:
Remove hardcoded `id` parameters, use `db.refresh()` to get auto-generated IDs:
```python
# Before:
tlog = TLog(id=3001, trig_id=1, user_id=user.id, ...)

# After:
tlog = TLog(trig_id=1, user_id=user.id, ...)
db.add(tlog)
db.commit()
db.refresh(tlog)  # Now tlog.id is auto-generated
```

### Estimated Effort:
**Medium** - 3 files, need to review each fixture and remove hardcoded IDs. Similar work to what we've done before.

---

## Issue #3: Tests Expecting Empty Database (3 tests)

### Affected Files:
1. **`test_crud.py`** 
   - `test_get_trig_count_empty_table` - expects 0, gets 959
   - `test_get_trig_count_with_data` - expects 3, gets 912

### Root Cause:
These tests assume they're running against an empty database, but in PostgreSQL with parallel execution, the test database is **shared** and contains data from migrations/other tests.

### Solution Options:
1. **Filter by test-specific data**: Add unique identifiers to test data and query only that data
2. **Use relative assertions**: Change `assert count == 0` to `assert count >= 0` (less ideal)
3. **Count only test data**: Create test data with unique markers and count only those

### Example Fix:
```python
def test_get_trig_count_with_data(db: Session):
    # Create test-specific trigs with unique waypoint prefix
    import uuid
    test_prefix = f"TEST_{uuid.uuid4().hex[:6]}"
    
    # Create 3 test trigs
    for i in range(3):
        trig = Trig(waypoint=f"{test_prefix}_{i}", ...)
        db.add(trig)
    db.commit()
    
    # Count only our test trigs
    count = db.query(Trig).filter(Trig.waypoint.like(f"{test_prefix}%")).count()
    assert count == 3  # Now accurate
```

### Estimated Effort:
**Low** - Only 2-3 tests, but requires thoughtful approach to querying.

---

## Issue #4: Log Search Regex Tests (4 tests)

### Affected Files:
1. **`test_log_search.py`**
   - `test_search_logs_by_text` - expects 2, gets 48
   - `test_count_logs_by_text` - expects 2, gets 48
   - `test_search_logs_by_regex` - SQLAlchemy error
   - `test_count_logs_by_regex` - SQLAlchemy error
   - `test_search_logs_pagination` - expects 10 results

### Root Cause:
Similar to Issue #3 - tests assume empty database or specific data only. The regex tests likely have a PostgreSQL vs SQLite regex syntax difference.

### Solution:
1. Create test-specific log entries with unique comment prefixes
2. Search only within those comments
3. Fix regex syntax for PostgreSQL if needed (MySQL `REGEXP` vs PostgreSQL `~`)

### Estimated Effort:
**Low-Medium** - 4-5 tests, may need to adjust regex syntax for PostgreSQL.

---

## Issue #5: Legacy Migration Tests (2 tests)

### Affected Files:
1. **`test_legacy_migration.py`**
   - `test_auth0_creation_fails` 
   - `test_successful_migration`

2. **`test_legacy_login.py`**
   - `test_email_updated_in_database`

### Root Cause:
These tests are known to be problematic with parallel execution (as noted in previous progress docs). They query all users in the database, causing unpredictable counts.

### Solution:
Mark as `@pytest.mark.serial` or adjust to work with shared data.

### Estimated Effort:
**Low** - Already identified as incompatible with parallel execution. May just document and skip.

---

## Issue #6: Include Photos Tests (7 tests)

### Affected Files:
1. **`test_logs_include_photos.py`** (3 tests)
2. **`test_trig_logs_include_photos.py`** (2 tests)
3. **`test_logs_photo_urls.py`** (3 tests)

### Root Cause:
Likely same as Issue #2 - hardcoded IDs or expecting specific database state.

### Estimated Effort:
**Low-Medium** - Similar to other photo tests, likely need to remove hardcoded IDs.

---

## Issue #7: PII Scope Tests (2 tests)

### Affected Files:
1. **`test_pii_scope_authorization.py`**
   - `test_update_non_pii_fields_without_pii_scope_succeeds`
   - `test_update_pii_with_scope_succeeds`

### Root Cause:
Already has unique test_user fixture, so likely an issue with the test logic or assertions, not data collisions.

### Estimated Effort:
**Low** - Only 2 tests, need to investigate specific failure.

---

## Summary by Priority

### High Priority (Quick Wins - 35 tests)
1. **Issue #1: Hardcoded Usernames** (~20 tests) - Same pattern we've been using
2. **Issue #2: Hardcoded Photo/TLog IDs** (~15 tests) - Same pattern we've been using

### Medium Priority (Require Thought - 14 tests)
3. **Issue #3: Empty Database Assumptions** (2 tests) - Requires test redesign
4. **Issue #4: Log Search Tests** (5 tests) - Requires filtering by test data
5. **Issue #6: Include Photos Tests** (7 tests) - Likely same as Issue #2

### Low Priority (Edge Cases - 20 tests)
6. **Issue #5: Legacy Migration Tests** (3 tests) - May skip for parallel execution
7. **Issue #7: PII Scope Tests** (2 tests) - Need investigation

---

## Recommended Approach

### Phase 1: Apply Known Patterns (Est. 2-3 hours)
1. Fix `test_crud_user_creation.py` - Add UUID suffixes
2. Fix `test_auth0_username_mapping.py` - Add UUID suffixes  
3. Fix `test_crud_email_functions.py` - Add UUID suffixes
4. Fix `test_auth0_provisioning_flow.py` - Add UUID suffixes
5. Fix `test_photo_rotate.py` - Remove hardcoded IDs
6. Fix `test_deleted_photo_filtering.py` - Remove hardcoded IDs

**Expected result: ~40-50 tests passing**

### Phase 2: Redesign Database-Dependent Tests (Est. 1-2 hours)
7. Fix `test_crud.py` - Filter by test data
8. Fix `test_log_search.py` - Filter by test data, fix regex
9. Fix include photos tests - Likely same as Phase 1

**Expected result: ~10-15 more tests passing**

### Phase 3: Handle Edge Cases (Est. 1 hour)
10. Investigate `test_pii_scope_authorization.py` failures
11. Mark legacy migration tests as serial or skip

**Expected result: Final 5-10 tests passing or documented**

---

## Total Estimated Effort
**4-6 hours** to get all 69 tests passing or properly handled.

The majority (Phase 1) can be done quickly using the patterns we've already established.

