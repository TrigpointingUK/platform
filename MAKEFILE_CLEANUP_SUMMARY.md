# Makefile & Migration Workflow Cleanup Summary

**Date:** 2025-11-30

## Overview

Simplified and rationalized the database migration workflow by:
1. Archiving legacy scripts
2. Removing deprecated Makefile targets
3. Adding new environment-aware migration targets
4. Updating documentation

## Changes Made

### 1. Scripts Archived → `scripts/archive/`

**Migration Scripts (17 files):**
- `run_alembic_on_bastion_staging.sh`
- `run_alembic_on_bastion_production.sh`
- `run_migration_on_bastion.sh`
- `run_migration_on_bastion_prod.sh`
- `export_mysql_to_postgres.py`
- `import_postgres.py`
- `create_postgres_schema.py`
- `fix_sequences.py`
- `transform_coordinates_to_postgis.py`
- `validate_migration.py`
- `convert_postcodes_to_sql.py`
- `POSTGRES_DEPLOYMENT_CHECKLIST.md`
- `FIX_AUTH0_RACE_CONDITION.md`
- `FIX_INVALID_EMAIL_HANDLING.md`
- `IMPLEMENTATION_SUMMARY.md`
- `UPDATE_DUPLICATE_DETECTION.md`
- `README.md` (new - explains archive)

**Scheduled for deletion:** After 2025-12-31

### 2. Makefile Changes

#### Removed Targets (11 total):
- `db-tunnel-staging-start` ❌ (old SSH-based)
- `db-tunnel-staging-stop` ❌ (old SSH-based)
- `db-tunnel-production-start` ❌ (old SSH-based)
- `db-tunnel-production-stop` ❌ (old SSH-based)
- `mysql-staging` ❌ (now PostgreSQL)
- `mysql-production` ❌ (now PostgreSQL)
- `mysql-client` ❌ (now PostgreSQL)
- `docker-run` ❌ (not used)
- `docker-dev` ❌ (not used)
- `docker-down` ❌ (not used)
- `docker-logs` ❌ (not used)

#### Added Targets (3 new):
- `migrate-staging` ✅ - Apply migrations to staging (with SSM tunnel)
- `migrate-production` ✅ - Apply migrations to production (with confirmation)
- `migrate-status` ✅ - Check migration status (ENV=staging|production)

#### Kept Targets:
- All SSM-based tunnels (`db-tunnel-staging-ssm-start`, etc.) ✅
- Test database targets (`test-db-start`, `test-db-stop`) ✅
- Existing migration targets (`migration-create`, etc.) ✅
- Core development targets (`run-staging`, `web-dev`, etc.) ✅

### 3. Code Changes

**alembic/env.py:**
- Added environment indicator: Shows "🔍 Alembic running against: STAGING/PRODUCTION/LOCAL"
- Helps prevent confusion about which database you're targeting

**api/migrations/ALEMBIC_GUIDE.md:**
- Updated Quick Start section with new Make targets
- Rewrote Staging Deployment section (simplified to 3 steps)
- Rewrote Production Deployment section (added safety confirmation)
- Removed references to old bastion scripts

### 4. Variables Updated

**Makefile variables:**
- Removed: `LOCAL_DB_TUNNEL_PORT_PROD` (was 3308, now uses 5433 for both)
- Updated: `PRODUCTION_SECRET_ARN` changed from legacy MySQL to PostgreSQL credentials
- Kept: All other SSM-related variables

## New Workflow

### Daily Development:
```bash
# Terminal 1
make db-tunnel-staging-ssm-start

# Terminal 2
make redis-tunnel-staging-ssm-start

# Terminal 3
make run-staging

# Terminal 4
make web-dev
```

### Creating Migrations:
```bash
# Create migration
make migration-create MSG="add feature"

# Test locally (optional - uses staging via tunnel)
make migration-upgrade
```

### Deploying Migrations:

**Staging:**
```bash
# With tunnel running
make migrate-staging
```

**Production:**
```bash
# With tunnel running
make migrate-production
# (prompts for confirmation)
```

**Check Status:**
```bash
make migrate-status ENV=staging
make migrate-status ENV=production
```

## Benefits

1. **Clearer Environment Context:** Always know which database you're targeting
2. **Simpler Commands:** `make migrate-staging` vs 184-line bash script
3. **Safety:** Production requires explicit "production" confirmation
4. **Consistency:** All migrations follow same pattern
5. **Less Confusion:** No duplicate SSH/SSM tunnel targets
6. **Better Organization:** Legacy scripts archived, not deleted

## Backward Compatibility

- Old scripts still available in `scripts/archive/` for 1 month
- All SSM tunnel commands unchanged
- Development workflow (`make run-staging`, etc.) unchanged
- Test workflow (`make test`) unchanged

## Testing

All changes tested:
- Makefile targets validate correctly
- Environment indicator displays in alembic
- Migration history remains intact
- No breaking changes to existing workflows

## Documentation

Updated files:
- ✅ `Makefile` - Removed old targets, added new ones
- ✅ `alembic/env.py` - Added environment indicator
- ✅ `api/migrations/ALEMBIC_GUIDE.md` - Complete rewrite of deployment sections
- ✅ `scripts/archive/README.md` - Explains archived files
- ✅ This summary document

## Next Steps

1. **Immediate:** Start using new `make migrate-*` targets
2. **Within 1 week:** Verify workflows on both staging and production
3. **After 2025-12-31:** Delete `scripts/archive/` directory

## Rollback Plan

If issues arise, all changes can be reverted via git:
```bash
git revert <commit-hash>
```

Scripts are preserved in archive and git history.

---

**Migration Simplified. Environment Clear. Workflow Streamlined.** ✨
