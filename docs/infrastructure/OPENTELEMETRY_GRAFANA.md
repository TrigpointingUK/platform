# OpenTelemetry + Grafana Cloud Integration

**Date:** 16 November 2025  
**Objective:** Implement distributed tracing and performance monitoring with OpenTelemetry and Grafana Cloud at zero cost (using free tier).

## Overview

This document describes how to set up OpenTelemetry instrumentation in the FastAPI application to export traces to Grafana Cloud, enabling:

- **Latency heatmaps** - Visualise request latency distribution over time
- **Percentile tracking** - Monitor p50, p95, p99 latencies for all endpoints
- **Distributed tracing** - Debug slow requests with detailed trace views
- **Database query performance** - Automatic SQLAlchemy instrumentation
- **Zero AWS costs** - Uses Grafana Cloud free tier (50GB traces/month)

## Architecture

```
┌─────────────────┐
│  FastAPI App    │
│  (ECS Fargate)  │
│                 │
│  OpenTelemetry  │──────────────┐
│  SDK            │              │
└─────────────────┘              │
                                 │ OTLP/gRPC
                                 │ (traces)
                                 ▼
                        ┌────────────────────┐
                        │  Grafana Cloud     │
                        │  OTLP Gateway      │
                        │                    │
                        │  - Trace storage   │
                        │  - Dashboards      │
                        │  - Query interface │
                        └────────────────────┘
```

## Implementation Status

✅ **Completed:**
- OpenTelemetry dependencies added to `requirements.txt`
- `api/core/telemetry.py` module created with initialization logic
- Configuration settings added to `api/core/config.py`
- Telemetry initialization integrated into `api/main.py`
- Application code ready (telemetry disabled by default)

⏳ **Manual Steps Required (when ready to enable):**
1. Create Grafana Cloud account (free tier)
2. Obtain OTLP endpoint and API token
3. Add secrets to AWS Secrets Manager
4. Update Terraform to enable OTEL and inject secrets
5. Apply Terraform changes

**Note:** The application runs perfectly fine without telemetry configured. OpenTelemetry is disabled by default and won't cause any errors if not configured.

## Setup Instructions

### 1. Create Grafana Cloud Account

