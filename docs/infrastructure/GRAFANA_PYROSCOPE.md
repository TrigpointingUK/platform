# Pyroscope Continuous Profiling

**Date:** November 17, 2025  
**Objective:** Implement continuous CPU profiling with Pyroscope to identify performance bottlenecks and optimize application performance.

## Overview

Pyroscope provides always-on continuous profiling with <1% overhead, enabling you to:
- Identify CPU-intensive code paths
- Optimize hot spots in your application
- Correlate performance issues with specific requests
- Compare performance across deployments

This is far more powerful than the existing query-parameter-based pyinstrument profiling, which only profiles individual requests manually.

## Architecture

```
┌─────────────────────────┐
│  FastAPI Application    │
│                         │
│  ┌──────────────────┐   │
│  │ Pyroscope SDK    │   │
│  │ (CPU Profiler)   │   │
│  └──────────────────┘   │
│           ↓             │
│    (Every 10s)          │
└─────────────────────────┘
           ↓ Pyroscope Protocol
┌─────────────────────────┐
│  Grafana Cloud          │
│  Pyroscope              │
│  - Store profiles       │
│  - Flame graphs         │
│  - Diff analysis        │
└─────────────────────────┘
```

## How It Works

Pyroscope uses statistical sampling profiling:

1. **Sampling:** Every 100 Hz (100 times per second), it samples what code is running
2. **Aggregation:** Samples are aggregated locally every 10 seconds
3. **Upload:** Aggregated profiles are uploaded to Grafana Cloud
4. **Analysis:** View flame graphs for any time period in Grafana

