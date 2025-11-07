"""
OS Maps tile proxy endpoint with caching and usage tracking.

Proxies requests to OS Maps API while:
- Hiding API key from client
- Caching tiles in EFS for cost savings
- Tracking usage across multiple dimensions
- Enforcing rate limits to control costs
"""

from pathlib import Path

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import Response

from api.api.deps import get_current_user_optional
from api.core.config import settings
from api.core.logging import get_logger
from api.services.tile_usage import get_tile_usage_tracker, is_premium_tile

logger = get_logger(__name__)

router = APIRouter()

# Allowed OS Maps layers
ALLOWED_LAYERS = ["Outdoor_3857", "Light_3857", "Leisure_27700"]


def get_client_ip(request: Request) -> str:
    """
    Get client IP address from request.

    Handles X-Forwarded-For header from load balancer.

    Args:
        request: FastAPI request

    Returns:
        Client IP address
    """
    # Check X-Forwarded-For header (from ALB/Cloudflare)
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # Take first IP in chain
        return forwarded_for.split(",")[0].strip()

    # Fall back to direct connection IP
    return request.client.host if request.client else "unknown"


@router.get("/{layer}/{z}/{x}/{y}.png")
async def proxy_os_tile(
    layer: str,
    z: int,
    x: int,
    y: int,
    request: Request,
    current_user=Depends(get_current_user_optional),
):
    """
    Proxy OS Maps API tiles with caching and rate limiting.

    Serves tiles from EFS cache if available (counts as FREE),
    otherwise proxies from OS API (counts as premium/free based on zoom).

    Enforces usage limits across multiple dimensions to control costs.

    Args:
        layer: OS Maps layer name (Outdoor_3857, Light_3857, Leisure_27700)
        z: Zoom level
        x: Tile X coordinate
        y: Tile Y coordinate
        request: FastAPI request (for IP extraction)
        current_user: Optional authenticated user

    Returns:
        PNG tile image

    Raises:
        HTTPException: 400 for invalid layer, 429 for rate limit exceeded, 502 for OS API errors
    """
    # Validate layer
    if layer not in ALLOWED_LAYERS:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid layer. Allowed: {', '.join(ALLOWED_LAYERS)}",
        )

    # Get client IP and user ID
    client_ip = get_client_ip(request)
    user_id = int(current_user.id) if current_user else None

    # Check if tile is cached in EFS
    tile_path = Path(settings.TILE_CACHE_DIR) / layer / str(z) / str(x) / f"{y}.png"
    from_cache = tile_path.exists()

    # Check usage limits before proceeding
    tracker = get_tile_usage_tracker()
    allowed, error_message = tracker.check_limits(
        layer, z, from_cache, client_ip, user_id
    )

    if not allowed:
        # Log the rejection
        logger.warning(
            f"Tile request blocked: {error_message} "
            f"(layer={layer}, z={z}, user_id={user_id}, ip={client_ip})"
        )
        raise HTTPException(status_code=429, detail=error_message)

    # Serve from cache if available
    if from_cache:
        try:
            with open(tile_path, "rb") as f:
                tile_data = f.read()

            # Record usage (cached tile = free)
            tracker.record_usage(layer, z, from_cache, client_ip, user_id)

            return Response(
                content=tile_data,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=31536000",  # 1 year for Cloudflare
                    "X-Tile-Source": "cache",
                    "X-Tile-Type": "free",  # Cached tiles are always free
                },
            )
        except Exception as e:
            logger.error(f"Failed to read cached tile {tile_path}: {e}")
            # Fall through to proxy if cache read fails

    # Tile not cached - proxy from OS API
    if not settings.OS_API_KEY:
        raise HTTPException(
            status_code=500,
            detail="OS API key not configured",
        )

    # Construct OS API URL
    os_url = (
        f"https://api.os.uk/maps/raster/v1/zxy/{layer}/{z}/{x}/{y}.png"
        f"?key={settings.OS_API_KEY}"
    )

    # Proxy request to OS API
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(os_url)
            response.raise_for_status()

            tile_data = response.content

            # Save to EFS cache for future requests
            try:
                tile_path.parent.mkdir(parents=True, exist_ok=True)
                with open(tile_path, "wb") as f:
                    f.write(tile_data)
            except Exception as e:
                logger.error(f"Failed to cache tile to {tile_path}: {e}")
                # Continue even if caching fails

            # Record usage (proxied tile = premium or free based on zoom)
            tracker.record_usage(layer, z, False, client_ip, user_id)

            # Determine if this was a premium tile
            premium = is_premium_tile(layer, z, False)

            return Response(
                content=tile_data,
                media_type="image/png",
                headers={
                    "Cache-Control": "public, max-age=31536000",  # 1 year for Cloudflare
                    "X-Tile-Source": "os-api",
                    "X-Tile-Type": "premium" if premium else "free",
                },
            )

        except httpx.HTTPStatusError as e:
            logger.error(f"OS API returned error {e.response.status_code} for {os_url}")
            raise HTTPException(
                status_code=502,
                detail=f"Failed to fetch tile from OS API: HTTP {e.response.status_code}",
            )
        except httpx.RequestError as e:
            logger.error(f"Failed to connect to OS API: {e}")
            raise HTTPException(
                status_code=502,
                detail="Failed to connect to OS Maps API",
            )


@router.get("/usage")
async def get_tile_usage(
    request: Request,
    current_user=Depends(get_current_user_optional),
):
    """
    Get tile usage statistics (admin-only).

    Returns current week's usage across all tracked dimensions.

    Requires authentication and admin privileges.

    Returns:
        Usage statistics with counts and limits

    Raises:
        HTTPException: 401 if not authenticated, 403 if not admin
    """
    # Require authentication
    if not current_user:
        raise HTTPException(status_code=401, detail="Authentication required")

    # Check if user is admin (adjust this based on your admin check logic)
    # For now, allowing any authenticated user to view stats
    # TODO: Add proper admin role check
    # if not current_user.is_admin:
    #     raise HTTPException(status_code=403, detail="Admin access required")

    client_ip = get_client_ip(request)
    user_id = int(current_user.id)

    tracker = get_tile_usage_tracker()
    stats = tracker.get_usage_stats(user_id=user_id, client_ip=client_ip)

    return stats
