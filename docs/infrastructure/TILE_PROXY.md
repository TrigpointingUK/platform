# OS Tile Proxy Implementation

## Overview

Secure tile proxy system for OS Maps API with comprehensive cost controls, EFS caching, and multi-dimensional rate limiting.

## Architecture

```
Browser → Cloudflare CDN → ALB → FastAPI → EFS Cache
                                        ↓
                                   OS Maps API
                                        ↓
                                   Redis (Usage Tracking)
```

## Components

### 1. EFS Tile Cache

**Location:** `/mnt/tiles` (mounted in FastAPI containers)

**Structure:**
```
/mnt/tiles/
  ├── Outdoor_3857/
  │   ├── 10/
  │   │   ├── 100/
  │   │   │   ├── 200.png
  │   │   │   └── 201.png
  │   │   └── 101/
  │   └── 11/
  ├── Light_3857/
  └── Leisure_27700/
```

**Benefits:**
- Permanent cache (survives container restarts)
- Shared across all FastAPI containers
- Cost savings (cached tile = free)
- Infrequent Access tier after 30 days

### 2. Usage Tracking (Redis)

**Key Structure:**
```
fastapi/{environment}/tiles/usage/weekly/{YYYY-WW}/total/premium → count
fastapi/{environment}/tiles/usage/weekly/{YYYY-WW}/total/free → count
fastapi/{environment}/tiles/usage/weekly/{YYYY-WW}/ip/{ip}/premium → count
fastapi/{environment}/tiles/usage/weekly/{YYYY-WW}/ip/{ip}/free → count
fastapi/{environment}/tiles/usage/weekly/{YYYY-WW}/user/{user_id}/premium → count
fastapi/{environment}/tiles/usage/weekly/{YYYY-WW}/user/{user_id}/free → count
fastapi/{environment}/tiles/usage/weekly/{YYYY-WW}/anon_total/premium → count
fastapi/{environment}/tiles/usage/weekly/{YYYY-WW}/anon_total/free → count
```

**TTL:** 8 days (automatic cleanup)

### 3. Rate Limiting

**Dimensions Tracked:**
1. **Global Total** - Overall usage for all users
2. **Per-IP** - Individual IP address usage
3. **Per-User** - Individual authenticated user usage
4. **Anonymous Total** - Total for all anonymous users combined

**Limits (Production):**
```python
# Global: 15 tx/sec * 1,904,762 sec/week / 4 req/tx = 7,000,000
global_premium: 7,000,000
global_free: 7,000,000

# Per-user: 1% of global
registered_premium: 70,000
registered_free: 70,000

# Per-IP (anonymous): 1% of global
anon_ip_premium: 70,000
anon_ip_free: 70,000

# Total anonymous: 10% of global
anon_total_premium: 700,000
anon_total_free: 700,000
```

**Limits (Staging):**
All limits set to 100 or lower for testing.

### 4. Premium Tile Classification

**Rules:**
```python
# Cached tiles: ALWAYS FREE (no OS API call)
if from_cache:
    return False

# High-zoom outdoor/light: PREMIUM
if layer in ['Outdoor_3857', 'Light_3857'] and z > 16:
    return True

# Any leisure zoom > 5: PREMIUM
if layer == 'Leisure_27700' and z > 5:
    return True

# Everything else: FREE
return False
```

## API Endpoints

### GET /v1/tiles/os/{layer}/{z}/{x}/{y}.png

Proxy OS Maps tiles with caching and rate limiting.

**Parameters:**
- `layer`: Outdoor_3857, Light_3857, or Leisure_27700
- `z`: Zoom level (0-20)
- `x`: Tile X coordinate
- `y`: Tile Y coordinate

**Headers:**
- `X-Tile-Source`: "cache" or "os-api"
- `X-Tile-Type`: "premium" or "free"
- `Cache-Control`: "public, max-age=31536000" (1 year)

**Responses:**
- `200`: PNG tile data
- `400`: Invalid layer
- `429`: Rate limit exceeded
- `502`: OS API error

### GET /v1/tiles/os/usage

View tile usage statistics (authenticated users only).

**Response:**
```json
{
  "week": "2025-45",
  "global": {
    "premium": {"used": 12345, "limit": 7000000},
    "free": {"used": 54321, "limit": 7000000}
  },
  "user": {
    "premium": {"used": 123, "limit": 70000},
    "free": {"used": 456, "limit": 70000}
  },
  "ip": {
    "premium": {"used": 100, "limit": 70000},
    "free": {"used": 200, "limit": 70000}
  }
}
```

## Deployment

### 1. Terraform Apply

Apply EFS and ECS changes:

```bash
cd terraform/common
terraform apply  # Creates EFS filesystem

cd ../staging
terraform apply  # Mounts EFS to FastAPI containers

cd ../production
terraform apply  # Mounts EFS to FastAPI containers
```

