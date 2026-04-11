"""
Admin endpoints for cache management and contact form.
"""

import json
from datetime import UTC, datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from api.api.deps import get_current_user_optional, get_db, require_admin
from api.api.lifecycle import openapi_lifecycle
from api.core.config import settings
from api.core.logging import get_logger
from api.crud import location as location_crud
from api.crud import status as status_crud
from api.crud import tlog as tlog_crud
from api.crud import trig as trig_crud
from api.crud import trig_type as trig_type_crud
from api.crud import user as user_crud
from api.crud import user_merge as user_merge_crud
from api.models.user import User
from api.schemas.admin import (
    AdminMergeUsersPreview,
    AdminMergeUsersRequest,
    AdminMergeUsersResponse,
    AdminMigrationRequest,
    AdminMigrationResponse,
    AdminUserSearchResponse,
    AdminUserSearchResult,
    MergeRecordCounts,
)
from api.schemas.contact import ContactRequest, ContactResponse
from api.schemas.log_admin import (
    DuplicateLogGroupEntry,
    DuplicateLogGroupItem,
    LogNeedsAttentionListResponse,
    LogNeedsAttentionSummary,
    OrphanedLogItem,
)
from api.schemas.trig_admin import (
    StatusResponse,
    TrigAdminCreate,
    TrigAdminDetail,
    TrigAdminUpdate,
    TrigNeedsAttentionListItem,
    TrigNeedsAttentionSummary,
)
from api.services.auth0_service import (
    Auth0EmailAlreadyExistsError,
    Auth0UserCreationFailedError,
    auth0_service,
)
from api.services.cache_invalidator import (
    invalidate_patterns,
    invalidate_trig_caches,
    invalidate_user_caches,
)
from api.services.cache_service import cache_delete_pattern, get_redis_client
from api.services.email_service import email_service
from api.services.user_stats import refresh_user_activity_summary

logger = get_logger(__name__)
router = APIRouter()
ADMIN_SCOPE_DEPENDENCY = require_admin()


@router.post(
    "/user-stats/refresh",
    status_code=status.HTTP_202_ACCEPTED,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Trigger a concurrent refresh of the user activity materialised view.",
    ),
)
def refresh_user_stats_view(
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
    db: Session = Depends(get_db),
):
    """
    Trigger a concurrent refresh of the user activity summary materialised view.

    Requires `api:admin` scope.
    """

    try:
        refresh_user_activity_summary(db, concurrently=True)
    except Exception as exc:  # pragma: no cover - defensive
        logger.error(
            "Failed to refresh user activity summary",
            extra={"admin_user_id": int(admin_user.id), "error": str(exc)},
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to refresh user activity summary. Please try again later.",
        ) from exc

    return {
        "message": "User activity summary refresh started.",
        "concurrent": True,
        "refreshed_at": datetime.now(timezone.utc).isoformat(),
    }


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
        to_email="trigpointing@teasel.org",
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
        250,
        ge=1,
        le=250,
        description="Maximum number of results to return (default 250, max 250).",
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

    user_id = int(user.id)

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
            legacy_user_id=user_id,
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
                    "user_id": user_id,
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
                    "user_id": user_id,
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
                    "user_id": user_id,
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
                "user_id": user_id,
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
                "user_id": user_id,
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