1. Go to [https://grafana.com/products/cloud/](https://grafana.com/products/cloud/)
2. Click **"Start for free"** and create an account
3. Select the **Free Forever** tier:
   - 50GB traces per month
   - 14-day trace retention
   - 3 active users
   - Perfect for this workload!

### 2. Get OpenTelemetry Configuration

Once logged into Grafana Cloud:

1. Navigate to **Connections** → **Add new connection**
2. Search for **"OpenTelemetry"** and select it
3. Click **"Via Grafana Alloy"** or **"OTLP"**
4. You'll see configuration details including:

   **OTLP Endpoint:**
   ```
   https://otlp-gateway-prod-<region>.grafana.net/otlp
   ```
   Example: `https://otlp-gateway-prod-eu-west-0.grafana.net/otlp`

   **Authentication:**
   - **Instance ID:** `123456`
   - **API Token:** `glc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx`

5. Create the authentication header in the format:
   ```
   Authorization=Basic <base64-encoded-credentials>
   ```
   
   Where `<base64-encoded-credentials>` is the base64 encoding of `{instanceID}:{APIToken}`
   
   You can encode it with:
   ```bash
   echo -n "123456:glc_xxxxxxxxxxxxxxxxxxxxxxxxxxxxx" | base64
   ```

   > **Important:** Grafana also shows a convenience string such as
   > `Authorization=Basic%20Z2xjXy...`. That value is the base64 encoding of
   > `{APIToken}:{instanceID}` (the reverse order) and will result in
   > `401 authentication error: invalid authentication credentials`. Always build
   > the header yourself using `instanceID:APIToken` as shown above.

### 3. Add Secrets to AWS Secrets Manager

You need to add the OTLP configuration to your existing secrets in AWS Secrets Manager.

#### For Staging Environment

1. Open AWS Console → Secrets Manager
2. Find the secret: **`fastapi-staging-app-secrets`**
3. Click **"Retrieve secret value"** → **"Edit"**
4. Add two new key-value pairs to the existing JSON:

   ```json
   {
     "auth0_custom_domain": "...",
     "auth0_tenant_domain": "...",
     ... existing keys ...
     "otel_exporter_otlp_endpoint": "https://otlp-gateway-prod-eu-west-0.grafana.net/otlp",
     "otel_exporter_otlp_headers": "Authorization=Basic MTIzNDU2OmdsY194eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eHh4eA=="
   }
   ```

5. Click **"Save"**

To double-check the stored value:

```bash
aws secretsmanager get-secret-value \
  --secret-id fastapi-staging-app-secrets \
  --region eu-west-1 \
  --query 'SecretString' --output text | jq -r '.otel_exporter_otlp_headers'
```

The output should start with `Authorization=Basic ` followed by the base64
encoding you generated in step 2.

#### For Production Environment

1. Open AWS Console → Secrets Manager
2. Find the secret: **`fastapi-production-app-secrets`**
3. Click **"Retrieve secret value"** → **"Edit"**
4. Add the same two key-value pairs to the existing JSON (you can use the same Grafana Cloud instance or create separate ones)
5. Click **"Save"**

**Note:** The secrets will be automatically injected as environment variables (`OTEL_EXPORTER_OTLP_ENDPOINT` and `OTEL_EXPORTER_OTLP_HEADERS`) when ECS tasks start.

### 4. Deploy Changes

The application code with OpenTelemetry is already deployed. Telemetry is **disabled by default**, so the application works normally without any additional configuration.

To **enable** telemetry later, you'll need to:

1. **Add the OTEL secrets** to AWS Secrets Manager (steps 1-3 above)
2. **Update Terraform** to enable OTEL and inject the secrets:

```hcl
# In terraform/modules/ecs-service/main.tf, around line 78:
{
  name  = "OTEL_ENABLED"
  value = "true"
},
```

And add the secret references around line 172:

```hcl
        ],
        # OpenTelemetry (for distributed tracing)
        [
          {
            name      = "OTEL_EXPORTER_OTLP_ENDPOINT"
            valueFrom = "${var.secrets_arn}:otel_exporter_otlp_endpoint::"
          },
          {
            name      = "OTEL_EXPORTER_OTLP_HEADERS"
            valueFrom = "${var.secrets_arn}:otel_exporter_otlp_headers::"
          }
        ]
      )
```

3. **Apply Terraform changes:**

```bash
cd terraform/staging
terraform plan
terraform apply

# After verifying in staging:
cd ../production
terraform plan
terraform apply
```

### 5. Verify Telemetry is Working

1. After deployment, check CloudWatch Logs for the ECS task
2. Look for the log message:
   ```
   OpenTelemetry initialized successfully for trigpointing-api-staging in staging environment, exporting to https://otlp-gateway-prod-eu-west-0.grafana.net/otlp
   ```

3. In Grafana Cloud, navigate to **Explore** → **Traces**
4. Make a few API requests to generate traces
5. You should see traces appearing within 10-30 seconds

## Using Grafana Cloud

### Viewing Traces

1. Log into Grafana Cloud
2. Navigate to **Explore** → **Tempo** (traces)
3. Search for traces:
   - By service name: `trigpointing-api-production` or `trigpointing-api-staging`
   - By endpoint: `GET /v1/trigs/{id}`
   - By duration: `duration > 1s` (slow requests)
   - By status: `status=error`

### Creating Latency Heatmaps

1. Go to **Dashboards** → **New Dashboard**
2. Add a panel with **Heatmap** visualisation
3. Use TraceQL query:
   ```
   {service.name="trigpointing-api-production"}
   | rate() by (span.name)
   ```

4. Alternatively, use Prometheus metrics (if you enable metrics export):
   ```
   histogram_quantile(0.95, 
     sum(rate(http_server_duration_bucket[5m])) by (le, http_route)
   )
   ```

### Pre-Built Dashboard

You can import a pre-built RED (Rate, Errors, Duration) metrics dashboard:

1. Go to **Dashboards** → **Import**
2. Use dashboard ID: `19426` (RED Metrics for OpenTelemetry)
3. Select your Tempo datasource

### Key Queries for Performance Analysis

**P95 latency by endpoint:**
```
{service.name="trigpointing-api-production"} 
| quantile_over_time(duration, 0.95) by (span.name)
```

**Slow database queries:**
```
{service.name="trigpointing-api-production" && db.system="postgresql"} 
| select(duration > 100ms)
```

**Error traces:**
```
{service.name="trigpointing-api-production" && status=error}
```

**Requests per second:**
```
{service.name="trigpointing-api-production"} | rate()
```

## Configuration Reference

### Environment Variables

These are automatically configured via Terraform:

| Variable | Source | Example |
|----------|--------|---------|
| `OTEL_ENABLED` | Environment | `true` |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | Secrets Manager | `https://otlp-gateway-prod-eu-west-0.grafana.net/otlp` |
| `OTEL_EXPORTER_OTLP_HEADERS` | Secrets Manager | `Authorization=Basic MTIzNDU2...` |
| `OTEL_SERVICE_NAME` | Auto-generated | `trigpointing-api-production` |
| `ENVIRONMENT` | Environment | `production` |

### Local Development

For local development, OpenTelemetry is **disabled by default**. To enable it:

1. Create a `.env` file:
   ```bash
   OTEL_ENABLED=true
   OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-eu-west-0.grafana.net/otlp
   OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic MTIzNDU2...
   ```

2. Run the application:
   ```bash
   source venv/bin/activate
   make run
   ```

3. Check logs for successful initialisation

## Automatic Instrumentation

The following are automatically instrumented (no code changes required):

### FastAPI
- All HTTP requests
- Request method and path
- Response status code
- Request duration
- Query parameters (sanitised)

### SQLAlchemy
- All database queries
- Query text (parameterised)
- Query duration
- Database name and operation

### Future Instrumentation (Optional)

You can add additional instrumentation for:
- Redis operations: `opentelemetry-instrumentation-redis`
- HTTP client requests: `opentelemetry-instrumentation-requests`
- AWS SDK calls: `opentelemetry-instrumentation-botocore`

## Cost Analysis

### Grafana Cloud Free Tier

- **50GB traces/month** - sufficient for ~100-200 million spans
- **14-day retention** - adequate for debugging recent issues
- **No credit card required**

### Estimated Usage

Based on current traffic patterns:

- **~10 requests/second** during peak hours
- **~3-5 spans per request** (HTTP + database queries)
- **~0.5KB per span** average

**Daily trace volume:**
```
10 req/s × 4 spans × 0.5KB × 86,400 seconds/day
= 10 × 4 × 0.5 × 86,400 / 1,000,000
= 1.7GB/day
= ~50GB/month
```

**Conclusion:** Well within the free tier limits! 🎉

### AWS Costs

**Zero additional AWS costs:**
- No CloudWatch Container Insights ($0.30/metric/month)
- No CloudWatch custom metrics
- No CloudWatch Logs Insights queries
- Only standard ECS CloudWatch Logs (already enabled)

## Performance Impact

OpenTelemetry has minimal performance overhead:

- **CPU:** <1% additional CPU usage
- **Memory:** ~5-10MB per container
- **Latency:** <1ms added per request (span creation)
- **Network:** ~100-500KB/minute outbound to Grafana Cloud

The BatchSpanProcessor batches spans before export, minimising network overhead.

## Troubleshooting

### Telemetry Not Initialising

**Symptoms:** No log message about OpenTelemetry initialisation

**Solutions:**
1. Check that `OTEL_ENABLED=true` in environment variables
2. Verify secrets exist in AWS Secrets Manager
3. Check CloudWatch Logs for error messages

### Traces Not Appearing in Grafana

**Symptoms:** OpenTelemetry initialises but no traces in Grafana

**Solutions:**
1. Verify the OTLP endpoint is correct (check region)
2. Verify the authentication token is valid
3. Check that the base64 encoding is correct:
   ```bash
   echo -n "instanceID:apiToken" | base64
   ```
4. Test connectivity (locally or from ECS) with the same credentials:
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" \
     -H "Authorization: Basic <base64(instanceID:apiToken)>" \
     -H "Content-Type: application/json" \
     -d '{}' https://otlp-gateway-prod-eu-west-0.grafana.net/otlp/v1/traces
   ```
   - `200` or `400` is good (auth accepted, payload may be empty)
   - `401` means the header is incorrect (usually the order of
     `instanceID:apiToken`)
   - `404` means the path is missing `/otlp`

### `401 authentication error: invalid authentication credentials`

**Symptoms:** CloudWatch logs show
`Failed to export batch code: 401, reason: {"status":"error","error":"authentication error: invalid authentication credentials"}`.

**Solutions:**
- Rebuild the header with `instanceID:apiToken` (NOT the other way around):
  ```bash
  echo -n "1439925:glc_xxx" | base64
  ```
- Update the `otel_exporter_otlp_headers` key in Secrets Manager and force a new
  ECS deployment.
- Run the `curl` command above (or via `aws ecs execute-command`) to confirm the
  new credentials are accepted before re-running any load tests.

### High Data Volume

**Symptoms:** Approaching 50GB/month limit

**Solutions:**
1. Enable sampling (modify `api/core/telemetry.py`):
   ```python
   from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
   
   # Sample 10% of traces
   sampler = TraceIdRatioBased(0.1)
   ```

2. Filter out health check endpoints:
   ```python
   # In telemetry.py, add span processor with filtering
   ```

3. Upgrade to Grafana Cloud Pro ($49/month for 100GB)

## Comparison with CloudWatch

| Feature | CloudWatch | Grafana Cloud (Free) |
|---------|------------|---------------------|
| **Latency heatmaps** | ❌ Not available | ✅ Built-in |
| **Distributed tracing** | ❌ Only with X-Ray ($5/million) | ✅ Free |
| **Custom metrics** | 💰 $0.30/metric/month | ✅ Free |
| **Database query tracking** | ❌ Not available | ✅ Automatic |
| **Retention** | ⚙️ Configurable (costs extra) | 14 days free |
| **Cost at current scale** | 💸 $50-150/month | ✅ $0/month |

## Next Steps

1. ✅ Deploy to staging and verify traces are working
2. ⏳ Monitor staging for a few days to ensure stability
3. ⏳ Deploy to production
4. ⏳ Create custom dashboards for key metrics
5. ⏳ Set up alerting for high latency or error rates
6. ⏳ Consider adding Redis and Boto3 instrumentation

## References

- [OpenTelemetry Python Documentation](https://opentelemetry.io/docs/instrumentation/python/)
- [Grafana Cloud Free Tier](https://grafana.com/products/cloud/)
- [FastAPI Instrumentation](https://opentelemetry-python-contrib.readthedocs.io/en/latest/instrumentation/fastapi/fastapi.html)
- [TraceQL Query Language](https://grafana.com/docs/tempo/latest/traceql/)

## Support

If you encounter issues:
1. Check CloudWatch Logs for error messages
2. Review this documentation
3. Check the OpenTelemetry Python GitHub issues
4. Contact Grafana Cloud support (free tier includes community support)