### 2. Add OS API Key to Secrets Manager

**Staging:**
```bash
aws secretsmanager update-secret \
  --secret-id fastapi-staging-app-secrets \
  --secret-string '{"OS_API_KEY":"your-os-api-key-here",...}'
```

**Production:**
```bash
aws secretsmanager update-secret \
  --secret-id fastapi-production-app-secrets \
  --secret-string '{"OS_API_KEY":"your-os-api-key-here",...}'
```

### 3. Deploy FastAPI

The application will automatically:
- Mount EFS at `/mnt/tiles`
- Load OS_API_KEY from Secrets Manager
- Start serving proxied tiles

### 4. Update Frontend

Frontend already configured to use proxy URLs:
```typescript
osDigital: {
  urlTemplate: `${apiBase}/v1/tiles/os/Outdoor_3857/{z}/{x}/{y}.png`,
}
```

## Cost Analysis

### Cloudflare Caching Impact

**First Request (cache miss):**
1. Browser → Cloudflare → ALB → FastAPI
2. FastAPI checks EFS (miss)
3. FastAPI proxies to OS API (costs money)
4. FastAPI saves to EFS
5. FastAPI returns to browser
6. Cloudflare caches for 1 year

**Subsequent Requests (cache hit):**
1. Browser → Cloudflare → Returns cached tile
2. **Never hits your backend**
3. **Never hits OS API**
4. **Completely free**

**Expected Cache Hit Rate:** >95% after warmup

### Cost Breakdown

**Tile Storage (EFS):**
- Assume 10,000 unique tiles cached
- Average 15KB per tile
- Total: 150MB
- Cost: $0.30/GB/month × 0.15GB = **$0.05/month**
- After 30 days: IA storage = $0.016/GB/month × 0.15GB = **$0.002/month**

**OS API Costs:**
- With 95% cache hit: Only 5% of requests hit OS API
- With limits: Maximum 7M premium tiles/week
- Actual usage likely: <100K/week (due to Cloudflare caching)
- **Cloudflare saves you ~99% of potential OS API costs**

**Compute:**
- Minimal - most requests served by Cloudflare

## Monitoring

### CloudWatch Logs

Search for limit breaches:
```
fields @timestamp, @message
| filter @message like /tile_limit_exceeded/
| stats count() by limit_type, tile_type
```

### Usage Dashboard

Visit: `https://api.trigpointing.uk/v1/tiles/os/usage` (authenticated)

Shows:
- Current week usage
- Percentage of limits
- Your personal usage
- IP-based usage

### Alerts

Set up CloudWatch alarms:
- Global usage > 90% of limit
- User approaching limit (80%)
- Unusual spike in premium tile requests

## Manual EFS Management

### SSH to Bastion

```bash
ssh bastion
```

### Mount EFS

```bash
sudo mkdir -p /mnt/tiles
sudo mount -t nfs4 -o nfsvers=4.1 \
  fs-xxxxx.efs.eu-west-1.amazonaws.com:/ /mnt/tiles
```

### Check Cache Size

```bash
du -sh /mnt/tiles/*
```

### Clear Cache (if needed)

```bash
# Clear specific layer
sudo rm -rf /mnt/tiles/Outdoor_3857/

# Clear high-zoom tiles only
find /mnt/tiles -name "1[7-9]" -type d -exec rm -rf {} +
```

## Troubleshooting

### Tiles Not Loading

1. Check FastAPI logs for errors
2. Verify OS_API_KEY is set in Secrets Manager
3. Check EFS mount is healthy
4. Test OS API directly

### High Costs

1. Check usage dashboard
2. Look for unusual IPs in CloudWatch
3. Reduce limits temporarily
4. Check for bot traffic

### Slow Performance

1. Check Cloudflare cache hit rate (should be >90%)
2. Check EFS performance metrics
3. Consider provisioned throughput if needed

## Security

**API Key Protection:**
- ✅ Never exposed to browser
- ✅ Stored in AWS Secrets Manager
- ✅ Encrypted in transit (HTTPS)
- ✅ Encrypted at rest (EFS, Secrets Manager)

**Rate Limiting:**
- ✅ Multi-dimensional tracking
- ✅ Per-IP limits prevent individual abuse
- ✅ Global limits prevent aggregate overuse
- ✅ Anonymous users tracked separately

**Access Control:**
- No authentication required (tiles are public data)
- Usage dashboard requires authentication
- Admin features require admin role

## Future Enhancements

- S3 storage for tiles (cheaper than EFS for infrequent access)
- Pre-warming cache for popular tiles
- Batch tile requests for efficiency
- WebP format support for smaller tile sizes
- Tile generation for custom styles

