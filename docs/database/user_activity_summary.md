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

1. **Enable pg_cron (RDS specific)**
   - Attach `pg_cron` to the RDS parameter group: `shared_preload_libraries = 'pg_cron'`
   - Reboot the instance to load the extension
   - Connect as a superuser and run `CREATE EXTENSION IF NOT EXISTS pg_cron;`

2. **Grant permissions**
   - `GRANT USAGE ON SCHEMA cron TO <app_role>;`
   - `GRANT ALL ON TABLE cron.job TO <app_role>;` (or run scheduling commands as `rds_superuser`)

3. **Automated 5‑minute schedule**
   - Migration `d3c5d7b8f4ee` creates (or replaces) the job named `refresh_user_activity_summary_every_5m`:

```sql
SELECT cron.schedule(
    'refresh_user_activity_summary_every_5m',
    '*/5 * * * *',
    'REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary'
);
```

   - Rollback removes it with `SELECT cron.unschedule(jobid) FROM cron.job WHERE jobname = 'refresh_user_activity_summary_every_5m';`

4. **Monitor / manage jobs**
   - List jobs: `SELECT * FROM cron.job ORDER BY jobid;`
   - Inspect history: `SELECT * FROM cron.job_run_details ORDER BY end_time DESC LIMIT 20;`
   - Force re‑schedule: re-run the SQL above (or re-apply the migration) after first unscheduling the job by name.

pg_cron runs inside the database process, so no external scheduler is needed. Because the command uses `CONCURRENTLY`, it avoids table-level locks, allowing the `/v1/users/browse` endpoint to continue reading while the refresh runs. Five minutes keeps the view fresh while keeping refresh cost low; adjust the cron string if operational data suggests a different cadence.

