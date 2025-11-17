# OpenTelemetry Metrics Integration

**Date:** November 17, 2025  
**Objective:** Implement comprehensive metrics collection for the FastAPI application, exporting to Grafana Cloud via OTLP for monitoring and alerting.

## Overview

This document describes the OpenTelemetry metrics implementation in the TrigpointingUK API. Metrics provide quantitative measurements of application behavior, enabling monitoring, alerting, and performance optimization.

## Architecture

```
┌─────────────────────────┐
│  FastAPI Application    │
│                         │
│  ┌──────────────────┐   │
│  │ MetricsCollector │   │
│  └──────────────────┘   │
│           ↓             │
│  ┌──────────────────┐   │
│  │ OpenTelemetry    │   │
│  │ Metrics SDK      │   │
│  └──────────────────┘   │
└─────────────────────────┘
           ↓ OTLP/HTTP
┌─────────────────────────┐
│  Grafana Cloud          │
│  Prometheus             │
│  - Store metrics        │
│  - Query with PromQL    │
│  - Alerting rules       │
└─────────────────────────┘
```

## Metrics Types

### HTTP Metrics (Automatic)

**`http.server.request.count`** (Counter)
- Description: Total number of HTTP requests
- Labels: `http.method`, `http.route`, `http.status_code`
- Use case: Track request volume by endpoint and status

**`http.server.request.duration`** (Histogram)
- Description: Duration of HTTP requests in milliseconds
- Labels: `http.method`, `http.route`
- Use case: Calculate P50/P95/P99 latencies by endpoint

**`http.server.active_requests`** (UpDownCounter)
- Description: Number of in-flight HTTP requests
- Labels: `http.method`, `http.route`
- Use case: Monitor concurrent request load

### Database Metrics

**`db.query.duration`** (Histogram)
- Description: Duration of database queries in milliseconds
- Labels: `db.operation`, `db.system`, `db.table`
- Use case: Identify slow queries and database bottlenecks

**`db.query.count`** (Counter)
- Description: Total number of database queries
- Labels: `db.operation`, `db.system`, `db.table`
- Use case: Track query volume by operation type

**`db.pool.size`** (UpDownCounter)
- Description: Current database connection pool size
- Labels: `db.system`
- Use case: Monitor connection pool usage

**`db.pool.idle`** (UpDownCounter)
- Description: Number of idle connections in pool
- Labels: `db.system`
- Use case: Optimize pool configuration

### Business Metrics

**`trigpointing.trigs.viewed`** (Counter)
- Description: Number of trig detail page views
- Labels: `trig_id`
- Use case: Track popular trigpoints

**`trigpointing.trigs.searched`** (Counter)
- Description: Number of trig search operations
- Labels: `search_type` (general, nearby, advanced)
- Use case: Understand user search patterns

**`trigpointing.photos.uploaded`** (Counter)
- Description: Number of photo uploads
- Labels: `status` (success, failure, rejected), `trig_id`
- Use case: Monitor upload success rate

**`trigpointing.photos.processing_duration`** (Histogram)
- Description: Duration of photo processing in milliseconds
- Use case: Optimize image processing pipeline

**`trigpointing.cache.hits`** (Counter)
- Description: Number of cache hits
- Labels: `cache_type` (auth0_token, api_response, tiles)
- Use case: Calculate cache hit rates

**`trigpointing.cache.misses`** (Counter)
- Description: Number of cache misses
- Labels: `cache_type`
- Use case: Identify caching inefficiencies

## Implementation Details

### Metrics Collector

The `MetricsCollector` class (`api/core/metrics.py`) provides a centralized interface for recording metrics:

```python
from api.core.metrics import get_metrics_collector

# Get the global metrics collector
metrics = get_metrics_collector()

if metrics:
    # Record a trig view
    metrics.record_trig_view(trig_id=12345)
    
    # Record a photo upload
    metrics.record_photo_upload("success", trig_id=12345)
    
    # Track photo processing time
    with metrics.track_photo_processing():
        # Process photo
        pass
```

### Configuration

Add to `.env` or environment variables:

```bash
# Enable OpenTelemetry metrics
OTEL_METRICS_ENABLED=true

# OTLP endpoint (same as traces)
OTEL_EXPORTER_OTLP_ENDPOINT=https://otlp-gateway-prod-eu-west-0.grafana.net/otlp
OTEL_EXPORTER_OTLP_HEADERS=Authorization=Basic <base64-encoded-token>
```

