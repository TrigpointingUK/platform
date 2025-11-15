# PostgreSQL Migration - Staging Deployment

## ✅ Migration Status: COMPLETE

### Database Migration
- **Source**: MySQL RDS (`fastapi-staging-credentials`)
- **Target**: PostgreSQL RDS (`trigpointing-postgres-staging-credentials`)
- **Data**: 39 tables, ~4.8M rows migrated successfully
- **PostGIS**: All 4 spatial tables have location columns and GIST indexes

### Changes Applied

#### 1. Terraform Configuration
**File**: `terraform/staging/main.tf`
- **Changed**: `credentials_secret_arn` from MySQL to PostgreSQL secret
- **Old**: `arn:aws:secretsmanager:eu-west-1:534526983272:secret:fastapi-staging-credentials-udrQoU`
- **New**: `arn:aws:secretsmanager:eu-west-1:534526983272:secret:trigpointing-postgres-staging-credentials-c5XrIG`

#### 2. Dockerfile
**File**: `Dockerfile`
- **Changed**: System dependencies from MySQL to PostgreSQL
- **Removed**: `default-libmysqlclient-dev`
- **Added**: `libpq-dev` (PostgreSQL client library)

#### 3. Requirements (No Changes Needed)
**File**: `requirements.txt`
- ✅ Already has `psycopg2-binary==2.9.10`
- ✅ Already has `geoalchemy2==0.16.0`
- ✅ Already has `sqlalchemy==2.0.44`

#### 4. GitHub Actions (No Changes Needed)
**File**: `.github/workflows/ci.yml`
- ✅ Tests use SQLite in-memory database (no external database required)
- ✅ All test dependencies already in `requirements-dev.txt`

### Deployment Steps

1. **Apply Terraform Changes**:
   ```bash
   cd terraform/staging
   terraform init
   terraform plan
   terraform apply
   ```

2. **Verify Secret Contents**:
   The PostgreSQL secret should contain:
   ```json
   {
     "host": "trigpointing-postgres.czyrbczcs1ak.eu-west-1.rds.amazonaws.com",
     "port": 5432,
     "username": "fastapi_staging",
     "password": "<password>",
     "dbname": "tuk_staging"
   }
   ```

3. **Deploy**:
   - Push to `develop` branch
   - GitHub Actions will build and deploy automatically
   - Or manually: `aws ecs update-service --cluster trigpointing-cluster --service fastapi-staging-service --force-new-deployment`

### Database Configuration

The API is already configured for PostgreSQL:
- **Connection**: Uses `postgresql+psycopg2://` driver (in `api/core/config.py`)
- **Spatial Queries**: PostGIS code already exists in `api/crud/trig.py` (lines 168-188)
- **Models**: `Trig` model has PostGIS `location` column with hybrid properties

### Testing Strategy

#### Phase 1: Current (Baseline with lat/lon)
- Using existing haversine calculations for now
- This allows comparison: PostgreSQL vs MySQL performance
- No code changes required - just database swap

#### Phase 2: PostGIS Optimization (Future)
- Switch to native PostGIS spatial queries
- Update models: `Town`, `Place`, `Postcode6` to use `location` columns
- Replace `wgs_lat`/`wgs_long` access with hybrid properties
- Benchmark: PostgreSQL+haversine vs PostgreSQL+PostGIS

### Verification Checklist

After deployment, verify:

- [ ] API health check passes: `https://api.trigpointing.me/health`
- [ ] Database connection works: Check logs for connection errors
- [ ] Spatial queries work: Test trig search endpoint with `center_lat`/`center_lon`
- [ ] GeoJSON export works: `/v1/trigs/geojson`
- [ ] Performance: Compare response times vs MySQL baseline
- [ ] Check CloudWatch logs for any database errors

### Rollback Plan

If issues occur:

1. **Immediate**: Revert Terraform change
   ```bash
   cd terraform/staging
   git checkout HEAD~1 main.tf
   terraform apply
   ```

2. **Full Rollback**: Previous MySQL secret will still work
   - Database is still intact
   - No data loss

### PostgreSQL Advantages Already Realized

1. **Data Integrity**: Stricter NULL handling
2. **Spatial Indexes**: GIST indexes on all location columns
3. **Better Query Planner**: More sophisticated optimization
4. **JSON Support**: Native JSONB for future features
5. **Full-Text Search**: Native support (vs MySQL limited)
6. **Extension Ecosystem**: PostGIS for spatial, pg_trgm for fuzzy search, etc.

### Next Steps (Future Optimizations)

1. **PostGIS Full Migration**:
   - Update `Town`, `Place`, `Postcode6` models
   - Switch all endpoints to use PostGIS queries
   - Add spatial joins (e.g., trigs near places)

2. **Indexing Optimization**:
   - Review query patterns
   - Add compound indexes where needed
   - Consider partial indexes for common filters

3. **Connection Pooling**:
   - Monitor connection usage
   - Adjust `DATABASE_POOL_SIZE` if needed
   - Consider pgBouncer for connection pooling

4. **Monitoring**:
   - Set up CloudWatch alarms for slow queries
   - Monitor connection pool exhaustion
   - Track spatial query performance

### Contact

For issues or questions, check:
- CloudWatch Logs: `/aws/ecs/trigpointing-staging`
- ECS Service: `fastapi-staging-service`
- RDS Instance: `trigpointing-postgres`

