# pg_cron Production Cutover Instructions

## Background

The `pg_cron` extension in AWS RDS PostgreSQL can **only be enabled in ONE database per RDS instance**. Currently, it may be configured for `tuk_staging`, but for the production cutover it needs to be on `tuk_production`.

## What Was Updated

The following files have been updated to ensure pg_cron is configured for production:

1. **terraform/common/terraform.tfvars** - Added explicit `postgres_cron_database_name = "tuk_production"`
2. **terraform/common/variables.tf** - Updated description with limitation note
3. **terraform/common/rds-postgres.tf** - Added comments explaining the limitation
4. **terraform/postgres/variables.tf** - Updated description with limitation note
5. **terraform/postgres/schemas.tf** - Added comprehensive comments about the limitation
6. **terraform/postgres/README.md** - Added detailed documentation section

## How to Apply Changes

⚠️ **IMPORTANT**: These changes require an RDS instance reboot. Plan accordingly.

### Step 1: Review Changes

```bash
cd terraform/common
terraform plan
```

Look for changes to the parameter group, specifically:
- `cron.database_name` should be set to `tuk_production`

### Step 2: Apply Terraform Changes (Common Infrastructure)

```bash
cd terraform/common
terraform apply
```

**Expected**: This will modify the RDS parameter group. The change requires a pending reboot.

### Step 3: Apply Terraform Changes (PostgreSQL Schemas)

```bash
# From bastion host
cd terraform/postgres
terraform plan
terraform apply
```

**Expected**: This will:
- Enable `pg_cron` extension in `tuk_production` database (count = 1)
- Skip `pg_cron` extension in `tuk_staging` database (count = 0)
- Grant proper permissions on cron schema to `fastapi_production` user

### Step 4: Reboot RDS Instance

The parameter group changes require a reboot. You can either:

**Option A: Schedule during maintenance window** (automatically applied)
```bash
# Check if pending reboot
aws rds describe-db-instances \
  --db-instance-identifier trigpointing-postgres \
  --query 'DBInstances[0].PendingModifiedValues'
```

**Option B: Apply immediately** (causes brief downtime)
```bash
aws rds reboot-db-instance \
  --db-instance-identifier trigpointing-postgres
```

### Step 5: Verify pg_cron is Available

From the bastion host, connect to production database:

```bash
ssh -i ~/.ssh/trigpointing-bastion.pem ec2-user@bastion.trigpointing.uk
./connect-to-postgres-master.sh
```

Then in PostgreSQL:

```sql
-- Connect to production database
\c tuk_production

-- Check if pg_cron extension exists
SELECT * FROM pg_extension WHERE extname = 'pg_cron';

-- Check if cron schema exists
\dn cron

-- Check if you can query cron jobs
SELECT * FROM cron.job;
```

Expected output: You should see the cron extension and schema.

### Step 6: Run Alembic Migrations

Now you can successfully run the Alembic migrations:

```bash
# From local machine
./scripts/run_alembic_on_bastion_production.sh
```

This should now succeed because the `cron` schema exists in the production database.

### Step 7: Verify Cron Job is Scheduled

After migrations complete, verify the job was created:

```sql
-- From bastion, connected to tuk_production
SELECT jobid, jobname, schedule, command, active
FROM cron.job
WHERE jobname = 'refresh_user_activity_summary_every_5m';
```

Expected output: One row showing the scheduled job.

## What About Staging?

After this change, **staging will NOT have pg_cron available**. This is expected and acceptable because:

1. The materialized view refresh is less critical in staging
2. Staging can be tested without cron jobs
3. Production needs the automatic refresh for user activity stats

If you need to test pg_cron functionality in staging in the future:
1. Update `postgres_cron_database_name = "tuk_staging"` in terraform/common/terraform.tfvars
2. Apply Terraform and reboot RDS
3. Note: This will **disable** pg_cron in production temporarily

## Rollback Procedure

If you need to rollback to staging having pg_cron:

```bash
# Edit terraform/common/terraform.tfvars
postgres_cron_database_name = "tuk_staging"

# Apply changes
cd terraform/common
terraform apply

# Reboot RDS
aws rds reboot-db-instance --db-instance-identifier trigpointing-postgres

# Re-apply postgres schemas
cd terraform/postgres
terraform apply
```

## Timeline Estimate

- **Planning**: Review this document (10 minutes)
- **Terraform apply**: ~2 minutes each for common and postgres
- **RDS reboot**: ~5-10 minutes downtime
- **Alembic migrations**: ~1 minute
- **Verification**: ~5 minutes

**Total time**: ~25-30 minutes
**Downtime window**: ~5-10 minutes during RDS reboot

## Troubleshooting

### Issue: "permission denied for schema cron"

This means pg_cron is not enabled in the database you're connected to. Verify:
1. Check `cron.database_name` parameter: `SHOW cron.database_name;`
2. Ensure you've connected to the correct database
3. Verify the extension was created: `SELECT * FROM pg_extension WHERE extname = 'pg_cron';`

### Issue: "cron schema not found"

The RDS instance hasn't been rebooted yet. The parameter change is pending.

### Issue: Staging tests need pg_cron

Consider:
1. Use production-like data in production for testing
2. Test cron functionality locally with PostgreSQL + pg_cron
3. Temporarily switch pg_cron to staging (see "What About Staging?" section)

## References

- AWS RDS PostgreSQL pg_cron: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/PostgreSQL_pg_cron.html
- pg_cron GitHub: https://github.com/citusdata/pg_cron

