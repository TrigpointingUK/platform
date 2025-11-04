# Database Migration: Make TLog Location Fields Nullable

## Summary
This migration makes the location fields (`osgb_eastings`, `osgb_northings`, `osgb_gridref`) in the `tlog` table nullable, allowing users to create logs without specifying a location.

## Files Changed
- `api/models/user.py` - Updated TLog model
- `api/schemas/tlog.py` - Updated TLogBase and TLogCreate schemas
- `api/migrations/001_make_tlog_location_nullable.sql` - SQL migration script

## Running the Migration

### Option 1: Via Bastion Host (Production/Staging)
```bash
# SSH to bastion
ssh -i ~/.ssh/trigpointing-bastion.pem ec2-user@bastion.trigpointing.uk

# Connect to MySQL
mysql -h <rds-endpoint> -u <admin-user> -p <database-name>

# Run the migration
source /path/to/001_make_tlog_location_nullable.sql
```

### Option 2: Direct MySQL (if you have access)
```bash
# From the api directory
mysql -h localhost -u root -p trigpoin_trigs < api/migrations/001_make_tlog_location_nullable.sql
```

### Option 3: Using MySQL Workbench or other GUI
1. Connect to the database
2. Open `api/migrations/001_make_tlog_location_nullable.sql`
3. Execute the SQL statements

## Verification
After running the migration, verify the changes:
```sql
DESCRIBE tlog;
```

The output should show:
- `osgb_eastings` - NULL: YES
- `osgb_northings` - NULL: YES
- `osgb_gridref` - NULL: YES

## Rollback (if needed)
If you need to revert this change:
```sql
-- WARNING: This will fail if any rows have NULL values in these columns
ALTER TABLE tlog 
  MODIFY COLUMN osgb_eastings INT NOT NULL,
  MODIFY COLUMN osgb_northings INT NOT NULL,
  MODIFY COLUMN osgb_gridref VARCHAR(14) NOT NULL;
```

## Impact
- Existing logs: No data changes
- New logs: Can be created without location data
- API: No longer returns 422 error when location fields are omitted