@router.get(
    "/trigs/needs-attention/summary",
    response_model=TrigNeedsAttentionSummary,
    openapi_extra=openapi_lifecycle(
        "beta", note="Get summary of trigpoints needing attention (admin only)."
    ),
)
def get_needs_attention_summary(
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigNeedsAttentionSummary:
    """Get summary statistics for trigpoints needing attention."""
    summary = trig_crud.get_needs_attention_summary(db)
    return TrigNeedsAttentionSummary(**summary)


@router.get(
    "/trigs/needs-attention",
    response_model=dict,
    openapi_extra=openapi_lifecycle(
        "beta", note="List trigpoints needing attention (admin only)."
    ),
)
def list_trigs_needing_attention(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of records"),
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    """List trigpoints flagged as needing attention with pagination."""
    trigs = trig_crud.get_trigs_needing_attention(db, skip=skip, limit=limit)
    total = trig_crud.count_trigs_needing_attention(db)

    items = [TrigNeedsAttentionListItem.model_validate(t) for t in trigs]

    has_more = (skip + len(items)) < total
    return {
        "items": items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
    }


@router.get(
    "/trigs/{trig_id}",
    response_model=TrigAdminDetail,
    openapi_extra=openapi_lifecycle(
        "beta", note="Get trigpoint details for admin editing."
    ),
)
def get_trig_for_admin(
    trig_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigAdminDetail:
    """Get full trigpoint details for admin editing."""
    trig = trig_crud.get_trig_by_id(db, trig_id)
    if not trig:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    return TrigAdminDetail.model_validate(trig)


@router.post(
    "/trigs",
    response_model=TrigAdminDetail,
    status_code=status.HTTP_201_CREATED,
    openapi_extra=openapi_lifecycle(
        "beta", note="Create a new trigpoint with admin privileges."
    ),
)
def create_trig_admin(
    create_data: TrigAdminCreate,
    request: Request,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigAdminDetail:
    """
    Create a new trigpoint with admin tracking.

    Creates a new trigpoint record with auto-generated waypoint code.
    Populates creation audit fields (crt_user_id, crt_date, crt_time, crt_ip_addr)
    and admin tracking fields (admin_user_id, admin_timestamp, admin_ip_addr).

    The waypoint is auto-generated as "TP" followed by the next available number.
    County and town fields are set to empty strings (deprecated fields).
    user_added is set to 0 (admin-created trigs are trusted).
    Postcode is auto-computed from WGS84 coordinates (NULL if >5km away).
    """
    from api.utils.ip_address import get_client_ip_normalized

    raw_ip = request.client.host if request.client else "unknown"
    client_ip = get_client_ip_normalized(raw_ip)

    # Auto-generate waypoint
    waypoint = trig_crud.get_next_waypoint(db)

    # Validate type_id if provided
    type_id_value: Optional[int] = create_data.type_id
    if create_data.type_id is not None:
        trig_type = trig_type_crud.get_type_by_id(db, create_data.type_id)
        if not trig_type:
            raise HTTPException(
                status_code=400, detail=f"Invalid type_id: {create_data.type_id}"
            )
        type_id_value = int(trig_type.id)  # type: ignore[arg-type]

    # Auto-set postcode based on WGS coordinates
    postcode_result = location_crud.find_nearest_postcode(
        db,
        float(create_data.wgs_lat),
        float(create_data.wgs_long),
        max_distance_m=5000.0,
    )
    nearest_postcode = postcode_result[0] if postcode_result else None

    # Format timestamp for attention_comment
    timestamp_str = datetime.now(UTC).strftime("%d %b %Y %H:%M:%S")
    attention_comment = f"{timestamp_str} - {admin_user.name} - {admin_user.email} - CREATED: {create_data.admin_comment}"

    # Prepare trig data
    trig_data: dict = {
        "name": create_data.name,
        "fb_number": create_data.fb_number or "",
        "stn_number": create_data.stn_number or "",
        "stn_number_active": create_data.stn_number_active or "",
        "stn_number_passive": create_data.stn_number_passive or "",
        "stn_number_osgb36": create_data.stn_number_osgb36 or "",
        "status_id": create_data.status_id,
        "type_id": type_id_value,
        "current_use": create_data.current_use or "none",
        "historic_use": create_data.historic_use or "none",
        "condition": create_data.condition or "G",
        "wgs_lat": create_data.wgs_lat,
        "wgs_long": create_data.wgs_long,
        "wgs_height": create_data.wgs_height,
        "osgb_eastings": create_data.osgb_eastings,
        "osgb_northings": create_data.osgb_northings,
        "osgb_gridref": create_data.osgb_gridref or "",
        "osgb_height": create_data.osgb_height,
        "postcode": nearest_postcode,
        "attention_comment": attention_comment,
        "legal_message": create_data.legal_message,
    }

    # Set PostGIS location from WGS84 coordinates (PostgreSQL only)
    if db.bind and db.bind.dialect.name != "sqlite":  # type: ignore[union-attr]
        from geoalchemy2.functions import ST_MakePoint, ST_SetSRID

        trig_data["location"] = ST_SetSRID(
            ST_MakePoint(float(create_data.wgs_long), float(create_data.wgs_lat)), 4326
        )

    # Create the trigpoint
    new_trig = trig_crud.create_trig_admin(
        db, waypoint, int(admin_user.id), client_ip, trig_data
    )

    # Invalidate export caches (new trig added)
    invalidate_patterns(["trigs:*:export*"])

    logger.info(
        json.dumps(
            {
                "event": "admin_trig_create",
                "trig_id": int(new_trig.id),
                "waypoint": waypoint,
                "admin_user_id": int(admin_user.id),
                "name": create_data.name,
            }
        )
    )

    return TrigAdminDetail.model_validate(new_trig)


@router.patch(
    "/trigs/{trig_id}",
    response_model=TrigAdminDetail,
    openapi_extra=openapi_lifecycle(
        "beta", note="Update trigpoint with admin privileges."
    ),
)
def update_trig_admin(
    trig_id: int,
    update_data: TrigAdminUpdate,
    request: Request,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> TrigAdminDetail:
    """
    Update trigpoint with admin tracking.

    Updates the trigpoint record and populates admin tracking fields
    (admin_user_id, admin_timestamp, admin_ip_addr) on the trig table.

    Handles three action types:
    - 'solved': Set needs_attention to 0 (problem resolved)
    - 'revisit': Keep needs_attention as-is (leave for later)
    - 'cant_fix': Increment needs_attention (escalate issue)

    Automatically sets postcode based on WGS84 coordinates (NULL if >5km away).
    Appends admin comment to attention_comment history.
    """
    trig = trig_crud.get_trig_by_id(db, trig_id)
    if not trig:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Get client IP address (normalized for varchar(15) storage)
    from api.utils.ip_address import get_client_ip_normalized

    raw_ip = request.client.host if request.client else "unknown"
    client_ip = get_client_ip_normalized(raw_ip)

    # Auto-set postcode based on WGS coordinates
    # Set to nearest postcode if within 5km, otherwise NULL
    postcode_result = location_crud.find_nearest_postcode(
        db,
        float(update_data.wgs_lat),
        float(update_data.wgs_long),
        max_distance_m=5000.0,
    )
    nearest_postcode = postcode_result[0] if postcode_result else None

    # Determine needs_attention value based on action
    if update_data.action == "solved":
        needs_attention_value = 0
    elif update_data.action == "cant_fix":
        needs_attention_value = int(trig.needs_attention) + 1
    else:  # revisit
        needs_attention_value = int(trig.needs_attention)

    # Format timestamp in the legacy format: DD MMM YYYY HH:MM:SS
    timestamp_str = datetime.now(UTC).strftime("%d %b %Y %H:%M:%S")

    # Append admin comment to attention_comment
    new_comment = f"{timestamp_str} - {admin_user.name} - {admin_user.email} - {update_data.admin_comment}"
    updated_attention_comment = (
        f"{new_comment}\n\n{trig.attention_comment}"
        if trig.attention_comment
        else new_comment
    )

    # Validate type_id if provided
    type_id_value: Optional[int] = update_data.type_id

    if update_data.type_id is not None:
        trig_type = trig_type_crud.get_type_by_id(db, update_data.type_id)
        if not trig_type:
            raise HTTPException(
                status_code=400, detail=f"Invalid type_id: {update_data.type_id}"
            )
        type_id_value = int(trig_type.id)  # type: ignore[arg-type]

    # Prepare updates dictionary - convert None to empty string for text fields
    updates: dict = {
        "name": update_data.name,
        "fb_number": update_data.fb_number or "",
        "stn_number": update_data.stn_number or "",
        "stn_number_active": update_data.stn_number_active or "",
        "stn_number_passive": update_data.stn_number_passive or "",
        "stn_number_osgb36": update_data.stn_number_osgb36 or "",
        "status_id": update_data.status_id,
        "type_id": type_id_value,
        "current_use": update_data.current_use or "none",
        "historic_use": update_data.historic_use or "none",
        "condition": update_data.condition or "G",
        "wgs_lat": update_data.wgs_lat,
        "wgs_long": update_data.wgs_long,
        "wgs_height": update_data.wgs_height,
        "osgb_eastings": update_data.osgb_eastings,
        "osgb_northings": update_data.osgb_northings,
        "osgb_gridref": update_data.osgb_gridref or "",
        "osgb_height": update_data.osgb_height,
        "postcode": nearest_postcode,  # NULL if no postcode within 5km
        "needs_attention": needs_attention_value,
        "attention_comment": updated_attention_comment,
        "legal_message": update_data.legal_message,  # NULL clears the message
        # Note: original_* fields are read-only and not updatable via API
    }

    # Update PostGIS location from WGS84 coordinates (PostgreSQL only)
    # Note: ST_MakePoint takes (x, y) = (lon, lat)
    if db.bind and db.bind.dialect.name != "sqlite":  # type: ignore[union-attr]
        from geoalchemy2.functions import ST_MakePoint, ST_SetSRID

        updates["location"] = ST_SetSRID(
            ST_MakePoint(float(update_data.wgs_long), float(update_data.wgs_lat)), 4326
        )

    # Update with admin tracking (stores admin_* fields on trig table)
    updated_trig = trig_crud.update_trig_admin(
        db, trig_id, int(admin_user.id), client_ip, updates
    )

    if not updated_trig:
        raise HTTPException(status_code=500, detail="Failed to update trigpoint")

    # Invalidate caches for the updated trigpoint
    invalidate_trig_caches(trig_id)

    logger.info(
        json.dumps(
            {
                "event": "admin_trig_update",
                "trig_id": trig_id,
                "admin_user_id": int(admin_user.id),
                "action": update_data.action,
                "needs_attention": needs_attention_value,
            }
        )
    )

    return TrigAdminDetail.model_validate(updated_trig)


@router.post(
    "/trigs/{trig_id}/move-to-log/{log_id}",
    response_model=TrigAdminDetail,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Move a trigpoint's location to match a log's location and set condition to 'M'.",
    ),
)
def move_trig_to_log_location(
    trig_id: int,
    log_id: int,
    request: Request,
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
    db: Session = Depends(get_db),
) -> TrigAdminDetail:
    """
    Move a trigpoint's location to match a log's location.

    This endpoint:
    - Copies the log's OSGB coordinates to the trig's wgs_*, osgb_*, and location fields
    - Converts OSGB to WGS84 for the wgs_* fields
    - Sets the trig's condition to 'M' (Moved)
    - Appends a note to attention_comment history
    - Does NOT modify needs_attention flag

    Requires `api:admin` scope.
    """
    from api.services.coordinate_service import convert_osgb_to_wgs84

    # Get the trig
    trig = trig_crud.get_trig_by_id(db, trig_id)
    if not trig:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Get the log
    log = tlog_crud.get_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    # Verify the log belongs to this trig
    if log.trig_id != trig_id:
        raise HTTPException(
            status_code=400,
            detail=f"Log {log_id} does not belong to trig {trig_id}",
        )

    # Check the log has location data
    if log.osgb_eastings is None or log.osgb_northings is None:
        raise HTTPException(
            status_code=400,
            detail="Log does not have location coordinates",
        )

    # Get client IP address
    from api.utils.ip_address import get_client_ip_normalized

    raw_ip = request.client.host if request.client else "unknown"
    client_ip = get_client_ip_normalized(raw_ip)

    # Convert log's OSGB to WGS84 using OSTN15 for accuracy
    wgs_long, wgs_lat, _ = convert_osgb_to_wgs84(
        float(log.osgb_eastings), float(log.osgb_northings)
    )

    # Format timestamp for attention_comment
    timestamp_str = datetime.now(UTC).strftime("%d %b %Y %H:%M:%S")
    new_comment = (
        f"{timestamp_str} - {admin_user.name} - {admin_user.email} - "
        f"MOVED: Location updated from log #{log_id} ({log.osgb_gridref})"
    )
    updated_attention_comment = (
        f"{new_comment}\n\n{trig.attention_comment}"
        if trig.attention_comment
        else new_comment
    )

    # Auto-set postcode based on new coordinates
    postcode_result = location_crud.find_nearest_postcode(
        db, wgs_lat, wgs_long, max_distance_m=5000.0
    )
    nearest_postcode = postcode_result[0] if postcode_result else None

    # Prepare updates
    updates: dict = {
        "wgs_lat": wgs_lat,
        "wgs_long": wgs_long,
        "osgb_eastings": log.osgb_eastings,
        "osgb_northings": log.osgb_northings,
        "osgb_gridref": log.osgb_gridref or "",
        "condition": "M",
        "postcode": nearest_postcode,
        "attention_comment": updated_attention_comment,
    }

    # Update PostGIS location (PostgreSQL only)
    if db.bind and db.bind.dialect.name != "sqlite":  # type: ignore[union-attr]
        from geoalchemy2.functions import ST_MakePoint, ST_SetSRID

        updates["location"] = ST_SetSRID(ST_MakePoint(wgs_long, wgs_lat), 4326)

    # Update with admin tracking
    updated_trig = trig_crud.update_trig_admin(
        db, trig_id, int(admin_user.id), client_ip, updates
    )

    if not updated_trig:
        raise HTTPException(status_code=500, detail="Failed to update trigpoint")

    # Invalidate caches
    invalidate_trig_caches(trig_id)

    logger.info(
        json.dumps(
            {
                "event": "admin_move_trig_to_log",
                "trig_id": trig_id,
                "log_id": log_id,
                "admin_user_id": int(admin_user.id),
                "new_gridref": log.osgb_gridref,
            }
        )
    )

    return TrigAdminDetail.model_validate(updated_trig)


@router.post(
    "/trigs/{trig_id}/set-condition-from-log/{log_id}",
    response_model=TrigAdminDetail,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Set a trigpoint's condition to match a log's condition.",
    ),
)
def set_trig_condition_from_log(
    trig_id: int,
    log_id: int,
    request: Request,
    admin_user: User = Depends(ADMIN_SCOPE_DEPENDENCY),
    db: Session = Depends(get_db),
) -> TrigAdminDetail:
    """
    Set a trigpoint's condition to match a log's condition.

    This endpoint:
    - Copies the log's condition code to the trig's condition field
    - Appends a note to attention_comment history
    - Does NOT modify needs_attention flag

    Requires `api:admin` scope.
    """
    # Get the trig
    trig = trig_crud.get_trig_by_id(db, trig_id)
    if not trig:
        raise HTTPException(status_code=404, detail="Trigpoint not found")

    # Get the log
    log = tlog_crud.get_log_by_id(db, log_id)
    if not log:
        raise HTTPException(status_code=404, detail="Log not found")

    # Verify the log belongs to this trig
    if log.trig_id != trig_id:
        raise HTTPException(
            status_code=400,
            detail=f"Log {log_id} does not belong to trig {trig_id}",
        )

    # Check the log has a condition
    if not log.condition:
        raise HTTPException(
            status_code=400,
            detail="Log does not have a condition set",
        )

    # Get client IP address
    from api.utils.ip_address import get_client_ip_normalized

    raw_ip = request.client.host if request.client else "unknown"
    client_ip = get_client_ip_normalized(raw_ip)

    # Format timestamp for attention_comment
    timestamp_str = datetime.now(UTC).strftime("%d %b %Y %H:%M:%S")
    new_comment = (
        f"{timestamp_str} - {admin_user.name} - {admin_user.email} - "
        f"CONDITION: Updated from log #{log_id} ('{trig.condition}' -> '{log.condition}')"
    )
    updated_attention_comment = (
        f"{new_comment}\n\n{trig.attention_comment}"
        if trig.attention_comment
        else new_comment
    )

    # Prepare updates
    updates: dict = {
        "condition": log.condition,
        "attention_comment": updated_attention_comment,
    }

    # Update with admin tracking
    updated_trig = trig_crud.update_trig_admin(
        db, trig_id, int(admin_user.id), client_ip, updates
    )

    if not updated_trig:
        raise HTTPException(status_code=500, detail="Failed to update trigpoint")

    # Invalidate caches
    invalidate_trig_caches(trig_id)

    logger.info(
        json.dumps(
            {
                "event": "admin_set_trig_condition_from_log",
                "trig_id": trig_id,
                "log_id": log_id,
                "admin_user_id": int(admin_user.id),
                "old_condition": trig.condition,
                "new_condition": log.condition,
            }
        )
    )

    return TrigAdminDetail.model_validate(updated_trig)


@router.get(
    "/statuses",
    response_model=list[StatusResponse],
    openapi_extra=openapi_lifecycle(
        "beta", note="Get all status records for admin dropdowns."
    ),
)
def get_all_statuses(
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> list[StatusResponse]:
    """Get all status records for dropdown population."""
    statuses = status_crud.get_all_statuses(db)
    return [StatusResponse.model_validate(s) for s in statuses]


@router.post(
    "/merge-users",
    response_model=AdminMergeUsersPreview | AdminMergeUsersResponse,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Merge source user into target user (admin only). Supports dry-run preview.",
    ),
)
def merge_users_admin(
    request: AdminMergeUsersRequest,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> AdminMergeUsersPreview | AdminMergeUsersResponse:
    """
    Merge source user into target user.

    This endpoint allows manual user merging where the admin explicitly selects
    both the target (to keep) and source (to delete) users.

    Dry-run mode (default):
    - Returns preview of changes without executing
    - Shows which records will be updated
    - Shows which profile fields will be copied
    - Indicates if Auth0 will be synchronized

    Execute mode (dry_run=false):
    - Updates all source user's logs (tlog) to target user
    - Updates all source user's photo votes (tphotovote) to target user
    - Copies blank profile fields from source to target
    - If auth0_user_id was copied, synchronizes Auth0 user
    - Deletes source user

    Requires `api:admin` scope.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_merge_users_requested",
                "admin_user_id": int(admin_user.id),
                "target_user_id": request.target_user_id,
                "source_user_id": request.source_user_id,
                "dry_run": request.dry_run,
            }
        )
    )

    # Validate users exist and are different
    if request.target_user_id == request.source_user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Target and source users must be different",
        )

    target_user = user_crud.get_user_by_id(db, request.target_user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target user {request.target_user_id} not found",
        )

    source_user = user_crud.get_user_by_id(db, request.source_user_id)
    if not source_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source user {request.source_user_id} not found",
        )

    # Call CRUD function
    try:
        result = user_merge_crud.merge_users_admin(
            db,
            target_user_id=request.target_user_id,
            source_user_id=request.source_user_id,
            dry_run=request.dry_run,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            json.dumps(
                {
                    "event": "admin_merge_users_error",
                    "admin_user_id": int(admin_user.id),
                    "target_user_id": request.target_user_id,
                    "source_user_id": request.source_user_id,
                    "error": str(e),
                }
            ),
            exc_info=True,
        )
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Merge failed: {str(e)}",
        )

    # If dry run, return preview
    if request.dry_run:
        preview = AdminMergeUsersPreview(
            dry_run=True,
            target_user=result["target_user"],
            source_user=result["source_user"],
            estimated_records=MergeRecordCounts(**result["estimated_records"]),
            profile_updates=result["profile_updates"],
            auth0_will_update=result["auth0_will_update"],
            member_since=result["member_since"],
        )

        logger.info(
            json.dumps(
                {
                    "event": "admin_merge_users_preview_generated",
                    "admin_user_id": int(admin_user.id),
                    "target_user_id": request.target_user_id,
                    "source_user_id": request.source_user_id,
                    "auth0_will_update": result["auth0_will_update"],
                }
            )
        )

        return preview

    # Execute mode - handle Auth0 synchronization if needed
    auth0_updated = False
    if result.get("auth0_transferred"):
        try:
            # Refresh target user from db to get updated auth0_user_id
            db.refresh(target_user)

            if target_user.auth0_user_id:
                auth0_user_id = str(target_user.auth0_user_id)

                # Get Auth0 user to fetch email
                auth0_user = auth0_service.find_user_by_auth0_id(auth0_user_id)

                if auth0_user:
                    # Update Auth0 user profile
                    auth0_service.update_user_profile(
                        auth0_user_id, nickname=str(target_user.name)
                    )

                    # Update app_metadata with target user ID
                    auth0_service.update_user_app_metadata(
                        auth0_user_id, {"database_user_id": int(target_user.id)}
                    )

                    # Get email from Auth0 and update target user
                    auth0_email = auth0_user.get("email")
                    if auth0_email:
                        target_user.email = auth0_email  # type: ignore
                        db.add(target_user)
                        db.commit()

                    auth0_updated = True

                    logger.info(
                        json.dumps(
                            {
                                "event": "admin_merge_users_auth0_updated",
                                "admin_user_id": int(admin_user.id),
                                "target_user_id": request.target_user_id,
                                "auth0_user_id": auth0_user_id,
                            }
                        )
                    )
                else:
                    logger.warning(
                        json.dumps(
                            {
                                "event": "admin_merge_users_auth0_user_not_found",
                                "admin_user_id": int(admin_user.id),
                                "target_user_id": request.target_user_id,
                                "auth0_user_id": auth0_user_id,
                            }
                        )
                    )
        except Exception as e:
            logger.error(
                json.dumps(
                    {
                        "event": "admin_merge_users_auth0_sync_failed",
                        "admin_user_id": int(admin_user.id),
                        "target_user_id": request.target_user_id,
                        "error": str(e),
                    }
                ),
                exc_info=True,
            )
            # Don't fail the whole merge if Auth0 sync fails

    # Invalidate user caches
    invalidate_user_caches(user_id=request.target_user_id)
    invalidate_user_caches(user_id=request.source_user_id)

    response = AdminMergeUsersResponse(
        success=True,
        target_user_id=result["target_user_id"],
        source_user_id=result["source_user_id"],
        updated_records=MergeRecordCounts(**result["updated_records"]),
        profile_updated=result["profile_updated"],
        auth0_updated=auth0_updated,
    )

    logger.info(
        json.dumps(
            {
                "event": "admin_merge_users_completed",
                "admin_user_id": int(admin_user.id),
                "target_user_id": request.target_user_id,
                "source_user_id": request.source_user_id,
                "auth0_updated": auth0_updated,
                "profile_updated": result["profile_updated"],
            }
        )
    )

    return response


# ============================================================================
# Logs Needing Attention
# ============================================================================


@router.get(
    "/logs/needs-attention/summary",
    response_model=LogNeedsAttentionSummary,
    openapi_extra=openapi_lifecycle(
        "beta", note="Get summary of logs needing attention (admin only)."
    ),
)
def get_logs_needs_attention_summary(
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> LogNeedsAttentionSummary:
    """
    Get summary statistics for logs needing attention.

    Returns counts for:
    - Orphaned logs: logs referencing deleted trigpoints
    - Duplicate logs: identical logs (same user, trig, date, time, comment) with no photos
    """
    summary = tlog_crud.get_logs_needing_attention_summary(db)
    return LogNeedsAttentionSummary(**summary)


@router.get(
    "/logs/needs-attention",
    response_model=LogNeedsAttentionListResponse,
    openapi_extra=openapi_lifecycle(
        "beta", note="List logs needing attention (admin only)."
    ),
)
def list_logs_needing_attention(
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(50, ge=1, le=200, description="Maximum number of records"),
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
) -> LogNeedsAttentionListResponse:
    """
    List logs needing attention with pagination.

    Returns two types of logs:
    - Orphaned: logs referencing deleted trigpoints
    - Duplicates: identical logs with no photos attached

    Logs are sorted by date (newest first) and interleaved.
    """
    # Fetch enough rows from each category to cover the requested page after interleaving.
    fetch_limit = max(limit * 2, (skip + limit) * 2)

    # Fetch orphaned logs
    orphaned_raw = tlog_crud.get_orphaned_logs(db, skip=0, limit=fetch_limit)
    orphaned_items = [
        OrphanedLogItem(
            id=int(log.id),
            trig_id=int(log.trig_id) if log.trig_id else None,
            user_id=int(log.user_id) if log.user_id else None,
            user_name=user_name,
            date=log.date if log.date else None,  # type: ignore[arg-type]
            time=log.time if log.time else None,  # type: ignore[arg-type]
            condition=str(log.condition) if log.condition else None,
            comment=str(log.comment) if log.comment else None,
            score=int(log.score) if log.score else None,
            issue_type="orphaned",
        )
        for log, user_name in orphaned_raw
    ]

    # Fetch duplicate logs
    duplicate_groups_raw = tlog_crud.get_duplicate_log_groups(
        db, skip=0, limit=fetch_limit * 10
    )
    duplicate_items: list[DuplicateLogGroupItem] = []
    for group in duplicate_groups_raw:
        logs = [
            DuplicateLogGroupEntry(
                id=int(log.id),
                time=log.time if log.time else None,  # type: ignore[arg-type]
                condition=str(log.condition) if log.condition else None,
                comment=str(log.comment) if log.comment else None,
                score=int(log.score) if log.score else None,
            )
            for log in group["logs"]
        ]
        # Only include groups that still have 2+ logs (defensive; should already be true)
        if len(logs) < 2:
            continue
        duplicate_items.append(
            DuplicateLogGroupItem(
                trig_id=group["trig_id"],
                trig_name=group["trig_name"],
                trig_waypoint=group["trig_waypoint"],
                user_id=group["user_id"],
                user_name=group["user_name"],
                date=group["date"] if group["date"] else None,
                duplicate_count=int(group["duplicate_count"]),
                logs=logs,
                issue_type="duplicate",
            )
        )

    # Combine and sort by date (newest first)
    all_items: list[OrphanedLogItem | DuplicateLogGroupItem] = (
        orphaned_items + duplicate_items
    )

    def sort_key(item: OrphanedLogItem | DuplicateLogGroupItem):
        def date_key(value):
            return value.isoformat() if value else ""

        def time_key(value):
            return value.isoformat() if value else ""

        if isinstance(item, OrphanedLogItem):
            return (date_key(item.date), time_key(item.time), item.id)

        # Duplicate groups: use date + latest time/id in the group for ordering
        latest_time = ""
        latest_id = 0
        if item.logs:
            latest_time = time_key(item.logs[0].time)
            latest_id = int(item.logs[0].id)
        return (date_key(item.date), latest_time, latest_id)

    all_items.sort(key=sort_key, reverse=True)

    # Apply pagination
    paginated_items = all_items[skip : skip + limit]

    total = len(all_items)
    has_more = (skip + len(paginated_items)) < total

    return LogNeedsAttentionListResponse(
        items=paginated_items,
        pagination={
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
    )


@router.delete(
    "/logs/{log_id}/orphaned",
    openapi_extra=openapi_lifecycle(
        "beta", note="Delete an orphaned log (admin only)."
    ),
)
def delete_orphaned_log_endpoint(
    log_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    """
    Delete an orphaned log (log referencing a deleted trigpoint).

    Verifies the log is actually orphaned before deletion.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_delete_orphaned_log_attempt",
                "admin_user_id": int(admin_user.id),
                "log_id": log_id,
            }
        )
    )

    success = tlog_crud.delete_orphaned_log(db, log_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found or is not orphaned",
        )

    logger.info(
        json.dumps(
            {
                "event": "admin_delete_orphaned_log_success",
                "admin_user_id": int(admin_user.id),
                "log_id": log_id,
            }
        )
    )

    return {"success": True, "message": f"Orphaned log {log_id} deleted"}


@router.delete(
    "/logs/{log_id}/duplicate",
    openapi_extra=openapi_lifecycle(
        "beta", note="Delete a duplicate log (admin only)."
    ),
)
def delete_duplicate_log_endpoint(
    log_id: int,
    admin_user: User = Depends(require_admin()),
    db: Session = Depends(get_db),
):
    """
    Delete a duplicate log entry.

    Verifies that this log is part of a duplicate set and has no photos
    before deletion.
    """
    logger.info(
        json.dumps(
            {
                "event": "admin_delete_duplicate_log_attempt",
                "admin_user_id": int(admin_user.id),
                "log_id": log_id,
            }
        )
    )

    success = tlog_crud.delete_duplicate_log(db, log_id)

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Log not found, has photos, or is not a duplicate",
        )

    logger.info(
        json.dumps(
            {
                "event": "admin_delete_duplicate_log_success",
                "admin_user_id": int(admin_user.id),
                "log_id": log_id,
            }
        )
    )

    return {"success": True, "message": f"Duplicate log {log_id} deleted"}
