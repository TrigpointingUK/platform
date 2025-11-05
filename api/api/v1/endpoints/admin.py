"""
Admin endpoints for cache management and contact form.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from api.api.deps import get_current_user_optional, get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.config import settings
from api.core.logging import get_logger
from api.models.user import User
from api.schemas.contact import ContactRequest, ContactResponse
from api.services.cache_service import cache_delete_pattern, get_redis_client
from api.services.email_service import email_service

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "/cache/stats",
    openapi_extra=openapi_lifecycle("beta", note="Get cache statistics"),
)
def get_cache_stats(
    admin_user: User = Depends(require_admin), db: Session = Depends(get_db)
):
    """
    Get statistics about the Redis cache for this application and environment.

    Requires `api:admin` scope.

    Returns:
    - info: Redis INFO dictionary (subset)
    - keys_count: Number of keys belonging to this application/environment
    """
    client = get_redis_client()
    if not client:
        raise HTTPException(
            status_code=503, detail="Cache unavailable or not configured"
        )

    try:
        info = client.info()  # type: ignore[misc]
        # Filter info to relevant stats
        stats = {
            "redis_version": info.get("redis_version"),  # type: ignore[union-attr]
            "uptime_in_seconds": info.get("uptime_in_seconds"),  # type: ignore[union-attr]
            "connected_clients": info.get("connected_clients"),  # type: ignore[union-attr]
            "used_memory_human": info.get("used_memory_human"),  # type: ignore[union-attr]
            "total_keys": info.get("db0", {}).get("keys"),  # type: ignore[union-attr]
        }

        # Count keys specific to this application and environment
        environment = settings.ENVIRONMENT.lower()
        app_env_pattern = f"fastapi:{environment}:*"
        keys_count = len(client.keys(app_env_pattern))  # type: ignore[arg-type]

        stats["app_env_keys_count"] = keys_count
        stats["app_env_pattern"] = app_env_pattern

        logger.info(
            json.dumps(
                {
                    "event": "cache_stats_retrieved",
                    "app_env_keys_count": keys_count,
                }
            )
        )

        return stats
    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "event": "cache_stats_error",
                    "error": str(e),
                    "detail": "Failed to retrieve Redis info",
                }
            )
        )
        raise HTTPException(
            status_code=503,
            detail=f"Failed to retrieve Redis info: {e}",
        )


@router.delete(
    "/cache",
    openapi_extra=openapi_lifecycle("beta", note="Flush cache by pattern or all"),
)
def flush_cache(
    pattern: Optional[str] = Query(
        None,
        description="Redis key pattern to delete (e.g., 'trig:*'). Pattern will be automatically prefixed with 'fastapi:{environment}:'. If omitted, flushes ALL FastAPI cache for this environment.",
    ),
    admin_user: User = Depends(require_admin),
):
    """
    Flush cache keys by pattern or flush all cache for this application/environment.

    Requires `api:admin` scope.

    Args:
    - pattern: Optional Redis key pattern (e.g., 'trig:123:*', 'user:*')

    If pattern is provided, only matching keys are deleted (automatically prefixed with 'fastapi:{environment}:').
    If pattern is omitted, ALL cache keys for this application and environment are deleted.

    Note: This only affects FastAPI caches in the current environment. Other applications
    (mediawiki, forum) and other environments are not affected.

    Returns:
    - deleted_count: Number of keys deleted
    - pattern: The full pattern used (including prefix)
    """
    environment = settings.ENVIRONMENT.lower()

    if pattern:
        # Add fastapi:environment prefix to user's pattern
        full_pattern = f"fastapi:{environment}:{pattern}"
        deleted_count = cache_delete_pattern(full_pattern)
        if deleted_count < 0:
            raise HTTPException(
                status_code=503,
                detail="Cache unavailable or not configured",
            )
        return {
            "deleted_count": deleted_count,
            "pattern": full_pattern,
            "message": f"Deleted {deleted_count} cache keys matching pattern '{full_pattern}'",
        }
    else:
        # Flush all FastAPI cache for this environment only
        full_pattern = f"fastapi:{environment}:*"
        deleted_count = cache_delete_pattern(full_pattern)
        if deleted_count < 0:
            raise HTTPException(
                status_code=503,
                detail="Cache unavailable or not configured",
            )
        return {
            "deleted_count": deleted_count,
            "pattern": full_pattern,
            "message": f"Flushed all FastAPI cache keys for {environment} environment ({deleted_count} keys)",
        }


@router.post(
    "/contact",
    response_model=ContactResponse,
    status_code=status.HTTP_200_OK,
    openapi_extra=openapi_lifecycle(
        "beta", note="Submit contact form. Public endpoint, authentication optional."
    ),
)
def submit_contact(
    contact_request: ContactRequest,
    current_user: Optional[User] = Depends(get_current_user_optional),
):
    """
    Submit a contact form message.

    This endpoint is public and does not require authentication. If a user is
    logged in, their user ID and Auth0 user ID will be included in the email.

    Args:
        contact_request: Contact form data (name, email, subject, message)
        current_user: Optional authenticated user (if logged in)

    Returns:
        ContactResponse with success status and message
    """
    # Extract user information from token/db if user is authenticated
    auth0_user_id = None
    user_id = None
    username = None

    if current_user:
        user_id = int(current_user.id)
        username = str(current_user.name)  # Database username

        # Get Auth0 user ID and nickname from token payload
        token_payload = getattr(current_user, "_token_payload", None)
        if token_payload:
            auth0_user_id = token_payload.get("auth0_user_id")
            # Prefer nickname from token, fallback to name from token, then database name
            username = (
                token_payload.get("nickname") or token_payload.get("name") or username
            )

        # Override request user_id/auth0_user_id/username with actual values from token/db
        # This prevents users from spoofing these values
        contact_request.user_id = user_id
        contact_request.auth0_user_id = auth0_user_id
        contact_request.username = username

    # Send email via SES
    success = email_service.send_contact_email(
        to_email="contact@teasel.org",
        reply_to=contact_request.email,
        subject=contact_request.subject,
        message=contact_request.message,
        name=contact_request.name,
        user_id=contact_request.user_id,
        auth0_user_id=contact_request.auth0_user_id,
        username=contact_request.username,
    )

    if success:
        return ContactResponse(
            success=True,
            message="Your message has been sent successfully. We'll get back to you soon!",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send email. Please try again later.",
        )
