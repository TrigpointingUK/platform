"""
Cache decorator for FastAPI endpoints.

Provides @cached() decorator that wraps endpoint functions with Redis caching,
including support for cache headers, bypass, and automatic serialization.
"""

import functools
import inspect
import json
from typing import Callable, Optional

from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse, StreamingResponse

from api.core.logging import get_logger
from api.services.cache_service import cache_get, cache_set, generate_cache_key

logger = get_logger(__name__)


def cached(
    resource_type: str,
    ttl: int,
    resource_id_param: Optional[str] = None,
    subresource: Optional[str] = None,
    include_query_params: bool = True,
    version: str = "v1",
):
    """
    Decorator to cache endpoint responses in Redis.

    Args:
        resource_type: Type of resource (e.g., 'trig', 'user', 'log')
        ttl: Time to live in seconds
        resource_id_param: Name of path parameter containing resource ID
        subresource: Optional subresource name (e.g., 'logs', 'photos')
        include_query_params: Whether to include query params in cache key
        version: Cache version for invalidation

    Usage:
        @router.get("/trigs/{trig_id}")
        @cached(resource_type="trig", ttl=86400, resource_id_param="trig_id")
        def get_trig(trig_id: int, db: Session = Depends(get_db)):
            ...

    The decorator:
    - Generates cache keys based on endpoint and parameters
    - Checks cache before calling endpoint function
    - Stores result in cache on cache miss
    - Adds X-Cache-* headers to response (in middleware)
    - Respects Cache-Control: no-cache header for cache bypass

    Note: The Request object is automatically injected by FastAPI's dependency system
    if not already present in the function signature.
    """

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Try to get request from kwargs (may not exist in all endpoints)
            request: Optional[Request] = kwargs.get("request")

            # Check for cache bypass header
            bypass_cache = False
            if request:
                cache_control = request.headers.get("cache-control", "").lower()
                if "no-cache" in cache_control:
                    bypass_cache = True
                    logger.debug(
                        json.dumps(
                            {
                                "event": "cache_bypass",
                                "reason": "Cache-Control: no-cache header present",
                            }
                        )
                    )

            # Generate cache key
            resource_id = None
            if resource_id_param and resource_id_param in kwargs:
                resource_id = str(kwargs[resource_id_param])

            params = None
            if include_query_params:
                # Build params dict from function kwargs
                # Exclude special parameters like 'db', 'request', 'current_user', etc.
                excluded_params = {
                    "db",
                    "request",
                    "current_user",
                    "_lc",
                    "token_payload",
                }
                params = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in excluded_params
                    and v is not None
                    and k != resource_id_param
                }

            cache_key = generate_cache_key(
                resource_type=resource_type,
                resource_id=resource_id,
                subresource=subresource,
                params=params,
                version=version,
            )

            # Try to get from cache (unless bypassed)
            cached_value = None
            cache_age = None
            cache_status = "MISS"

            if not bypass_cache:
                cached_value, cache_age = cache_get(cache_key)
                if cached_value is not None:
                    cache_status = "HIT"
                    logger.debug(
                        json.dumps(
                            {
                                "event": "cache_hit",
                                "key": cache_key,
                                "age": cache_age,
                            }
                        )
                    )
            else:
                cache_status = "BYPASS"

            # Call endpoint function if cache miss or bypass
            if cached_value is None:
                result = await func(*args, **kwargs)

                # Cache the result (unless bypassed)
                if not bypass_cache:
                    # Serialize result for caching
                    try:
                        # Handle different response types
                        if isinstance(result, (StreamingResponse, Response)):
                            # Can't cache Response objects directly
                            logger.debug(
                                json.dumps(
                                    {
                                        "event": "cache_skip",
                                        "reason": "Response object not cacheable",
                                    }
                                )
                            )
                        else:
                            # Cache the result (convert to JSON-serializable format first)
                            cache_set(cache_key, jsonable_encoder(result), ttl)
                            logger.debug(
                                json.dumps(
                                    {
                                        "event": "cache_miss_stored",
                                        "key": cache_key,
                                        "ttl": ttl,
                                    }
                                )
                            )
                    except Exception as e:
                        logger.warning(
                            json.dumps(
                                {
                                    "event": "cache_store_error",
                                    "key": cache_key,
                                    "error": str(e),
                                }
                            )
                        )

                # Add cache headers - wrap in JSONResponse if needed
                if isinstance(result, Response):
                    result.headers["X-Cache-Status"] = cache_status
                    result.headers["X-Cache-Key"] = cache_key
                    result.headers["X-Cache-TTL"] = str(ttl)
                    return result
                else:
                    # Return JSONResponse with cache headers for dict/list results
                    return JSONResponse(
                        content=jsonable_encoder(result),
                        headers={
                            "X-Cache-Status": cache_status,
                            "X-Cache-Key": cache_key,
                            "X-Cache-TTL": str(ttl),
                        },
                    )
            else:
                # Return cached result with cache headers
                return JSONResponse(
                    content=jsonable_encoder(cached_value),
                    headers={
                        "X-Cache-Status": "HIT",
                        "X-Cache-Key": cache_key,
                        "X-Cache-Age": str(cache_age) if cache_age else "0",
                        "X-Cache-TTL": str(ttl),
                    },
                )

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Try to get request from kwargs (may not exist in all endpoints)
            request: Optional[Request] = kwargs.get("request")

            # Check for cache bypass header
            bypass_cache = False
            if request:
                cache_control = request.headers.get("cache-control", "").lower()
                if "no-cache" in cache_control:
                    bypass_cache = True
                    logger.debug(
                        json.dumps(
                            {
                                "event": "cache_bypass",
                                "reason": "Cache-Control: no-cache header present",
                            }
                        )
                    )

            # Generate cache key
            resource_id = None
            if resource_id_param and resource_id_param in kwargs:
                resource_id = str(kwargs[resource_id_param])

            params = None
            if include_query_params:
                # Build params dict from function kwargs
                # Exclude special parameters like 'db', 'request', 'current_user', etc.
                excluded_params = {
                    "db",
                    "request",
                    "current_user",
                    "_lc",
                    "token_payload",
                }
                params = {
                    k: v
                    for k, v in kwargs.items()
                    if k not in excluded_params
                    and v is not None
                    and k != resource_id_param
                }

            cache_key = generate_cache_key(
                resource_type=resource_type,
                resource_id=resource_id,
                subresource=subresource,
                params=params,
                version=version,
            )

            # Try to get from cache (unless bypassed)
            cached_value = None
            cache_age = None
            cache_status = "MISS"

            if not bypass_cache:
                cached_value, cache_age = cache_get(cache_key)
                if cached_value is not None:
                    cache_status = "HIT"
                    logger.debug(
                        json.dumps(
                            {
                                "event": "cache_hit",
                                "key": cache_key,
                                "age": cache_age,
                            }
                        )
                    )
            else:
                cache_status = "BYPASS"

            # Call endpoint function if cache miss or bypass
            if cached_value is None:
                result = func(*args, **kwargs)

                # Cache the result (unless bypassed)
                if not bypass_cache:
                    # Serialize result for caching
                    try:
                        # Handle different response types
                        if isinstance(result, (StreamingResponse, Response)):
                            # Can't cache Response objects directly
                            logger.debug(
                                json.dumps(
                                    {
                                        "event": "cache_skip",
                                        "reason": "Response object not cacheable",
                                    }
                                )
                            )
                        else:
                            # Cache the result (convert to JSON-serializable format first)
                            cache_set(cache_key, jsonable_encoder(result), ttl)
                            logger.debug(
                                json.dumps(
                                    {
                                        "event": "cache_miss_stored",
                                        "key": cache_key,
                                        "ttl": ttl,
                                    }
                                )
                            )
                    except Exception as e:
                        logger.warning(
                            json.dumps(
                                {
                                    "event": "cache_store_error",
                                    "key": cache_key,
                                    "error": str(e),
                                }
                            )
                        )

                # Add cache headers - wrap in JSONResponse if needed
                if isinstance(result, Response):
                    result.headers["X-Cache-Status"] = cache_status
                    result.headers["X-Cache-Key"] = cache_key
                    result.headers["X-Cache-TTL"] = str(ttl)
                    return result
                else:
                    # Return JSONResponse with cache headers for dict/list results
                    return JSONResponse(
                        content=jsonable_encoder(result),
                        headers={
                            "X-Cache-Status": cache_status,
                            "X-Cache-Key": cache_key,
                            "X-Cache-TTL": str(ttl),
                        },
                    )
            else:
                # Return cached result with cache headers
                return JSONResponse(
                    content=jsonable_encoder(cached_value),
                    headers={
                        "X-Cache-Status": "HIT",
                        "X-Cache-Key": cache_key,
                        "X-Cache-Age": str(cache_age) if cache_age else "0",
                        "X-Cache-TTL": str(ttl),
                    },
                )

        # Return appropriate wrapper based on whether function is async
        if inspect.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
