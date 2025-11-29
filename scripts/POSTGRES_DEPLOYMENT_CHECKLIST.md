# PostgreSQL Deployment Checklist

## Pre-Deployment Verification

- [x] Database migrated (39 tables, 4.8M rows)
- [x] Spatial indexes created (GIST on location columns)
- [x] Terraform updated (staging secret ARN)
- [x] Dockerfile updated (PostgreSQL dependencies)
- [x] All packages verified (psycopg2, geoalchemy2)
- [ ] Local testing complete
- [ ] Git changes committed

## Deployment Steps

### 1. Apply Terraform
```bash
cd terraform/staging
terraform init
terraform plan    # Verify only task definition changes
terraform apply   # Type 'yes' when ready
```

### 2. Deploy via Git
```bash
cd /home/ianh/dev/platform
git status
git add terraform/staging/main.tf Dockerfile POSTGRES_MIGRATION_COMPLETE.md scripts/POSTGRES_DEPLOYMENT_CHECKLIST.md
git commit -m "feat(staging): Switch to PostgreSQL RDS

- Update ECS task to use fastapi-staging-postgres-credentials
- Replace MySQL client libs with PostgreSQL (libpq-dev)
- All 39 tables migrated with 4.8M rows
- PostGIS spatial indexes ready for future optimization
"
git push origin develop
```

### 3. Monitor Deployment
```bash
# Watch ECS service update
aws ecs describe-services \
  --cluster trigpointing-cluster \
  --services fastapi-staging-service \
  --query 'services[0].{Desired:desiredCount,Running:runningCount,Status:status}' \
  --output table

# Watch logs in real-time
aws logs tail /aws/ecs/trigpointing-staging --follow --since 5m
```

## Post-Deployment Verification

### Health Check
```bash
curl -v https://api.trigpointing.me/health
# Expected: 200 OK with {"status": "healthy"}
```

### Database Connection Test
```bash
# Check logs for successful DB connection
aws logs filter-log-events \
  --log-group-name /aws/ecs/trigpointing-staging \
  --start-time $(date -u -d '5 minutes ago' +%s)000 \
  --filter-pattern "Database" \
  --limit 20
```

### Functional Tests

1. **Basic Query**:
   ```bash
   curl "https://api.trigpointing.me/v1/trigs?limit=5" | jq .
   ```

2. **Spatial Query** (haversine distance):
   ```bash
   curl "https://api.trigpointing.me/v1/trigs?center_lat=51.5074&center_lon=-0.1278&max_km=10&limit=5" | jq .
   ```

3. **GeoJSON Export**:
   ```bash
   curl "https://api.trigpointing.me/v1/trigs/geojson?limit=100" | jq '.fbm.features | length'
   ```

4. **User Endpoint**:
   ```bash
   curl "https://api.trigpointing.me/v1/users?limit=5" | jq .
   ```

5. **Log Endpoint**:
   ```bash
   curl "https://api.trigpointing.me/v1/logs?limit=5" | jq .
   ```

## Performance Baseline

### Capture Metrics
```bash
# Time a spatial query
time curl -s "https://api.trigpointing.me/v1/trigs?center_lat=51.5074&center_lon=-0.1278&max_km=50&limit=100" > /dev/null

# Check CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/ECS \
  --metric-name CPUUtilization \
  --dimensions Name=ServiceName,Value=fastapi-staging-service Name=ClusterName,Value=trigpointing-cluster \
  --start-time $(date -u -d '30 minutes ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average \
  --output table
```

### Compare: MySQL vs PostgreSQL

| Metric | MySQL Baseline | PostgreSQL | Change |
|--------|---------------|------------|--------|
| Spatial query (10km) | __ ms | __ ms | __ % |
| Spatial query (50km) | __ ms | __ ms | __ % |
| List trigs (100) | __ ms | __ ms | __ % |
| GeoJSON export | __ ms | __ ms | __ % |
| CPU utilization | __ % | __ % | __ % |
| Memory usage | __ MB | __ MB | __ % |

## Rollback Procedure

If critical issues occur:

```bash
cd terraform/staging

# Revert to MySQL
git checkout HEAD~1 main.tf

# Verify change
git diff HEAD main.tf

# Apply
terraform apply

# Force new deployment
aws ecs update-service \
  --cluster trigpointing-cluster \
  --service fastapi-staging-service \
  --force-new-deployment

# Monitor rollback
aws logs tail /aws/ecs/trigpointing-staging --follow
```

## Known Good State

- **MySQL Secret**: `arn:aws:secretsmanager:eu-west-1:534526983272:secret:fastapi-staging-credentials-udrQoU`
- **PostgreSQL Secret**: `arn:aws:secretsmanager:eu-west-1:534526983272:secret:fastapi-staging-postgres-credentials`
- **Database Host**: `trigpointing-postgres.czyrbczcs1ak.eu-west-1.rds.amazonaws.com`
- **Database Name**: `tuk_staging`
- **Tables**: 39 (all migrated)
- **Rows**: ~4.8M (verified)
- **Indexes**: Spatial GIST indexes on `trig`, `place`, `town`, `postcode6`

## Troubleshooting

### Connection Errors
```bash
# Check if secret is accessible
aws secretsmanager get-secret-value \
  --secret-id fastapi-staging-postgres-credentials \
  --region eu-west-1 \
  --query 'SecretString' \
  | jq .

# Verify RDS security group allows ECS
aws ec2 describe-security-groups \
  --filters "Name=tag:Name,Values=*postgres*" \
  --query 'SecurityGroups[].{ID:GroupId,Name:GroupName,Rules:IpPermissions}' \
  --output table
```

### Query Errors
```bash
# Search for SQL errors in logs
aws logs filter-log-events \
  --log-group-name /aws/ecs/trigpointing-staging \
  --start-time $(date -u -d '10 minutes ago' +%s)000 \
  --filter-pattern "ERROR" \
  --limit 50
```

### Performance Issues
```bash
# Check database connections
aws rds describe-db-instances \
  --db-instance-identifier trigpointing-postgres \
  --query 'DBInstances[0].{Status:DBInstanceStatus,Connections:DBInstanceIdentifier}' \
  --output table

# Monitor RDS metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/RDS \
  --metric-name DatabaseConnections \
  --dimensions Name=DBInstanceIdentifier,Value=trigpointing-postgres \
  --start-time $(date -u -d '1 hour ago' +%Y-%m-%dT%H:%M:%S) \
  --end-time $(date -u +%Y-%m-%dT%H:%M:%S) \
  --period 300 \
  --statistics Average,Maximum \
  --output table
```

## Success Criteria

- [ ] Health endpoint returns 200 OK
- [ ] All 5 functional tests pass
- [ ] No errors in logs for 15 minutes
- [ ] Spatial queries return correct results
- [ ] Response times similar to MySQL (within 20%)
- [ ] No connection pool exhaustion
- [ ] ECS service stable (no task restarts)

## Next Phase: PostGIS Optimization

After successful PostgreSQL deployment and baseline metrics:

1. Update models to use PostGIS location columns
2. Replace haversine calculations with `ST_Distance`
3. Benchmark: PostgreSQL+haversine vs PostgreSQL+PostGIS
4. Document performance improvements

Expected improvements with PostGIS:
- Faster spatial queries (leveraging GIST indexes)
- More accurate distance calculations (spherical earth)
- Native spatial operations (within, contains, intersects)
- Reduced application-side calculations

