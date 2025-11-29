# Grafana Dashboards

This directory contains Grafana dashboard JSON files for visualizing observability data from the TrigpointingUK API.

## Dashboards

### 1. API Overview (RED Metrics)

**File:** `api-overview.json`

**Purpose:** Monitor API health and performance using RED metrics (Rate, Errors, Duration)

**Panels:**
- Request rate per endpoint (requests/second)
- P50, P95, P99 latency by endpoint
- Error rate by status code
- Active requests gauge
- Request volume heatmap

**Data Sources:** 
- Prometheus (metrics via OTLP)
- Tempo (traces)

### 2. Database Performance

**File:** `database-performance.json`

**Purpose:** Monitor database query performance and connection pool health

**Panels:**
- Query duration P95 by operation type
- Query count by operation
- Connection pool utilization
- Slow queries (>100ms)
- Query rate over time

**Data Sources:** 
- Prometheus (metrics via OTLP)

### 3. Business Metrics

**File:** `business-metrics.json`

**Purpose:** Track business-specific KPIs and user engagement

**Panels:**
- Trigs viewed per hour
- Photos uploaded per hour (success vs failure)
- Cache hit rate percentage
- Search operations by type (nearby, general)
- User activity trends

**Data Sources:** 
- Prometheus (metrics via OTLP)

### 4. Trace Analysis

**File:** `trace-analysis.json`

**Purpose:** Analyze distributed traces and identify performance bottlenecks

**Panels:**
- Latency heatmap by endpoint
- Slowest traces (P99)
- Error traces
- Database span analysis
- Service dependency graph

**Data Sources:** 
- Tempo (traces)

## Importing Dashboards

### Via Grafana UI

1. Log into Grafana Cloud
2. Navigate to **Dashboards** → **New** → **Import**
3. Click **Upload JSON file** and select the desired dashboard file
4. Select your data sources:
   - **Prometheus**: Select your Grafana Cloud Prometheus instance
   - **Tempo**: Select your Grafana Cloud Tempo instance
5. Click **Import**

### Via API

```bash
# Export GRAFANA_API_TOKEN with your Grafana Cloud API token
# Export GRAFANA_URL with your Grafana Cloud URL

curl -X POST "${GRAFANA_URL}/api/dashboards/db" \
  -H "Authorization: Bearer ${GRAFANA_API_TOKEN}" \
  -H "Content-Type: application/json" \
  -d @api-overview.json
```

## Customizing Dashboards

All dashboards are provided as starting points. You can customize:

- Time ranges and refresh intervals
- Alert thresholds
- Panel layouts and visualizations
- Filters and variables

## Dashboard Variables

Most dashboards include these template variables:

- `environment`: Filter by environment (staging, production)
- `endpoint`: Filter by API endpoint
- `timeRange`: Quick time range selector

## Alerting

To set up alerts based on these dashboards:

1. Open a dashboard
2. Click on a panel
3. Select **Edit**
4. Go to the **Alert** tab
5. Configure alert rules (e.g., P95 latency > 500ms)
6. Configure notification channels

## Maintenance

These dashboard JSON files should be:
- Version controlled in Git
- Updated when adding new metrics
- Exported after making significant changes in Grafana UI
- Tested after import to ensure all panels render correctly

## Support

For issues with dashboards:
1. Check data source connections
2. Verify metrics are being exported (check OTEL/Pyroscope logs)
3. Ensure Grafana Cloud free tier limits aren't exceeded
4. Check TraceQL/PromQL query syntax in Grafana Explore

## References

- [Grafana Dashboard Documentation](https://grafana.com/docs/grafana/latest/dashboards/)
- [PromQL Query Language](https://prometheus.io/docs/prometheus/latest/querying/basics/)
- [TraceQL Query Language](https://grafana.com/docs/tempo/latest/traceql/)

