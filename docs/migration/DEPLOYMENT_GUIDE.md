# PostgreSQL Migration Deployment Guide

This guide provides step-by-step instructions for deploying the PostgreSQL migration.

## Prerequisites

- [x] All Terraform configurations created
- [x] Application code updated for PostgreSQL
- [x] Migration scripts created and tested
- [ ] Backup of current MySQL database
- [ ] Maintenance window scheduled

## Pre-Deployment Checklist

### 1. Backup Current State
```bash
# On bastion host - backup MySQL database
mysqldump -h <mysql-rds-endpoint> -u admin -p \
  --databases tuk_production tuk_staging \
  --single-transaction \
  --routines --triggers \
  > mysql_backup_$(date +%Y%m%d_%H%M%S).sql

# Upload to S3
aws s3 cp mysql_backup_*.sql s3://trigpointing-backups/mysql-migration/
```

### 2. Test Locally
```bash
# Start local PostgreSQL with PostGIS
docker-compose -f docker-compose.dev.yml up -d db

# Wait for database to be ready
docker-compose -f docker-compose.dev.yml logs -f db

# Run migrations (if using Alembic)
# alembic upgrade head

# Start API
docker-compose -f docker-compose.dev.yml up api

# Test endpoints
curl http://localhost:8000/v1/trigs?center_lat=51.5&center_lon=-0.1&max_km=10
```

## Deployment Steps

### Phase 1: Deploy Infrastructure (Staging First)

#### 1.1 Deploy PostgreSQL RDS

```bash
# From local machine
cd terraform/common

# Review changes
terraform plan

# Apply (creates PostgreSQL RDS)
terraform apply

# Note the outputs
terraform output postgres_rds_endpoint
terraform output postgres_rds_master_secret_arn
```

#### 1.2 Deploy PostgreSQL Schemas and Users

```bash
# From local machine - deploy to bastion
cd terraform
./deploy.sh postgres

# This will:
# - Copy postgres terraform to bastion
# - SSH to bastion
# - Run terraform to create databases and users
# - Store credentials in AWS Secrets Manager
```

**Alternatively, manual SSH approach:**
```bash
# SSH to bastion
ssh -i ~/.ssh/trigpointing-bastion.pem ec2-user@bastion.trigpointing.uk

# Navigate to postgres terraform directory
cd /home/ec2-user/postgres-terraform

# Initialize and apply
terraform init -backend-config=backend.conf
terraform plan
terraform apply
```

#### 1.3 Verify Infrastructure

```bash
# On bastion host - connect to PostgreSQL
psql -h <postgres-rds-endpoint> -U postgres -d postgres

# Verify databases exist
\l

# Verify PostGIS extension
\dx

# Verify users
\du

# Exit
\q
```

### Phase 2: Migrate Data

#### 2.1 Export from MySQL

```bash
# Activate venv
source venv/bin/activate

# Set MySQL environment variables
export MYSQL_HOST=<mysql-rds-endpoint>
export MYSQL_PORT=3306
export MYSQL_USER=fastapi_staging  # Or fastapi_production
export MYSQL_PASSWORD=<from-secrets-manager>
export MYSQL_DB=tuk_staging  # Or tuk_production

# Run export
python scripts/export_mysql_to_postgres.py --output-dir ./mysql_export_staging

# This creates CSV files in ./mysql_export_staging/
```

#### 2.2 Transform Coordinates

```bash
# Transform coordinates to PostGIS WKT format
python scripts/transform_coordinates_to_postgis.py --input-dir ./mysql_export_staging

# This creates *_transformed.csv files with location column
```

#### 2.3 Import to PostgreSQL

```bash
# Set PostgreSQL environment variables
export DB_HOST=<postgres-rds-endpoint>
export DB_PORT=5432
export DB_USER=fastapi_staging  # Or fastapi_production
export DB_PASSWORD=<from-secrets-manager>
export DB_NAME=tuk_staging  # Or tuk_production

# Run import
python scripts/import_postgres.py --input-dir ./mysql_export_staging

# This:
# - Creates tables via SQLAlchemy
# - Imports CSV data in dependency order
# - Creates spatial indexes
# - Runs ANALYZE
```

#### 2.4 Validate Migration

```bash
# Validate data integrity
python scripts/validate_migration.py

# Review output for:
# - Row count matches
# - Spatial data validation
# - Foreign key integrity
# - Sample data spot checks
```

### Phase 3: Deploy Application Code (Staging)

#### 3.1 Update Environment Variables

```bash
# In staging environment (Terraform or ECS task definition)
DB_HOST=<postgres-rds-endpoint>
DB_PORT=5432
DB_USER=fastapi_staging
DB_PASSWORD=<from-secrets-manager>
DB_NAME=tuk_staging
```

#### 3.2 Deploy Updated Code

```bash
# Commit changes
git add .
git commit -m "feat: migrate from MySQL to PostgreSQL with PostGIS"
git push origin develop

# Deploy to staging (via CI/CD or manual)
# Update ECS task definition with new code
# ECS will automatically pull new image and restart tasks
```

#### 3.3 Test Staging

```bash
# Test key endpoints
curl https://api.trigpointing.me/v1/health
curl https://api.trigpointing.me/v1/trigs?center_lat=51.5&center_lon=-0.1&max_km=10
curl https://api.trigpointing.me/v1/trigs/geojson

# Test map display
# - Open staging web app
# - Verify map loads with trig points
# - Test search by location
# - Test distance-based queries

# Run API tests
pytest api/tests/

# Monitor logs for errors
aws logs tail /ecs/trigpointing-staging --follow
```

