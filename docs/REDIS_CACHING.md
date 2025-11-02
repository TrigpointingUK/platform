# Redis API Caching Implementation Guide

## Overview

This document describes the comprehensive Redis-based caching system implemented for the TrigpointingUK API. The system provides:

- **Long TTL caching** (1-24 hours depending on endpoint)
- **Instant cache invalidation** on write operations
- **Cache headers** for debugging (`X-Cache-Status`, `X-Cache-Key`, etc.)
- **Admin endpoints** for cache management
- **Graceful degradation** when Redis is unavailable

## Architecture

### Core Components

#### 1. Cache Service (`api/services/cache_service.py`)

Provides low-level Redis operations:

- `get_redis_client()` - Singleton Redis client with connection pooling
- `generate_cache_key()` - Generate structured cache keys
- `cache_get()` - Get value from cache with age calculation
- `cache_set()` - Set value with TTL
- `cache_delete()` - Delete single key
- `cache_delete_pattern()` - Delete keys matching pattern (e.g., `trig:*`)
- `cache_flush_all()` - Flush entire cache
- `cache_get_stats()` - Get cache statistics

**Cache Key Structure:**
```
{resource_type}:{resource_id}:{subresource}:params_{hash}:{version}
```

Examples:
- `trig:123:v1` - Single trig
- `trig:123:logs:params_abc123:v1` - Trig logs with specific pagination
- `trigs:list:params_def456:v1` - Trig list with filters

#### 2. Cache Decorator (`api/utils/cache_decorator.py`)

Provides `@cached()` decorator for endpoints:

```python
@router.get("/trigs/{trig_id}")
@cached(resource_type="trig", ttl=86400, resource_id_param="trig_id")
def get_trig(trig_id: int, db: Session = Depends(get_db)):
    ...
```

Features:
- Automatic cache key generation from function parameters
- Query parameter hashing for unique keys
- Cache-Control: no-cache header support for bypass
- Automatic cache headers on responses
- JSON serialization/deserialization

#### 3. Cache Invalidator (`api/services/cache_invalidator.py`)

Centralized invalidation logic:

- `invalidate_log_caches()` - Invalidate when logs change
- `invalidate_photo_caches()` - Invalidate when photos change
- `invalidate_user_caches()` - Invalidate when users change
- `invalidate_trig_caches()` - Invalidate when trigs change

**Invalidation Patterns:**

When a log is created/updated/deleted:
```python
invalidate_patterns([
    "stats:site:*",      # Site-wide stats
    f"trig:{trig_id}:*", # All trig-related caches
    f"user:{user_id}:*", # All user-related caches
    "trigs:list:*",      # All trig lists
    "logs:list:*",       # All log lists
])
```

When a photo is created/updated/deleted:
```python
invalidate_patterns([
    "stats:site:*",
    f"trig:{trig_id}:*",
    f"user:{user_id}:*",
    f"log:{log_id}:*",
    "photos:list:*",
])
```

### CRUD Integration

Cache invalidation hooks added to:

1. **`api/crud/tlog.py`**
   - `create_log()` → invalidates related caches
   - `update_log()` → invalidates related caches
   - `delete_log_hard()` → invalidates related caches
   - `soft_delete_photos_for_log()` → invalidates photo caches

2. **`api/crud/tphoto.py`**
   - `create_photo()` → invalidates photo-related caches
   - `update_photo()` → invalidates photo-related caches
   - `delete_photo()` → invalidates photo-related caches

3. **`api/crud/user.py`**
   - `create_user()` → invalidates user lists and site stats

## Endpoint Caching Strategy

### High-Value Endpoints (Long TTLs)

| Endpoint | TTL | Cache Key Pattern | Invalidated On |
|----------|-----|-------------------|----------------|
| `/v1/stats/site` | 1 hour | `stats:site:v1` | Any log, photo, or user creation |
| `/v1/trigs/{trig_id}` | 24 hours | `trig:{id}:include_{hash}:v1` | Logs/photos for this trig |
| `/v1/users/{user_id}` | 6 hours | `user:{id}:include_{hash}:v1` | User's logs/photos change |
| `/v1/users/{user_id}/badge` | 5 minutes | `user:{id}:badge:params_{hash}:v1` | User's logs/photos change |

### List Endpoints (Medium TTLs)

