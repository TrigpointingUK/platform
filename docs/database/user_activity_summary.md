# User Activity Summary Refresh Options

## Manual refresh via Admin API

- Endpoint: `POST /v1/admin/user-stats/refresh`
- Auth: requires bearer token with `api:admin`
- Behaviour: issues `REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary`
- Example:

```bash
curl -X POST \
  -H "Authorization: Bearer ${ADMIN_TOKEN}" \
  https://api.trigpointing.me/v1/admin/user-stats/refresh
```

The response returns HTTP `202 Accepted` with metadata indicating the refresh start timestamp. Concurrent refresh means existing readers keep working while the view is rebuilt.

## Scheduled refresh via pg_cron

### ⚠️ Important RDS Limitation

**`pg_cron` can only be enabled in ONE database per RDS instance.** This is controlled by the `cron.database_name` parameter, which defaults to `tuk_production`.

**Implications:**
- **Production database**: The `pg_cron` job will automatically refresh the materialized view every 5 minutes.
- **Staging database**: No automatic refresh occurs. The view must be refreshed manually or via the admin API endpoint.
- If you need `pg_cron` in staging, you must change `cron.database_name` to `tuk_staging` and reboot, but this will **disable** automatic refreshes in production.

For most use cases, automatic refresh in production is sufficient. Staging can use manual refreshes during testing.

### Setup Instructions

1. **Enable pg_cron (Terraform managed)**
   - `terraform/common` now sets `shared_preload_libraries = 'pg_cron'` and `cron.database_name` via `var.postgres_cron_database_name` (default `tuk_production`)
   - After applying that stack, reboot the instance to load the library
   - `terraform/postgres` creates `pg_cron` in the target database using the master connection; no manual SQL is required once the parameter update is active

2. **Grant permissions (Terraform managed)**
   - `terraform/postgres/schemas.tf` automatically grants the necessary permissions to `fastapi_production` and `fastapi_staging` roles:
     - `USAGE` on the `cron` schema
     - `SELECT, INSERT, UPDATE, DELETE` on `cron.job` and `cron.job_run_details` tables
   - These grants are conditional and only applied to the database where `pg_cron` is enabled

3. **Automated 5‑minute schedule (Alembic migration)**
   - Migration `d3c5d7b8f4ee` creates (or replaces) the job named `refresh_user_activity_summary_every_5m` **only if the `cron` schema exists** in the target database:

```sql
SELECT cron.schedule(
    'refresh_user_activity_summary_every_5m',
    '*/5 * * * *',
    'REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary'
);
```

   - If `pg_cron` is not enabled in the database, the migration logs a warning and skips scheduling: `"Skipping pg_cron scheduling because the cron schema was not found."`
   - Rollback removes it with `SELECT cron.unschedule(jobid) FROM cron.job WHERE jobname = 'refresh_user_activity_summary_every_5m';`

4. **Monitor / manage jobs**
   - List jobs: `SELECT * FROM cron.job ORDER BY jobid;`
   - Inspect history: `SELECT * FROM cron.job_run_details ORDER BY end_time DESC LIMIT 20;`
   - Force re‑schedule: re-run the SQL above (or re-apply the migration) after first unscheduling the job by name.

pg_cron runs inside the database process, so no external scheduler is needed. Because the command uses `CONCURRENTLY`, it avoids table-level locks, allowing the `/v1/users/browse` endpoint to continue reading while the refresh runs. Five minutes keeps the view fresh while keeping refresh cost low; adjust the cron string if operational data suggests a different cadence.

## Staging Database Refresh

Since `pg_cron` is only enabled in the production database, the staging database requires manual refreshes. You have several options:

### Option 1: Direct SQL (via SSH tunnel)

If you have a bastion tunnel open to staging:

```bash
psql -h localhost -p 5433 -U fastapi_staging -d tuk_staging \
  -c "REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary"
```

Replace `localhost:5433` with your actual tunnel endpoint.

### Option 2: Admin API Endpoint

If your staging environment has the admin API enabled:

```bash
curl -X POST \
  -H "Authorization: Bearer ${STAGING_ADMIN_TOKEN}" \
  https://api-staging.trigpointing.me/v1/admin/user-stats/refresh
```

### Option 3: As Part of Testing

Add a refresh step to your test setup or deployment scripts:

```python
from api.services.user_stats import refresh_user_activity_summary
from api.db.database import get_db

# In your test fixtures or setup
db = next(get_db())
refresh_user_activity_summary(db, concurrently=True)
```

### When to Refresh in Staging

- After loading test data
- After running migrations
- Before running integration/E2E tests that depend on user statistics
- Periodically during active development (e.g., start of day)