### Phase 4: Production Deployment

#### 4.1 Schedule Maintenance Window

- Announce maintenance window to users (e.g., 2 AM - 4 AM)
- Update status page
- Prepare rollback plan

#### 4.2 Enable Maintenance Mode

```bash
# Put site in maintenance mode
# (Update ALB to redirect to maintenance page or similar)
```

#### 4.3 Final MySQL Export

```bash
# Export production data
export MYSQL_DB=tuk_production
export MYSQL_USER=fastapi_production
python scripts/export_mysql_to_postgres.py --output-dir ./mysql_export_production
```

#### 4.4 Transform and Import

```bash
# Transform coordinates
python scripts/transform_coordinates_to_postgis.py --input-dir ./mysql_export_production

# Import to PostgreSQL
export DB_NAME=tuk_production
export DB_USER=fastapi_production
python scripts/import_postgres.py --output-dir ./mysql_export_production

# Validate
python scripts/validate_migration.py
```

#### 4.5 Deploy Production Code

```bash
# Merge to main
git checkout main
git merge develop
git push origin main

# Update production environment variables
# Deploy code to production ECS
```

#### 4.6 Smoke Test

```bash
# Test critical paths
curl https://api.trigpointing.uk/v1/health
curl https://api.trigpointing.uk/v1/trigs?limit=10

# Test map
# Test user login
# Test trig search
# Test photo upload
```

#### 4.7 Disable Maintenance Mode

```bash
# Remove maintenance page
# Monitor closely for first hour
```

### Phase 5: Post-Deployment

#### 5.1 Monitor

```bash
# Watch logs
aws logs tail /ecs/trigpointing-production --follow

# Monitor CloudWatch metrics
# - CPU usage
# - Memory usage
# - Request count
# - Error rate
# - Response time

# Monitor RDS metrics
# - Connections
# - CPU
# - IOPS
# - Slow queries
```

#### 5.2 Optimize (After 24-48 Hours)

```bash
# On bastion, connect to PostgreSQL
psql -h <postgres-rds-endpoint> -U postgres -d tuk_production

# Check slow queries
SELECT query, mean_exec_time, calls
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;

# Check index usage
SELECT
    schemaname,
    tablename,
    indexname,
    idx_scan,
    idx_tup_read,
    idx_tup_fetch
FROM pg_stat_user_indexes
ORDER BY idx_scan;

# Vacuum and analyze
VACUUM ANALYZE;
```

#### 5.3 Cleanup (After 7 Days)

```bash
# Archive MySQL dumps to S3 (long-term storage)
aws s3 cp mysql_backup_*.sql s3://trigpointing-backups/mysql-migration-archive/

# Keep MySQL RDS running for safety
# DO NOT destroy - MediaWiki and phpBB still need it!

# Clean up local export files
rm -rf mysql_export_*
```

## Rollback Plan

If issues are discovered post-deployment:

### Quick Rollback (Environment Variables)

```bash
# Revert environment variables to MySQL
DB_HOST=<mysql-rds-endpoint>
DB_PORT=3306
DB_NAME=tuk_production

# Restart ECS tasks
aws ecs update-service --cluster trigpointing-cluster \
  --service trigpointing-production --force-new-deployment
```

### Full Rollback (Code)

```bash
# Revert code changes
git revert <commit-hash>
git push origin main

# Deploy old version
# ECS will pull previous image and restart
```

## Troubleshooting

### Connection Issues

```bash
# Verify security groups allow access
aws ec2 describe-security-groups --group-ids <postgres-sg-id>

# Test connection from ECS task
aws ecs execute-command --cluster trigpointing-cluster \
  --task <task-id> --container api \
  --command "psql -h <endpoint> -U fastapi_production -d tuk_production -c '\l'"
```

### Performance Issues

```bash
# Check connection pool
# Adjust DATABASE_POOL_SIZE in config

# Check slow queries
# Add indexes if needed

# Check VACUUM status
SELECT schemaname, relname, last_vacuum, last_autovacuum
FROM pg_stat_user_tables;
```

### Data Issues

```bash
# Re-run validation
python scripts/validate_migration.py

# Check specific table
psql -h <endpoint> -U postgres -d tuk_production
SELECT COUNT(*) FROM trig WHERE location IS NULL;
```

## Success Criteria

- [ ] All infrastructure deployed successfully
- [ ] Data migrated with 100% row count match
- [ ] Spatial queries return correct results
- [ ] No critical errors in logs
- [ ] Response times within acceptable range
- [ ] Map displays correctly
- [ ] User workflows function properly
- [ ] MediaWiki and phpBB unaffected

## Post-Migration Notes

- **MySQL RDS**: Keep running for MediaWiki/phpBB
- **PostgreSQL RDS**: Primary database for FastAPI
- **Monitoring**: Watch for 1 week post-migration
- **Optimization**: Tune parameters based on actual usage
- **Documentation**: Update all references to database type

## Support

If issues arise:
1. Check CloudWatch logs
2. Review validation script output
3. Connect to database and inspect data
4. Consult rollback plan if needed
5. Monitor user reports

---

**Last Updated**: 2025-11-14
**Deployment Target**: Staging first, then Production
**Estimated Downtime**: 1-2 hours for production