| Endpoint | TTL | Cache Key Pattern | Invalidated On |
|----------|-----|-------------------|----------------|
| `/v1/trigs` | 12 hours | `trigs:list:params_{hash}:v1` | Any log (conservative) |
| `/v1/trigs/{trig_id}/logs` | 2 hours | `trig:{id}:logs:params_{hash}:v1` | Logs for this trig |
| `/v1/trigs/{trig_id}/photos` | 2 hours | `trig:{id}:photos:params_{hash}:v1` | Photos for this trig |
| `/v1/users` | 12 hours | `users:list:params_{hash}:v1` | New user registration |
| `/v1/users/{user_id}/logs` | 2 hours | `user:{id}:logs:params_{hash}:v1` | User's logs change |
| `/v1/users/{user_id}/photos` | 2 hours | `user:{id}:photos:params_{hash}:v1` | User's photos change |
| `/v1/logs` | 1 hour | `logs:list:params_{hash}:v1` | Any log created/updated/deleted |
| `/v1/photos` | 1 hour | `photos:list:params_{hash}:v1` | Any photo created/updated/deleted |

### Individual Resource Endpoints

| Endpoint | TTL | Cache Key Pattern | Invalidated On |
|----------|-----|-------------------|----------------|
| `/v1/logs/{log_id}` | 6 hours | `log:{id}:include_{hash}:v1` | Log updated/deleted or photos change |
| `/v1/photos/{photo_id}` | 12 hours | `photo:{id}:v1` | Photo updated/deleted |

### Generated Image Endpoints

| Endpoint | TTL | Cache Key Pattern | Invalidated On |
|----------|-----|-------------------|----------------|
| `/v1/trigs/{trig_id}/map` | 4 hours | `trig:{id}:map:params_{hash}:v1` | Logs for this trig (shows logged status) |
| `/v1/users/{user_id}/map` | 4 hours | `user:{id}:map:params_{hash}:v1` | User's logs change |

## Cache Management

### Admin API Endpoints

**Get Cache Statistics**
```http
GET /v1/admin/cache/stats
Authorization: Bearer <token_with_api:admin_scope>
```

Returns:
```json
{
  "total_keys": 1234,
  "memory_used_bytes": 5242880,
  "memory_used_human": "5.00M",
  "keyspace_hits": 98765,
  "keyspace_misses": 1234,
  "hit_rate_percent": 98.77,
  "connected_clients": 3
}
```

**Flush Cache by Pattern**
```http
DELETE /v1/admin/cache?pattern=trig:*
Authorization: Bearer <token_with_api:admin_scope>
```

**Flush All Cache**
```http
DELETE /v1/admin/cache
Authorization: Bearer <token_with_api:admin_scope>
```

### Cache Bypass

Send `Cache-Control: no-cache` header to bypass cache for a specific request:

```bash
curl -H "Cache-Control: no-cache" https://api.trigpointing.me/v1/trigs/123
```

The response will include `X-Cache-Status: BYPASS`

### Cache Headers

All cached responses include these headers:

- `X-Cache-Status`: `HIT` | `MISS` | `BYPASS`
- `X-Cache-Key`: The cache key used (e.g., `trig:123:v1`)
- `X-Cache-TTL`: Remaining TTL in seconds (on HIT)
- `X-Cache-Age`: Age of cached response in seconds (on HIT)

Example:
```http
HTTP/1.1 200 OK
X-Cache-Status: HIT
X-Cache-Key: trig:123:v1
X-Cache-Age: 45
X-Cache-TTL: 86355
```

## Configuration

### Environment Variables

```bash
# Redis connection URL
REDIS_URL=redis://localhost:6379

# Globally enable/disable caching (default: true)
CACHE_ENABLED=true
```

### Testing Support

For pytest, add this fixture to clear cache between tests:

```python
import pytest
from api.services.cache_service import cache_flush_all

@pytest.fixture(autouse=True)
def clear_cache():
    """Clear cache before each test."""
    cache_flush_all()
    yield
    cache_flush_all()
```

Or disable caching entirely in tests:

```python
# In conftest.py or test setup
os.environ["CACHE_ENABLED"] = "false"
```

## Redis CLI Commands

Manual cache management via Redis CLI:

```bash
# Connect to Redis
redis-cli -h localhost -p 6379

# List all keys
KEYS "*"

# Get specific key
GET "trig:123:v1"

# Delete key
DEL "trig:123:v1"

# Delete by pattern
redis-cli --scan --pattern "trig:*" | xargs redis-cli DEL

# Get key TTL
TTL "trig:123:v1"

# Flush all cache
FLUSHDB

# Get cache stats
INFO stats
INFO memory
```