### Terraform Configuration

Metrics are automatically enabled in Terraform for staging and production:

```hcl
# In terraform/modules/ecs-service/main.tf
{
  name  = "OTEL_METRICS_ENABLED"
  value = "true"
}
```

Secrets are read from AWS Secrets Manager:
- `otel_exporter_otlp_endpoint`: Grafana Cloud OTLP endpoint
- `otel_exporter_otlp_headers`: Base64-encoded authentication

## Querying Metrics in Grafana

### PromQL Examples

**Request rate by endpoint:**
```promql
rate(http_server_request_count[5m])
```

**P95 latency by endpoint:**
```promql
histogram_quantile(0.95, 
  rate(http_server_request_duration_bucket[5m])
)
```

**Error rate:**
```promql
rate(http_server_request_count{http_status_code=~"5.."}[5m])
```

**Cache hit rate percentage:**
```promql
100 * (
  rate(trigpointing_cache_hits[5m]) /
  (rate(trigpointing_cache_hits[5m]) + rate(trigpointing_cache_misses[5m]))
)
```

**Photos uploaded per hour:**
```promql
increase(trigpointing_photos_uploaded[1h])
```

## Dashboards

Pre-built dashboards are available in `docs/grafana/dashboards/`:
- `api-overview.json` - RED metrics (Rate, Errors, Duration)
- `database-performance.json` - Database metrics
- `business-metrics.json` - Business KPIs

Import these into Grafana Cloud for instant visibility.

## Alerting

### Recommended Alerts

**High Error Rate:**
```promql
rate(http_server_request_count{http_status_code=~"5.."}[5m]) > 0.01
```
Alert when error rate exceeds 1% of total requests.

**High Latency:**
```promql
histogram_quantile(0.95, rate(http_server_request_duration_bucket[5m])) > 500
```
Alert when P95 latency exceeds 500ms.

**Database Slow Queries:**
```promql
histogram_quantile(0.95, rate(db_query_duration_bucket[5m])) > 100
```
Alert when P95 query duration exceeds 100ms.

## Performance Impact

OpenTelemetry metrics have minimal overhead:
- **CPU:** <1% additional CPU usage
- **Memory:** ~5-10MB per container
- **Network:** ~50-200KB/minute to Grafana Cloud (exported every 60 seconds)

## Free Tier Limits

**Grafana Cloud Free Tier:**
- **10,000 active series** - More than sufficient for our ~300-500 series
- **14-day retention** - Adequate for debugging and monitoring
- **No credit card required**

**Estimated usage:**
- HTTP metrics: ~100 series (endpoints × methods × status codes)
- Database metrics: ~50 series
- Business metrics: ~100-150 series
- **Total:** ~300-500 active series (well under 10k limit)

## Troubleshooting

### Metrics Not Appearing in Grafana

1. **Check metrics are enabled:**
   ```bash
   echo $OTEL_METRICS_ENABLED
   # Should output: true
   ```

2. **Verify export logs:**
   ```bash
   # Check CloudWatch Logs for:
   "OpenTelemetry metrics initialized successfully"
   ```

3. **Test OTLP endpoint:**
   ```bash
   curl -s -o /dev/null -w "%{http_code}\n" \
     -H "Authorization: Basic <base64-token>" \
     -H "Content-Type: application/json" \
     -d '{}' https://otlp-gateway-prod-eu-west-0.grafana.net/otlp/v1/metrics
   ```

### High Cardinality Issues

If you exceed the 10k series limit:

1. **Remove high-cardinality labels:**
   - Don't use `trig_id` in labels (use filters in PromQL instead)
   - Aggregate by broader categories

2. **Enable sampling:**
   - Sample less critical metrics
   - Use aggregation rules in Grafana

## Best Practices

1. **Keep cardinality low:** Avoid user IDs, timestamps, or unique identifiers as labels
2. **Use histograms for durations:** Enables percentile calculations
3. **Counter for counts:** Use counters for cumulative values (requests, errors)
4. **UpDownCounter for gauges:** Use for values that go up and down (active requests)
5. **Meaningful labels:** Use semantic labels (`http.method`, `http.route`, not `path`)

## References

- [OpenTelemetry Metrics Specification](https://opentelemetry.io/docs/specs/otel/metrics/)
- [OpenTelemetry Python Metrics API](https://opentelemetry-python.readthedocs.io/en/latest/api/metrics.html)
- [Prometheus Naming Best Practices](https://prometheus.io/docs/practices/naming/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)

