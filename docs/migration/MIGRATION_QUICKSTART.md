# PostgreSQL Migration - Quick Start Guide

This guide explains how to run the complete MySQL to PostgreSQL migration.

## Prerequisites

1. **PostgreSQL RDS deployed**: Run `cd terraform && ./deploy.sh common`
2. **Access to bastion host**: SSH key at `~/.ssh/trigpointing-bastion.pem`
3. **Migration dependencies installed locally**: `pip install -r requirements-migration.txt`

## Migration Overview

The migration consists of 4 steps, all automated:

1. **Export**: Extract data from MySQL RDS to CSV files
2. **Transform**: Convert lat/lon coordinates to PostGIS WKT format
3. **Import**: Load CSV data into PostgreSQL with spatial indexes
4. **Validate**: Compare row counts and verify spatial data accuracy

## Running the Migration

### Option 1: Complete Migration (Recommended)

Run the entire pipeline on the bastion host:

```bash
./scripts/run_migration_on_bastion.sh
```

This script will:
- Copy all migration scripts to the bastion
- Set up a Python virtual environment
- Install dependencies
- Run all 4 migration steps
- Report validation results

**Duration**: Approximately 10-30 minutes (depends on database size)

### Option 2: Step-by-Step Migration

For more control, run individual steps:

#### Step 1: Export MySQL Data

```bash
./scripts/run_migration_on_bastion.sh --export-only
```

This exports MySQL data to `/home/ec2-user/postgres-migration/mysql_export/` on the bastion.

#### Step 2: Import to PostgreSQL

After reviewing the export, run the import:

```bash
./scripts/run_migration_on_bastion.sh --import-only
```

## What to Expect

### Successful Migration Output

```
✓ Exported X tables
✓ Transformed coordinates for Y rows
✓ Imported Z rows to PostgreSQL
✓ Created spatial indexes
✓ All validation checks passed
```

### Common Issues

#### MySQL Connection Refused
- **Cause**: Running scripts locally instead of on bastion
- **Solution**: Use `run_migration_on_bastion.sh` which handles this

#### Row Count Mismatch
- **Cause**: Data changes between export and import, or export incomplete
- **Solution**: Re-run the export step

#### NULL Location Columns
- **Cause**: Invalid coordinates in source data
- **Solution**: Review validation warnings, may be acceptable for some records

## After Migration

### 1. Review Validation Report

Check the validation output for:
- ✓ All row counts match
- ✓ Spatial data converted correctly
- ✓ Spatial indexes created

### 2. Download Export for Backup (Optional)

```bash
scp -r -i ~/.ssh/trigpointing-bastion.pem \
  ec2-user@bastion.trigpointing.uk:/home/ec2-user/postgres-migration/mysql_export \
  ./mysql_export_backup
```

### 3. Test the Application

Update `.env` to point to PostgreSQL:

```bash
DB_HOST=trigpointing-postgres.xxxxxx.eu-west-1.rds.amazonaws.com
DB_PORT=5432
DB_NAME=tuk_staging  # or tuk_production
DB_USER=fastapi_staging  # or fastapi_production
DB_PASSWORD=<from AWS Secrets Manager>
```

Then run the application:

```bash
make dev
```

Test key functionality:
- List trigs
- Search by location (distance queries)
- View trig details
- Add/edit trig logs

### 4. Deploy to Staging

Once local testing passes:

```bash
# Update staging environment variables via AWS Console or CLI
cd terraform
./deploy.sh staging
```

### 5. Deploy to Production

After staging testing:

```bash
# Schedule maintenance window
# Update production environment variables
cd terraform
./deploy.sh production
```

## Rollback Plan

If issues arise:

1. **Keep MySQL RDS running** for 7 days post-migration
2. **Revert environment variables** to point back to MySQL
3. **Redeploy previous version** of the application
4. **MySQL dump available** on bastion for emergency restoration

## Database Credentials

Credentials are stored in AWS Secrets Manager:

```bash
# Production PostgreSQL
aws secretsmanager get-secret-value \
  --secret-id trigpointing-postgres-fastapi-production \
  --query SecretString --output text | jq

# Staging PostgreSQL
aws secretsmanager get-secret-value \
  --secret-id trigpointing-postgres-fastapi-staging \
  --query SecretString --output text | jq
```

## Accessing Databases

### Via pgAdmin (Web)
Visit: https://pgadmin.trigpointing.uk (Auth0 login required)

### Via Bastion (CLI)
```bash
ssh -i ~/.ssh/trigpointing-bastion.pem ec2-user@bastion.trigpointing.uk
pg-connect.sh
```

## Monitoring

After migration, monitor:

1. **CloudWatch Metrics**: Database CPU, connections, IOPS
2. **Application Logs**: Check for database errors
3. **Query Performance**: Compare response times to baseline
4. **Spatial Queries**: Verify distance calculations are accurate

## Cleanup (After 7 Days)

Once production is stable:

1. Remove MySQL driver: Edit `requirements.txt`, remove `pymysql`
2. Remove migration scripts: `rm -rf scripts/{export,transform,import,validate}_*.py`
3. Remove migration dependencies: `rm requirements-migration.txt`
4. Update documentation to reflect PostgreSQL as primary database

## Troubleshooting

### SSH to Bastion Fails
Check:
- Bastion instance is running
- Security group allows SSH from your IP
- SSH key has correct permissions (`chmod 600`)

### Import Fails with Foreign Key Error
- Tables are imported in dependency order
- Check that reference tables (status, county, etc.) imported successfully

### Validation Shows Coordinate Mismatch
- PostGIS uses double precision (15-17 significant digits)
- Small differences (<0.000001°) are acceptable
- Large differences indicate transformation error

### Spatial Queries Return No Results
- Check that `location` column is populated
- Verify spatial indexes exist: `\d trig` in psql
- Confirm SRID is 4326 (WGS84)

## Support

For issues:
1. Check `docs/migration/POSTGRESQL_MIGRATION_SUMMARY.md` for technical details
2. Review bastion logs: `/home/ec2-user/postgres-migration/`
3. Check CloudWatch logs for ECS tasks
4. Consult PostgreSQL/PostGIS documentation

---

**Last Updated**: 2025-11-14
**Migration Status**: Ready to execute

