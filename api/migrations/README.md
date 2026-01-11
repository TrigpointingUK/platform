# Database Migration: Make TLog Location Fields Nullable

> **Note**: This is a legacy migration from when the database was MySQL.
> The database has since been migrated to PostgreSQL and all new migrations
> should use Alembic. See `/api/migrations/ALEMBIC_GUIDE.md` for current practices.

## Summary
This migration makes the location fields (`osgb_eastings`, `osgb_northings`, `osgb_gridref`) in the `tlog` table nullable, allowing users to create logs without specifying a location.

## Status
**COMPLETED** - This migration was applied to the MySQL database before the PostgreSQL migration.
The schema changes were preserved during the database migration.

## Files Changed
- `api/models/user.py` - Updated TLog model
- `api/schemas/tlog.py` - Updated TLogBase and TLogCreate schemas
- `api/migrations/001_make_tlog_location_nullable.sql` - Legacy SQL migration script (MySQL syntax)

## Impact
- Existing logs: No data changes
- New logs: Can be created without location data
- API: No longer returns 422 error when location fields are omitted

