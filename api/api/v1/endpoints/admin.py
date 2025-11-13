"""
Admin endpoints for cache management and contact form.
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.api.deps import get_current_user_optional, get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.config import settings
from api.core.logging import get_logger
from api.crud import user as user_crud
from api.models.user import User
from api.schemas.admin import (
    AdminMigrationRequest,
    AdminMigrationResponse,
    AdminUserSearchResponse,
    AdminUserSearchResult,
)
from api.schemas.contact import ContactRequest, ContactResponse
from api.services.auth0_service import (
    Auth0EmailAlreadyExistsError,
    Auth0UserCreationFailedError,
    auth0_service,
)
from api.services.cache_invalidator import invalidate_patterns, invalidate_user_caches
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
    admin_user: User = Depends(require_admin()),
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


@router.delete(
    "/cache/trigs/export",
    openapi_extra=openapi_lifecycle("beta"),
)
def clear_export_cache(
    current_user: User = Depends(require_admin),
):
    """
    Clear the trigs export cache (admin only).

    Requires `api:admin` scope.

    This endpoint clears the heavily-cached /v1/trigs/export endpoint,
    forcing it to regenerate on the next request. Use this when you need
    to refresh the bulk export data after significant database changes.
    """
    deleted = invalidate_patterns(["trigs:export:*"])
    return {"message": f"Cleared {deleted} cache keys", "deleted_count": deleted}


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


@router.get(
    "/legacy-migration/users",
    response_model=AdminUserSearchResponse,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Search legacy users by username or email fragment for admin migration.",
    ),
)
def search_legacy_users_for_migration(
    q: str = Query(
        ...,
        description="Username or email fragment to search for",
        min_length=2,
    ),
    limit: int = Query(
        20,
        ge=1,
        le=50,
        description="Maximum number of results to return (default 20, max 50).",
    ),
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> AdminUserSearchResponse:
    """Search legacy users by username or email fragment."""

    query = q.strip()
    if len(query) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Search query must contain at least two non-space characters.",
        )

    logger.info(
        json.dumps(
            {
                "event": "admin_legacy_migration_search",
                "query": query,
                "limit": limit,
                "admin_user_id": int(admin_user.id),
            }
        )
    )

    users = user_crud.search_users_by_name_or_email(db, query, limit)
    items = [
        AdminUserSearchResult(
            id=int(user.id),
            name=str(user.name),
            email=str(user.email),
            email_valid=str(user.email_valid),
            auth0_user_id=str(user.auth0_user_id) if user.auth0_user_id else None,
            has_auth0_account=bool(user.auth0_user_id),
        )
        for user in users
    ]

    return AdminUserSearchResponse(items=items)


@router.post(
    "/legacy-migration/migrate",
    response_model=AdminMigrationResponse,
    status_code=status.HTTP_200_OK,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Migrate a legacy user into Auth0 on their behalf.",
    ),
)
def migrate_user_to_auth0(
    request: AdminMigrationRequest,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> AdminMigrationResponse:
    """Create an Auth0 user for a legacy account and update local records."""

    logger.info(
        json.dumps(
            {
                "event": "admin_legacy_migration_start",
                "admin_user_id": int(admin_user.id),
                "target_user_id": request.user_id,
                "email": request.email,
            }
        )
    )

    user = user_crud.get_user_by_id(db, request.user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.auth0_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This user already has an Auth0 account.",
        )

    email = request.email.strip()

    existing = user_crud.get_user_by_email(db, email)
    if existing and int(existing.id) != int(user.id):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The email address {email} is already in use by another user.",
        )

    try:
        auth0_user = auth0_service.create_user_for_admin_migration(
            username=str(user.name),
            email=email,
            legacy_user_id=int(user.id),
            firstname=str(user.firstname) if user.firstname else None,
            surname=str(user.surname) if user.surname else None,
        )
    except Auth0EmailAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The email address {email} is already registered in Auth0.",
        )
    except Auth0UserCreationFailedError as exc:
        logger.error(
            json.dumps(
                {
                    "event": "admin_legacy_migration_auth0_failure",
                    "user_id": int(user.id),
                    "email": email,
                    "details": getattr(exc, "details", {}),
                }
            )
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Failed to create Auth0 user. Please try again later.",
        )
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            json.dumps(
                {
                    "event": "admin_legacy_migration_unexpected_error",
                    "user_id": int(user.id),
                    "email": email,
                    "error": str(exc),
                }
            )
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during migration.",
        )

    auth0_user_id = auth0_user.get("user_id")
    if not auth0_user_id:
        logger.error(
            json.dumps(
                {
                    "event": "admin_legacy_migration_missing_auth0_id",
                    "user_id": int(user.id),
                    "email": email,
                }
            )
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Auth0 did not return a user identifier.",
        )

    auth0_user_id_str = str(auth0_user_id)
    user.auth0_user_id = auth0_user_id_str  # type: ignore
    user.email = email  # type: ignore
    user.email_valid = "Y"  # type: ignore

    def cleanup_auth0_user() -> None:
        try:
            deleted = auth0_service.delete_user(auth0_user_id_str)
            log_payload = {
                "event": "admin_legacy_migration_cleanup_auth0_user",
                "auth0_user_id": auth0_user_id_str,
                "deleted": bool(deleted),
            }
            if deleted:
                logger.info(json.dumps(log_payload))
            else:
                logger.warning(json.dumps(log_payload))
        except Exception as cleanup_exc:  # pragma: no cover - best effort clean-up
            logger.error(
                "Failed to clean up Auth0 user after migration error",
                extra={
                    "auth0_user_id": auth0_user_id_str,
                    "error": str(cleanup_exc),
                },
                exc_info=True,
            )

    try:
        db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        cleanup_auth0_user()
        logger.error(
            "Auth0 migration database integrity error",
            extra={
                "user_id": int(user.id),
                "auth0_user_id": auth0_user_id_str,
                "email": email,
                "error": str(exc),
            },
            exc_info=True,
        )
        message = "Database rejected the Auth0 mapping. Please verify the user has not already been migrated."
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=message,
        ) from exc
    except Exception as exc:
        db.rollback()
        cleanup_auth0_user()
        logger.error(
            "Auth0 migration database persist failure",
            extra={
                "user_id": int(user.id),
                "auth0_user_id": auth0_user_id_str,
                "email": email,
                "error": str(exc),
            },
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist Auth0 migration details in the database.",
        ) from exc

    db.refresh(user)
    invalidate_user_caches(user_id=int(user.id))

    message = (
        f"Hi {user.name}! Your account has been migrated to the new login system. "
        'In order to choose a password, please click "login" in the top-right corner of the Trigpointing.uk homepage, '
        'click "Can\'t log in to your account?", enter '
        f'"{email}" and click continue. Within a few minutes you should receive an email from contact@trigpointing.uk, '
        "containing a link which will enable you to set a password."
    )

    logger.info(
        json.dumps(
            {
                "event": "admin_legacy_migration_success",
                "user_id": int(user.id),
                "email": email,
                "auth0_user_id": auth0_user_id_str,
                "admin_user_id": int(admin_user.id),
            }
        )
    )

    return AdminMigrationResponse(
        user_id=int(user.id),
        username=str(user.name),
        email=email,
        auth0_user_id=auth0_user_id_str,
        message=message,
    )
