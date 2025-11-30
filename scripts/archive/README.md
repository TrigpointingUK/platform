# Archived Scripts

This directory contains scripts and documentation that are no longer needed for day-to-day operations but are preserved for historical reference.

## Contents

### Alembic Migration Scripts (Superseded by Makefile)

These scripts were used to run Alembic migrations on the bastion host. They've been replaced by simpler Makefile targets:

- `run_alembic_on_bastion_staging.sh` - Use `make migrate-staging` instead
- `run_alembic_on_bastion_production.sh` - Use `make migrate-production` instead
- `run_migration_on_bastion.sh` - Legacy script
- `run_migration_on_bastion_prod.sh` - Legacy script

**Current approach:** Use `make migrate-staging` or `make migrate-production` with SSM tunnels. See `api/migrations/ALEMBIC_GUIDE.md` for details.

### MySQL to PostgreSQL Migration Scripts (One-time migration, completed)

These scripts were used for the one-time migration from MySQL to PostgreSQL:

- `export_mysql_to_postgres.py` - Export data from MySQL
- `import_postgres.py` - Import data into PostgreSQL
- `create_postgres_schema.py` - Create PostgreSQL schema
- `fix_sequences.py` - Fix sequence values after import
- `transform_coordinates_to_postgis.py` - Convert coordinates to PostGIS format
- `validate_migration.py` - Validate migration success
- `convert_postcodes_to_sql.py` - Convert postcode data

**Status:** Migration completed November 2025. Scripts retained for reference only.

### Legacy Documentation

These documents relate to the MySQL→PostgreSQL migration and other one-time fixes:

- `POSTGRES_DEPLOYMENT_CHECKLIST.md` - Migration deployment steps
- `FIX_AUTH0_RACE_CONDITION.md` - Auth0 race condition fix
- `FIX_INVALID_EMAIL_HANDLING.md` - Email validation fix
- `IMPLEMENTATION_SUMMARY.md` - Migration implementation summary
- `UPDATE_DUPLICATE_DETECTION.md` - Duplicate detection improvements

## Deletion Plan

These files are scheduled for deletion after **2025-12-31** (one month retention period).

If you need to reference these scripts before then, they will be available in git history even after deletion.

## Current Workflow

For current database migration workflows, see:
- `api/migrations/ALEMBIC_GUIDE.md` - Complete Alembic guide
- `Makefile` - Migration targets (`make migrate-staging`, etc.)
- `DATABASE_CLEANUP_SUMMARY.md` - Template for future database cleanups

---

*Archived: 2025-11-30*