**Key Benefits:**
- **Always on:** No need to manually enable profiling
- **Low overhead:** <1% CPU impact (much lower than pyinstrument's 10-30%)
- **Historical analysis:** Profile any past time period
- **Comparison:** Compare profiles before/after deployments

## Configuration

### Environment Variables

Add to `.env` or environment variables:

```bash
# Enable Pyroscope
PYROSCOPE_ENABLED=true

# Pyroscope server address (Grafana Cloud)
PYROSCOPE_SERVER_ADDRESS=https://profiles-prod-001.grafana.net

# Authentication token
PYROSCOPE_AUTH_TOKEN=<your-pyroscope-token>

# Optional: Custom application name (defaults to service name + environment)
PYROSCOPE_APPLICATION_NAME=trigpointing-api-production
```

### Getting Pyroscope Credentials

1. Log into Grafana Cloud
2. Navigate to **Profiles** (Pyroscope)
3. Click **Send data** or **Configure**
4. Copy the server address and create an API token
5. Add to AWS Secrets Manager (see below)

### AWS Secrets Manager

Add Pyroscope credentials to your secrets:

**For Staging:**
```bash
aws secretsmanager update-secret \
  --secret-id fastapi-staging-app-secrets \
  --secret-string '{
    "auth0_custom_domain": "...",
    ...existing keys...,
    "pyroscope_server_address": "https://profiles-prod-001.grafana.net",
    "pyroscope_auth_token": "pyr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }'
```

**For Production:**
```bash
aws secretsmanager update-secret \
  --secret-id fastapi-production-app-secrets \
  --secret-string '{
    "auth0_custom_domain": "...",
    ...existing keys...,
    "pyroscope_server_address": "https://profiles-prod-001.grafana.net",
    "pyroscope_auth_token": "pyr_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
  }'
```

### Terraform Configuration

Pyroscope is automatically enabled in Terraform for staging and production:

```hcl
# In terraform/modules/ecs-service/main.tf
{
  name  = "PYROSCOPE_ENABLED"
  value = "true"
}
```

Secrets are read from AWS Secrets Manager:
- `pyroscope_server_address`: Grafana Cloud Pyroscope endpoint
- `pyroscope_auth_token`: Pyroscope authentication token

## Using Pyroscope in Grafana

### Viewing Profiles

1. Log into Grafana Cloud
2. Navigate to **Explore** → **Profiles** (Pyroscope)
3. Select your application: `trigpointing-api-production` or `trigpointing-api-staging`
4. Choose a time range
5. View the flame graph

### Flame Graph Interpretation

**Flame Graph Basics:**
- **Width:** Time spent (wider = more CPU time)
- **Height:** Call stack depth
- **Color:** Different functions (no semantic meaning)
- **Hover:** See function name and percentage of CPU time

**What to look for:**
- Wide "plateaus" = hot spots (optimize these first)
- Deep stacks = potential recursion or inefficient algorithms
- External library calls = opportunities to cache or parallelize

### Filtering and Comparison

**Filter by tags:**
```
environment=production
service=trigpointing-api-production
```

**Compare profiles:**
1. Select a baseline time range (e.g., last week)
2. Click **Compare** 
3. Select a comparison time range (e.g., today)
4. View the diff (green = less time, red = more time)

Use this to:
- Compare before/after a deployment
- Identify regressions
- Validate optimizations

### Common Analysis Patterns

**Find slowest endpoints:**
1. View profile during high load
2. Look for wide plateaus in application code
3. Trace back to endpoint handler functions

**Database query optimization:**
1. Look for time spent in SQLAlchemy
2. Check for N+1 query patterns (repeated small queries)
3. Optimize with joins or caching

**External API calls:**
1. Look for time spent in `requests` library
2. Consider async/parallel calls or caching

## Profiling Configuration

The Pyroscope configuration in `api/core/telemetry.py`:

```python
pyroscope.configure(
    application_name=app_name,
    server_address=pyroscope_server_address,
    auth_token=pyroscope_auth_token,
    tags={
        "environment": environment,
        "service": app_name,
    },
    detect_subprocesses=False,  # Disable for FastAPI/uvicorn
    oncpu=True,                  # CPU profiling (default)
    gil_only=True,               # Only Python code (not C extensions)
)
```

**Configuration options:**
- `oncpu=True`: Profile CPU time (recommended)
- `gil_only=True`: Only profile Python code (faster, less noise from C extensions)
- `detect_subprocesses=False`: Don't profile worker processes (not needed for uvicorn)

## Performance Impact

Pyroscope has minimal overhead:
- **CPU:** <1% additional CPU usage
- **Memory:** ~5-10MB per container
- **Network:** ~50-500KB/minute to Grafana Cloud

This is **much lower** than pyinstrument (10-30% overhead), making it suitable for always-on profiling in production.

## Free Tier Limits

**Grafana Cloud Free Tier:**
- **15GB profiles/month** - Sufficient for continuous profiling
- **14-day retention** - Adequate for performance debugging
- **No credit card required**

**Estimated usage:**
- ~3-5GB/month at 100Hz sampling rate (default)
- Well within free tier limits

## Comparison with Pyinstrument

| Feature | Pyroscope | Pyinstrument (existing) |
|---------|-----------|------------------------|
| **Overhead** | <1% | 10-30% |
| **Usage** | Always-on | Manual (query param) |
| **Scope** | All requests | Single request |
| **Historical** | Yes (14 days) | No |
| **Comparison** | Yes | No |
| **Format** | Flame graph | HTML/Speedscope |
| **Production** | ✅ Suitable | ❌ Too expensive |

**Recommendation:** Use Pyroscope for always-on production profiling, keep pyinstrument for deep-dive debugging in staging.

## Troubleshooting

### Profiles Not Appearing in Grafana

1. **Check Pyroscope is enabled:**
   ```bash
   echo $PYROSCOPE_ENABLED
   # Should output: true
   ```

2. **Verify initialization logs:**
   ```bash
   # Check CloudWatch Logs for:
   "Pyroscope initialized successfully"
   ```

3. **Test connectivity:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" \
     -H "Authorization: Bearer <pyroscope-token>" \
     https://profiles-prod-001.grafana.net/ingest
   ```

### High Data Volume

If approaching 15GB/month limit:

1. **Reduce sampling rate:**
   ```python
   pyroscope.configure(
       ...,
       sample_rate=50,  # Reduce from 100Hz to 50Hz
   )
   ```

2. **Disable in non-production environments** (keep staging/production only)

3. **Upgrade to Grafana Cloud Pro** (£49/month for 50GB)

## Use Cases

### 1. Optimize Slow Endpoints

**Scenario:** `/v1/trigs?limit=100` is slow

**Steps:**
1. View profile during high load period
2. Search for `list_trigs` function
3. Identify hot spots (e.g., serialization, database queries)
4. Optimize (e.g., select only needed fields, add caching)
5. Deploy and compare profiles

### 2. Find CPU Regressions

**Scenario:** After deployment, CPU usage increased

**Steps:**
1. Open Pyroscope in Grafana
2. Compare: Last week vs. This week
3. Look for red areas (more CPU time)
4. Identify the regression (new code path)
5. Optimize or rollback

### 3. Optimize Photo Processing

**Scenario:** Photo uploads are slow

**Steps:**
1. Profile during photo upload
2. Look for time in `ImageProcessor` class
3. Identify bottlenecks (e.g., image resize, format conversion)
4. Optimize (e.g., use faster libraries, reduce quality)
5. Validate with before/after comparison

## Best Practices

1. **Always enable in production:** The overhead is negligible
2. **Use tags for filtering:** Add environment and version tags
3. **Compare before/after:** Always compare profiles when optimizing
4. **Focus on wide plateaus:** These are your biggest wins
5. **Don't optimize prematurely:** Profile first, then optimize

## Integration with Traces

Pyroscope integrates with OpenTelemetry traces:

1. Find a slow trace in Tempo
2. Note the timestamp
3. Open Pyroscope at that exact timestamp
4. See which code was using CPU during that trace

This correlation helps identify performance issues that span multiple services.

## References

- [Pyroscope Documentation](https://pyroscope.io/docs/)
- [Grafana Cloud Pyroscope](https://grafana.com/docs/grafana-cloud/monitor-applications/profiles/)
- [Python Profiling Guide](https://docs.python.org/3/library/profile.html)
- [Flame Graph Interpretation](https://www.brendangregg.com/flamegraphs.html)

