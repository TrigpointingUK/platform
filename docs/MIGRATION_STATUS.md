# MySQL to PostgreSQL Migration - Implementation Status

## Completed Tasks

### Phase 1: Infrastructure Setup ✅
- [x] Created `terraform/postgres/` directory structure
- [x] Created `terraform/postgres/main.tf` - PostgreSQL provider configuration
- [x] Created `terraform/postgres/variables.tf` - Variables
- [x] Created `terraform/postgres/backend.conf` - S3 backend configuration
- [x] Created `terraform/common/rds-postgres.tf` - PostgreSQL RDS instance
- [x] Created `terraform/postgres/schemas.tf` - Databases, users, and PostGIS extensions
- [x] Created `terraform/postgres/secrets.tf` - AWS Secrets Manager integration
- [x] Created `terraform/postgres/outputs.tf` - Terraform outputs
- [x] Created `terraform/postgres/deploy.sh` - Deployment script
- [x] Created `terraform/postgres/README.md` - Documentation
- [x] Updated `terraform/common/outputs.tf` - Added PostgreSQL RDS outputs

### Phase 2: Application Code Changes (In Progress) 🟡
- [x] Updated `requirements.txt` - Replaced `pymysql` with `psycopg2-binary`, added `geoalchemy2`
- [x] Updated `api/core/config.py` - Changed DATABASE_URL to PostgreSQL
- [x] Updated `api/models/trig.py` - Added PostGIS Geography column and hybrid properties
- [x] Updated `api/crud/trig.py` - Replaced haversine with PostGIS ST_Distance/ST_DWithin

### Phase 3: Data Migration Scripts ✅
- [x] Created `scripts/export_mysql_to_postgres.py` - MySQL data export
- [x] Created `scripts/transform_coordinates_to_postgis.py` - Coordinate transformation
- [x] Created `scripts/import_postgres.py` - PostgreSQL data import
- [x] Created `scripts/validate_migration.py` - Data validation
- [x] Created `scripts/run_migration_on_bastion.sh` - Orchestration script
- [x] Created `docs/migration/MIGRATION_QUICKSTART.md` - Operator guide

### Phase 4: Validation & Testing ⏳
- [ ] Data integrity validation
- [ ] Query performance testing
- [ ] Application testing

### Phase 5: Deployment ⏳
- [ ] Staging deployment
- [ ] Production deployment

### Phase 6: Optimization & Cleanup ⏳
- [ ] Post-migration optimization
- [ ] Code cleanup
- [ ] Documentation updates

## Key Changes Summary

### Database Driver
- **Before**: `mysql+pymysql://`
- **After**: `postgresql+psycopg2://`

### Spatial Data Storage
- **Before**: Separate `DECIMAL(7,5)` columns for lat/lon + haversine distance calculation
- **After**: PostGIS `GEOGRAPHY(POINT, 4326)` column + native `ST_Distance`/`ST_DWithin`

### Benefits of PostGIS
1. Native spherical earth calculations (accurate)
2. Spatial indexing (GiST) for performance
3. Rich set of spatial functions
4. Industry standard for geospatial data

### Database Port
- **Before**: MySQL port 3306
- **After**: PostgreSQL port 5432

## Next Steps

1. ~~Complete `scripts/import_postgres.py`~~ ✅ Done
2. ~~Complete `scripts/validate_migration.py`~~ ✅ Done
3. **RUN MIGRATION**: Execute `./scripts/run_migration_on_bastion.sh`
4. **Test the application** against PostgreSQL database locally
5. **Deploy to staging** and test thoroughly
6. **Schedule production maintenance window**
7. **Run production migration**
8. **Monitor** for 24-48 hours
9. **Cleanup** after 7 days (remove MySQL deps, migration scripts)

## Architecture Notes

### Hybrid Database Approach
- **PostgreSQL RDS**: For FastAPI backend (production & staging)
- **MySQL RDS**: Continues to serve MediaWiki & phpBB (unchanged)
- Both coexist in same VPC, separate RDS instances

### Security Groups
- New security group: `postgres_rds` 
- Allows access from:
  - FastAPI ECS tasks
  - Bastion host
  - phpMyAdmin/pgAdmin

## Important Reminders

1. **DO NOT destroy MySQL RDS** - MediaWiki and phpBB still need it
2. **Run Terraform from bastion** - PostgreSQL user creation requires bastion host access
3. **Test thoroughly on staging** - Before production migration
4. **Keep MySQL running for 7 days** - As rollback safety net
5. **Backup before migration** - Create RDS snapshot before final migration