## Performance Testing

To test cache effectiveness:

1. **Initial request (cache miss)**:
   ```bash
   curl -w "\nTime: %{time_total}s\n" https://api.trigpointing.me/v1/stats/site
   ```

2. **Subsequent request (cache hit)**:
   ```bash
   curl -w "\nTime: %{time_total}s\n" https://api.trigpointing.me/v1/stats/site
   ```

3. **Check headers** in browser DevTools Network tab:
   - Look for `X-Cache-Status: HIT`
   - Compare response times

## Monitoring

### Structured Logging

All cache operations are logged with structured JSON:

```json
{
  "event": "cache_hit",
  "key": "trig:123:v1",
  "age": 45
}
```

```json
{
  "event": "cache_invalidated",
  "patterns": ["stats:site:*", "trig:123:*"],
  "keys_deleted": 5
}
```

### Log Events

- `cache_hit` - Cache hit with key and age
- `cache_miss_stored` - Cache miss, value stored
- `cache_bypass` - Cache bypassed via header
- `cache_skip` - Response not cacheable (e.g., StreamingResponse)
- `cache_store_error` - Error storing value
- `cache_invalidated` - Keys invalidated
- `cache_delete_pattern` - Pattern-based deletion
- `cache_redis_connected` - Redis connection established
- `cache_redis_connection_failed` - Redis connection failed

## Best Practices

1. **Choose appropriate TTLs**:
   - Static data (trigs): 24 hours
   - User-generated lists: 1-6 hours
   - Generated images: 4 hours
   - Highly dynamic: 5-15 minutes

2. **Be conservative with invalidation**:
   - Better to invalidate too much than serve stale data
   - Use pattern matching for related resources

3. **Monitor cache effectiveness**:
   - Check hit rates via `/v1/admin/cache/stats`
   - Adjust TTLs based on actual usage patterns

4. **Handle cache failures gracefully**:
   - API continues to work if Redis is down
   - No user-facing errors from cache failures

5. **Test invalidation logic**:
   - Verify caches are cleared after write operations
   - Test pattern matching works correctly

## Troubleshooting

### Cache not working

1. Check Redis is running:
   ```bash
   redis-cli ping
   # Should return: PONG
   ```

2. Check `REDIS_URL` environment variable is set

3. Check logs for `cache_redis_connected` event

### Stale data being served

1. Check invalidation is being called in CRUD operations
2. Verify invalidation patterns match cache key patterns
3. Flush cache manually: `DELETE /v1/admin/cache`

### High memory usage

1. Check cache statistics: `GET /v1/admin/cache/stats`
2. Reduce TTLs for less-accessed endpoints
3. Configure Redis maxmemory policy: `allkeys-lru`

## Future Enhancements

Potential improvements for future iterations:

1. **Background cache warming**: Pre-populate cache for popular queries
2. **Cache compression**: Compress large responses before caching
3. **Probabilistic early expiration**: Prevent thundering herd on popular keys
4. **Per-user cache limits**: Prevent single users from dominating cache
5. **Cache metrics endpoint**: Expose Prometheus-compatible metrics
6. **Conditional caching**: Only cache responses above certain size
7. **Vary header support**: Cache different versions for different Accept headers

## Example: Adding Caching to a New Endpoint

```python
from api.utils.cache_decorator import cached

@router.get("/example/{resource_id}")
@cached(
    resource_type="example",
    ttl=3600,  # 1 hour
    resource_id_param="resource_id",
    subresource="detail",  # Optional
    include_query_params=True,  # Include query params in cache key
    version="v1"
)
def get_example(
    resource_id: int,
    include: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    # Your endpoint logic here
    ...
```

Then add invalidation in the corresponding CRUD operation:

```python
from api.services.cache_invalidator import invalidate_patterns

def update_example(db: Session, resource_id: int, updates: dict):
    # Update logic
    ...
    
    # Invalidate related caches
    invalidate_patterns([
        f"example:{resource_id}:*",
        "examples:list:*",
    ])
    
    return updated_resource
```

## Conclusion

The Redis caching system provides significant performance improvements for the API while maintaining data consistency through instant invalidation. The system is production-ready with comprehensive monitoring, debugging tools, and graceful degradation.

For questions or issues, check the logs for cache-related events or use the admin endpoints to inspect cache state.

