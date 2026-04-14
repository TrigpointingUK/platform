"""
User endpoints with permission-based field filtering.
"""

import base64
import io
import json
import os
import time
from datetime import UTC
from datetime import date as date_type
from datetime import datetime, timedelta
from typing import Any, Dict, Mapping, Optional, Union

import numpy as np
import sqlalchemy as sa
from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPBearer
from PIL import Image, ImageChops, ImageDraw, ImageFilter
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from api.api.deps import (
    get_current_user,
    get_db,
    verify_webhook_auth,
)
from api.api.lifecycle import openapi_lifecycle
from api.crud import area as area_crud
from api.crud import tlog as tlog_crud
from api.crud import tphoto as tphoto_crud
from api.crud import user as user_crud
from api.models.condition import Condition
from api.models.server import Server
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.trig_type import TrigCategory, TrigType
from api.models.user import TLog, User
from api.schemas.area import (
    AreaCountItem,
    AreaTypeResponse,
    UserAreaBreakdownResponse,
)
from api.schemas.tphoto import TPhotoResponse
from api.schemas.user import (
    CategoryTypeBreakdown,
    SortDirection,
    TypeCount,
    UserBreakdown,
    UserCreate,
    UserCreateResponse,
    UserListFilters,
    UserListItem,
    UserListResponse,
    UserPrefs,
    UserResponse,
    UserSortField,
    UserStats,
    UserUpdate,
    UserWithIncludes,
)
from api.services.badge_service import BadgeService
from api.utils.cache_decorator import cached
from api.utils.condition_mapping import get_condition_counts_by_description
from api.utils.geocalibrate import CalibrationResult
from api.utils.url import join_url

# from api.core.security import auth0_validator


router = APIRouter()
security = HTTPBearer(auto_error=False)


_DEFAULT_JOINED_DATE = date_type(1900, 1, 1)

USER_ACTIVITY_SUMMARY = sa.table(
    "user_activity_summary",
    sa.column("user_id", sa.Integer),
    sa.column("member_since", sa.Date),
    sa.column("total_logs", sa.Integer),
    sa.column("total_trigs_logged", sa.Integer),
    sa.column("total_photos", sa.Integer),
)


def _encode_cursor_value(value: Any) -> Any:
    if isinstance(value, (date_type, datetime)):
        return value.isoformat()
    return value


def _encode_cursor_token(
    sort_value: Any, user_id: int, sort: UserSortField, direction: SortDirection
) -> str:
    payload = {
        "sort_value": _encode_cursor_value(sort_value),
        "user_id": user_id,
        "sort": sort.value,
        "direction": direction.value,
    }
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("utf-8")


def _decode_cursor_token(cursor: str) -> dict[str, Any]:
    try:
        decoded = base64.urlsafe_b64decode(cursor.encode("utf-8")).decode("utf-8")
        data = json.loads(decoded)
        if not isinstance(data, dict):
            raise ValueError("Cursor payload must be an object")
        return data
    except Exception as exc:  # pragma: no cover - defensive branch
        raise HTTPException(status_code=400, detail="Invalid cursor token") from exc


def _coerce_cursor_value(sort_field: UserSortField, raw_value: Any) -> Any:
    if sort_field == UserSortField.JOINED:
        if not raw_value:
            return _DEFAULT_JOINED_DATE
        try:
            return date_type.fromisoformat(str(raw_value))
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Invalid cursor value") from exc
    if sort_field in {UserSortField.TRIGPOINTS, UserSortField.PHOTOS}:
        return int(raw_value or 0)
    if sort_field == UserSortField.NAME:
        return str(raw_value or "")
    # Fallback for future enum entries
    return raw_value


@router.post(
    "",
    response_model=UserCreateResponse,
    status_code=201,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Create a new user from Auth0 webhook. Requires M2M token or shared secret authentication.",
    ),
)
def create_user_from_auth0(
    user_data: UserCreate,
    token_payload: dict = Depends(verify_webhook_auth),
    db: Session = Depends(get_db),
) -> UserCreateResponse:
    """
    Create a new user in the legacy database.

    This endpoint is called by Auth0 Post User Registration Action.
    Requires M2M authentication with Management API token.

    Receives:
    - username (nickname from Auth0)
    - email (from Auth0)
    - auth0_user_id

    Firstname and surname remain empty until user updates profile.
    Sets cryptpw to random string for legacy cookie compatibility.

    Returns:
        UserCreateResponse: Created user with id, name, email, auth0_user_id
    """
    from api.core.logging import get_logger

    logger = get_logger(__name__)

    logger.info(
        "User creation request from Auth0",
        extra={
            "username": user_data.username,
            "email": user_data.email,
            "auth0_user_id": user_data.auth0_user_id,
        },
    )

    try:
        # Create user using CRUD function
        new_user = user_crud.create_user(
            db=db,
            username=user_data.username,
            email=user_data.email,
            auth0_user_id=user_data.auth0_user_id,
        )

        logger.info(
            "User created successfully",
            extra={
                "user_id": new_user.id,
                "username": new_user.name,
                "email": new_user.email,
            },
        )

        return UserCreateResponse(
            id=int(new_user.id),
            name=str(new_user.name),
            email=str(new_user.email),
            auth0_user_id=str(new_user.auth0_user_id),
        )

    except ValueError as e:
        # Handle uniqueness violations
        error_msg = str(e)
        logger.warning(
            "User creation failed - uniqueness violation",
            extra={
                "error": error_msg,
                "username": user_data.username,
                "email": user_data.email,
            },
        )

        if "username" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail=f"Username '{user_data.username}' already exists",
            )
        elif "email" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail=f"Email '{user_data.email}' already exists",
            )
        elif "auth0" in error_msg.lower():
            raise HTTPException(
                status_code=409,
                detail=f"Auth0 user ID '{user_data.auth0_user_id}' already exists",
            )
        else:
            raise HTTPException(status_code=409, detail=error_msg)

    except Exception as e:
        logger.error(
            "User creation failed - unexpected error",
            extra={
                "error": str(e),
                "error_type": type(e).__name__,
                "username": user_data.username,
                "email": user_data.email,
            },
            exc_info=True,  # Include full traceback
        )
        raise HTTPException(
            status_code=500,
            detail=f"Failed to create user: {str(e)}",
        )


@router.get(
    "/me",
    response_model=UserWithIncludes,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Returns the current authenticated user's profile. Supports include=stats,prefs.",
    ),
)
def get_current_user_profile(
    include: Optional[str] = Query(
        None, description="Comma-separated includes: stats,prefs"
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserWithIncludes:
    """
    Get the current authenticated user's profile.

    - Supports optional includes via the `include` query parameter:
      - stats: adds basic log stats (totals only) for the user
      - breakdown: adds detailed breakdown statistics (requires stats)
      - prefs: adds the user's preferences (always allowed on /me)
    """

    # Create UserResponse with member_since field
    user_response = UserResponse.model_validate(current_user)
    user_response.member_since = current_user.crt_date  # type: ignore
    user_response.auth0_user_id = current_user.auth0_user_id  # type: ignore
    result = UserWithIncludes(**user_response.model_dump())

    # Extract roles from token payload if available
    if hasattr(current_user, "_token_payload"):
        from api.core.config import settings

        token_payload = getattr(current_user, "_token_payload")
        roles_claim = f"{settings.AUTH0_CLAIMS_NAMESPACE}roles"
        roles = token_payload.get(roles_claim, [])
        if isinstance(roles, list):
            result.roles = roles

    if include:
        tokens = {t.strip() for t in include.split(",") if t.strip()}

        # Validate include tokens
        valid_includes = {"stats", "breakdown", "prefs"}
        invalid_tokens = tokens - valid_includes
        if invalid_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
            )

        if "stats" in tokens:
            # Calculate basic stats
            total_logs = (
                db.query(user_crud.TLog)
                .filter(user_crud.TLog.user_id == current_user.id)
                .count()
            )
            total_trigs = (
                db.query(user_crud.TLog.trig_id)
                .filter(user_crud.TLog.user_id == current_user.id)
                .distinct()
                .count()
            )
            total_photos = (
                db.query(TPhoto)
                .join(user_crud.TLog, TPhoto.tlog_id == user_crud.TLog.id)
                .filter(
                    user_crud.TLog.user_id == current_user.id, TPhoto.deleted_ind != "Y"
                )
                .count()
            )

            result.stats = UserStats(
                total_logs=int(total_logs),
                total_trigs_logged=int(total_trigs),
                total_photos=int(total_photos),
            )

        if "breakdown" in tokens:
            # Calculate breakdowns by trig characteristics (distinct trigpoints only)
            by_current_use_raw = (
                db.query(
                    Trig.current_use, func.count(func.distinct(user_crud.TLog.trig_id))
                )
                .join(user_crud.TLog, user_crud.TLog.trig_id == Trig.id)
                .filter(user_crud.TLog.user_id == current_user.id)
                .group_by(Trig.current_use)
                .all()
            )
            by_current_use: Dict[str, int] = {
                str(use): int(count) for use, count in by_current_use_raw
            }

            by_historic_use_raw = (
                db.query(
                    Trig.historic_use, func.count(func.distinct(user_crud.TLog.trig_id))
                )
                .join(user_crud.TLog, user_crud.TLog.trig_id == Trig.id)
                .filter(user_crud.TLog.user_id == current_user.id)
                .group_by(Trig.historic_use)
                .all()
            )
            by_historic_use: Dict[str, int] = {
                str(use): int(count) for use, count in by_historic_use_raw
            }

            # Calculate breakdown by type grouped by category
            by_type_raw = (
                db.query(
                    TrigCategory.code.label("category_code"),
                    TrigCategory.name.label("category_name"),
                    TrigCategory.sort_order.label("sort_order"),
                    TrigType.code.label("type_code"),
                    TrigType.name.label("type_name"),
                    func.count(func.distinct(user_crud.TLog.trig_id)).label(
                        "trig_count"
                    ),
                )
                .select_from(Trig)
                .join(user_crud.TLog, user_crud.TLog.trig_id == Trig.id)
                .join(TrigType, Trig.type_id == TrigType.id)
                .join(TrigCategory, TrigType.category_id == TrigCategory.id)
                .filter(user_crud.TLog.user_id == current_user.id)
                .group_by(
                    TrigCategory.code,
                    TrigCategory.name,
                    TrigCategory.sort_order,
                    TrigType.code,
                    TrigType.name,
                )
                .all()
            )

            # Group by category and build the structured response
            categories_dict: Dict[str, CategoryTypeBreakdown] = {}
            for row in by_type_raw:
                cat_code = str(row.category_code)
                if cat_code not in categories_dict:
                    categories_dict[cat_code] = CategoryTypeBreakdown(
                        category_code=cat_code,
                        category_name=str(row.category_name),
                        sort_order=int(row.sort_order),
                        types=[],
                    )
                categories_dict[cat_code].types.append(
                    TypeCount(
                        type_code=str(row.type_code),
                        type_name=str(row.type_name),
                        count=int(row.trig_count),
                    )
                )

            # Sort types within each category by count descending
            for cat in categories_dict.values():
                cat.types.sort(key=lambda t: t.count, reverse=True)

            # Sort categories by sort_order
            by_type = sorted(categories_dict.values(), key=lambda c: c.sort_order)

            # Calculate breakdown by log condition (all logs counted)
            condition_counts_raw = (
                db.query(user_crud.TLog.condition, func.count(user_crud.TLog.id))
                .filter(user_crud.TLog.user_id == current_user.id)
                .group_by(user_crud.TLog.condition)
                .all()
            )
            condition_counts: Dict[str, int] = {
                str(cond): int(count) for cond, count in condition_counts_raw
            }
            by_condition = get_condition_counts_by_description(condition_counts, db)

            result.breakdown = UserBreakdown(
                by_current_use=by_current_use,
                by_historic_use=by_historic_use,
                by_type=by_type,
                by_condition=by_condition,
            )

        if "prefs" in tokens:
            # Always allowed on /me
            result.prefs = UserPrefs(
                distance_ind=str(current_user.distance_ind),
                public_ind=str(current_user.public_ind),
                email=str(current_user.email),
                email_valid=str(current_user.email_valid),
                archive_frequency=str(current_user.archive_frequency or "N"),
                archive_format=str(current_user.archive_format or "C"),
                ui_prefs=dict(current_user.ui_prefs) if current_user.ui_prefs else {},
            )

    return result


@router.patch(
    "/me",
    response_model=UserWithIncludes,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Update the current authenticated user's profile and preferences. Name and email changes sync to Auth0.",
    ),
)
def update_current_user_profile(
    user_updates: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserWithIncludes:
    """
    Update the current authenticated user's profile and preferences.

    All fields are optional - only provided fields will be updated.

    Special handling for Auth0 sync:
    - name (username/nickname): Syncs to Auth0 nickname field
    - email: Syncs to Auth0 email field (marked as verified)
    - firstname, surname: Database only (not in Auth0)

    Auth0 sync failures are logged but don't fail the database update.
    """
    from api.core.logging import get_logger
    from api.services.auth0_service import auth0_service

    logger = get_logger(__name__)

    # Get update data
    update_data = user_updates.model_dump(exclude_unset=True)

    if not update_data:
        # No updates provided, return current user
        user_response = UserResponse.model_validate(current_user)
        user_response.member_since = current_user.crt_date  # type: ignore
        result = UserWithIncludes(**user_response.model_dump())
        result.prefs = UserPrefs(
            distance_ind=str(current_user.distance_ind),
            public_ind=str(current_user.public_ind),
            email=str(current_user.email),
            email_valid=str(current_user.email_valid),
            archive_frequency=str(current_user.archive_frequency or "N"),
            archive_format=str(current_user.archive_format or "C"),
            ui_prefs=dict(current_user.ui_prefs) if current_user.ui_prefs else {},
        )
        return result

    # Check for fields that need Auth0 sync
    name_changed = "name" in update_data and update_data["name"] != current_user.name
    email_changed = (
        "email" in update_data and update_data["email"] != current_user.email
    )

    # Validate uniqueness for name and email changes
    if name_changed:
        new_name = update_data["name"]
        existing_user = user_crud.get_user_by_name(db, new_name)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409,
                detail=f"Username '{new_name}' is already taken",
            )

    if email_changed:
        new_email = update_data["email"]
        existing_user = user_crud.get_user_by_email(db, new_email)
        if existing_user and existing_user.id != current_user.id:
            raise HTTPException(
                status_code=409,
                detail=f"Email '{new_email}' is already in use",
            )

    # Handle ui_prefs merge (merge with existing rather than replace)
    if "ui_prefs" in update_data:
        existing_ui_prefs: dict = current_user.ui_prefs or {}  # type: ignore[assignment]
        new_ui_prefs: dict = update_data.pop("ui_prefs") or {}
        # Merge: new values override existing
        merged_ui_prefs = {**existing_ui_prefs, **new_ui_prefs}
        current_user.ui_prefs = merged_ui_prefs  # type: ignore[assignment]

    # Update database fields
    for field, value in update_data.items():
        setattr(current_user, field, value)

    # If email is changing, mark as unvalidated until Auth0 sync succeeds
    if email_changed:
        current_user.email_valid = "N"  # type: ignore

    try:
        db.commit()
        db.refresh(current_user)
        logger.info(
            "User profile updated in database",
            extra={
                "user_id": current_user.id,
                "updated_fields": list(update_data.keys()),
            },
        )
    except Exception as e:
        db.rollback()
        logger.error(
            "Database update failed",
            extra={"user_id": current_user.id, "error": str(e)},
        )
        raise HTTPException(status_code=500, detail=f"Failed to update user: {str(e)}")

    # Sync to Auth0 if needed (only if user has auth0_user_id)
    if current_user.auth0_user_id:
        try:
            if name_changed:
                logger.info(
                    "Syncing username change to Auth0",
                    extra={
                        "user_id": current_user.id,
                        "auth0_user_id": current_user.auth0_user_id,
                        "new_name": current_user.name,
                    },
                )
                success = auth0_service.update_user_profile(
                    user_id=str(current_user.auth0_user_id),
                    nickname=str(current_user.name),
                )
                if not success:
                    logger.error(
                        json.dumps(
                            {
                                "event": "auth0_username_sync_failed",
                                "user_id": current_user.id,
                                "auth0_user_id": current_user.auth0_user_id,
                                "new_username": current_user.name,
                                "timestamp": datetime.now(UTC).isoformat() + "Z",
                                "action_required": "admin_review",
                            }
                        )
                    )

            if email_changed:
                logger.info(
                    "Syncing email change to Auth0",
                    extra={
                        "user_id": current_user.id,
                        "auth0_user_id": current_user.auth0_user_id,
                        "new_email": current_user.email,
                    },
                )
                success = auth0_service.update_user_email(
                    user_id=str(current_user.auth0_user_id),
                    email=str(current_user.email),
                )
                if success:
                    # Update email_valid to 'Y' on successful sync
                    current_user.email_valid = "Y"  # type: ignore
                    db.commit()
                    db.refresh(current_user)
                    logger.info(
                        "Auth0 email sync successful",
                        extra={
                            "user_id": current_user.id,
                            "auth0_user_id": current_user.auth0_user_id,
                        },
                    )
                else:
                    # Email stays as 'N' - batch job can retry later
                    logger.error(
                        json.dumps(
                            {
                                "event": "auth0_email_sync_failed",
                                "user_id": current_user.id,
                                "auth0_user_id": current_user.auth0_user_id,
                                "email": current_user.email,
                                "timestamp": datetime.now(UTC).isoformat() + "Z",
                                "action_required": "batch_retry_or_manual_sync",
                            }
                        )
                    )

        except Exception as e:
            # Log Auth0 sync failure but don't fail the request
            logger.error(
                "Auth0 sync failed (database updated successfully)",
                extra={
                    "user_id": current_user.id,
                    "auth0_user_id": current_user.auth0_user_id,
                    "error": str(e),
                },
            )
    else:
        if name_changed or email_changed:
            logger.info(
                "Skipping Auth0 sync - user has no auth0_user_id",
                extra={"user_id": current_user.id},
            )

    # Return updated user data with prefs
    user_response = UserResponse.model_validate(current_user)
    user_response.member_since = current_user.crt_date  # type: ignore
    result = UserWithIncludes(**user_response.model_dump())

    # Always include prefs in PATCH response since they might have been updated
    result.prefs = UserPrefs(
        distance_ind=str(current_user.distance_ind),
        public_ind=str(current_user.public_ind),
        email=str(current_user.email),
        email_valid=str(current_user.email_valid),
        archive_frequency=str(current_user.archive_frequency or "N"),
        archive_format=str(current_user.archive_format or "C"),
        ui_prefs=dict(current_user.ui_prefs) if current_user.ui_prefs else {},
    )

    return result


@router.post(
    "/me/archive",
    status_code=202,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Immediately generate and send a data archive email to the current user. "
        "Non-admin users limited to once per 24 hours.",
    ),
)
def send_archive_now(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Immediately generate and email a data archive to the authenticated user.

    Rate limited to once per 24 hours for non-admin users.
    Admin users (api:admin scope) are exempt from the rate limit.
    """
    from api.core.config import settings
    from api.core.logging import get_logger
    from api.core.metrics import get_metrics_collector
    from api.models.user import UserArchive
    from api.services.archive_service import generate_archive_zip
    from api.services.email_service import email_service

    logger = get_logger(__name__)
    mc = get_metrics_collector()

    user_id = int(current_user.id)
    username = str(current_user.name or f"user_{user_id}")
    email_addr = str(current_user.email or "")

    if not email_addr or email_addr.strip() == "":
        raise HTTPException(
            status_code=400,
            detail="No email address on your account. Update your email in settings first.",
        )

    # Rate limit: once per 24h unless admin
    token_payload = getattr(current_user, "_token_payload", None)
    is_admin = False
    if token_payload:
        from api.api.deps import has_scope

        is_admin = has_scope(token_payload, "api:admin")

    if not is_admin:
        cutoff = datetime.now(UTC) - timedelta(hours=24)
        recent = (
            db.query(UserArchive)
            .filter(
                UserArchive.user_id == user_id,
                UserArchive.status == "S",
                UserArchive.created_at >= cutoff,
            )
            .first()
        )
        if recent:
            raise HTTPException(
                status_code=429,
                detail="Archive already sent in the last 24 hours. Try again later.",
            )

    archive_format = str(current_user.archive_format or "C")

    try:
        zip_bytes = generate_archive_zip(db, current_user, archive_format)
    except Exception as e:
        logger.error(f"Archive generation failed for user {user_id}: {e}")
        archive_record = UserArchive(
            user_id=user_id,
            status="F",
            frequency_at_send="N",
            format_at_send=archive_format,
            error_message=str(e),
        )
        db.add(archive_record)
        db.commit()
        if mc:
            mc.record_archive_failed("generate")
        raise HTTPException(status_code=500, detail="Failed to generate archive")

    export_ts = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    filename = f"trigpointinguk_{username}_{export_ts}.zip"

    dry_run = getattr(settings, "DRY_RUN_ARCHIVES", False)
    if dry_run:
        import pathlib
        import tempfile

        out_path = pathlib.Path(tempfile.gettempdir()) / filename
        out_path.write_bytes(zip_bytes)
        logger.info(f"DRY RUN: archive written to {out_path} ({len(zip_bytes)} bytes)")
        email_sent = True
    else:
        email_sent = email_service.send_archive_email(
            to_email=email_addr,
            username=username,
            zip_bytes=zip_bytes,
            filename=filename,
            log_count=db.query(TLog)
            .filter(TLog.user_id == user_id, TLog.status == "P")
            .count(),
            user_id=user_id,
            firstname=str(current_user.firstname or ""),
            surname=str(current_user.surname or ""),
        )

    log_count = (
        db.query(TLog).filter(TLog.user_id == user_id, TLog.status == "P").count()
    )

    archive_record = UserArchive(
        user_id=user_id,
        status="S" if email_sent else "F",
        frequency_at_send="N",
        format_at_send=archive_format,
        log_count=log_count,
        file_size_bytes=len(zip_bytes),
        error_message=None if email_sent else "SES send failed",
    )
    db.add(archive_record)
    db.commit()

    if not email_sent:
        if mc:
            mc.record_archive_failed("send")
        raise HTTPException(status_code=500, detail="Failed to send archive email")

    if mc:
        mc.record_archive_sent(archive_format, len(zip_bytes))

    return {
        "status": "sent",
        "log_count": log_count,
        "zip_size_bytes": len(zip_bytes),
        "format": archive_format,
    }


@router.get(
    "/me/archives",
    openapi_extra=openapi_lifecycle(
        "beta", note="List past archive emails sent to the current user."
    ),
)
def list_my_archives(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List past archive emails for the authenticated user."""
    from api.models.user import UserArchive

    user_id = int(current_user.id)

    total = db.query(UserArchive).filter(UserArchive.user_id == user_id).count()
    archives = (
        db.query(UserArchive)
        .filter(UserArchive.user_id == user_id)
        .order_by(UserArchive.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    items = []
    for a in archives:
        items.append(
            {
                "id": a.id,
                "status": a.status,
                "frequency_at_send": a.frequency_at_send,
                "format_at_send": a.format_at_send,
                "log_count": a.log_count,
                "file_size_bytes": a.file_size_bytes,
                "error_message": a.error_message,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
        )

    return {
        "items": items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": (skip + len(archives)) < total,
        },
    }


@router.get(
    "/archive-unsubscribe",
    openapi_extra=openapi_lifecycle(
        "beta", note="One-click unsubscribe from archive emails via signed token."
    ),
)
def archive_unsubscribe(
    uid: int = Query(..., description="User ID"),
    token: str = Query(..., description="HMAC token"),
    db: Session = Depends(get_db),
):
    """One-click unsubscribe from archive emails (no login required)."""
    from api.core.config import settings
    from api.services.email_service import verify_unsubscribe_token

    secret = settings.WEBHOOK_SHARED_SECRET or "dev-fallback"
    if not verify_unsubscribe_token(secret, uid, token):
        raise HTTPException(status_code=403, detail="Invalid or expired link")

    user = db.query(User).filter(User.id == uid).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user.archive_frequency = "N"  # type: ignore[assignment]
    db.commit()

    site_url = {
        "production": "https://trigpointing.uk",
        "staging": "https://trigpointing.me",
    }.get(settings.ENVIRONMENT, "http://localhost:5173")

    from fastapi.responses import HTMLResponse

    return HTMLResponse(
        f"<html><body style='font-family: sans-serif; max-width: 600px; "
        f"margin: 2em auto; text-align: center;'>"
        f"<h2>Unsubscribed</h2>"
        f"<p>You have been unsubscribed from TrigpointingUK archive emails.</p>"
        f"<p>If you change your mind, you can re-enable them from your "
        f'<a href="{site_url}/preferences#data-archive">account preferences</a>.</p>'
        f"</body></html>"
    )


@router.post(
    "/me/avatar",
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Upload a profile avatar image. Accepts JPEG, PNG, or WebP. "
        "Image is resized to 200x200 and stored in S3. Auth0 picture field is updated.",
    ),
)
def upload_avatar(
    file: UploadFile = File(..., description="Image file (JPEG, PNG, or WebP)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, str]:
    """
    Upload or replace the current user's avatar image.

    The image is validated, resized to 200x200 JPEG, uploaded to S3 with a
    public URL, and the Auth0 picture claim is updated to point at it.
    """
    from api.core.logging import get_logger
    from api.services.auth0_service import auth0_service
    from api.services.avatar_service import AvatarService

    logger = get_logger(__name__)

    file_contents = file.file.read()
    if not file_contents:
        raise HTTPException(status_code=400, detail="Empty file")

    avatar_service = AvatarService()
    is_valid, message = avatar_service.validate_image(file_contents)
    if not is_valid:
        raise HTTPException(status_code=400, detail=message)

    processed = avatar_service.process_image(file_contents)
    if processed is None:
        raise HTTPException(status_code=400, detail="Failed to process image")

    avatar_url = avatar_service.upload(int(current_user.id), processed)
    if avatar_url is None:
        raise HTTPException(status_code=500, detail="Failed to upload avatar")

    versioned_url = f"{avatar_url}?v={int(time.time())}"

    if not current_user.has_avatar:
        current_user.has_avatar = True  # type: ignore[assignment]
        db.commit()

    auth0_user_id = getattr(current_user, "auth0_user_id", None)
    if auth0_user_id:
        success = auth0_service.update_user_picture(auth0_user_id, versioned_url)
        if not success:
            logger.warning(
                json.dumps(
                    {
                        "event": "avatar_auth0_sync_failed",
                        "user_id": current_user.id,
                        "auth0_user_id": auth0_user_id,
                    }
                )
            )

    return {"avatar_url": versioned_url}


@router.get(
    "/me/logged-trigs",
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Get list of trigpoints the current user has logged with conditions. Used for map marker coloring.",
    ),
)
def get_current_user_logged_trigs(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get list of trigpoints the current user has logged with conditions.

    Returns a lightweight list containing just trig_id and condition for each log.
    This is used by the frontend to color map markers based on the user's log history.

    Cache is automatically invalidated when the user creates, updates, or deletes a log
    via the existing user:{user_id}:* cache invalidation pattern.

    The caching is handled in a wrapper that calls the user-specific version.

    Returns:
        List of dicts with trig_id and condition for each log
    """
    # Call the cached version with the user_id
    # IMPORTANT: Must use keyword arguments so the @cached decorator can extract
    # user_id from kwargs for the cache key (positional args are not checked)
    return get_user_logged_trigs_cached(user_id=current_user.id, db=db)


@cached(
    resource_type="user",
    ttl=31536000,
    resource_id_param="user_id",
    subresource="logged-trigs",
    cache_control="private, no-cache",
)  # 1 year - invalidated by log CRUD operations
def get_user_logged_trigs_cached(user_id: int, db: Session):
    """Cached implementation for getting user's logged trigs."""
    logs = db.query(TLog.trig_id, TLog.condition).filter(TLog.user_id == user_id).all()

    return [
        {"trig_id": int(log.trig_id), "condition": str(log.condition or "U")}
        for log in logs
    ]


@router.get(
    "/{user_id}/area-breakdown",
    response_model=UserAreaBreakdownResponse,
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Get user's log counts grouped by area for a specific area type. "
        "Uses spatial queries to determine which area each logged trigpoint falls within.",
    ),
)
@cached(
    resource_type="user",
    ttl=86400,
    resource_id_param="user_id",
    subresource="area-breakdown",
)  # 24 hours - area boundaries don't change often
def get_user_area_breakdown(
    user_id: int,
    area_type_code: str = Query(
        "county_1991",
        description="Area type code (e.g., county_1991, historic_county)",
    ),
    db: Session = Depends(get_db),
) -> UserAreaBreakdownResponse:
    """
    Get user's log counts grouped by area for a specific area type.

    Returns the count of distinct trigpoints the user has logged within each area
    of the specified type, ordered by count descending.

    Uses PostGIS spatial queries to determine which area each trigpoint falls within.
    """
    # Get area type info
    area_type = area_crud.get_area_type_by_code(db, area_type_code)
    if area_type is None:
        raise HTTPException(
            status_code=404,
            detail=f"Area type '{area_type_code}' not found",
        )

    # Get log counts by area
    counts = area_crud.get_user_log_counts_by_area(db, user_id, area_type_code)

    return UserAreaBreakdownResponse(
        area_type=AreaTypeResponse(
            id=int(area_type.id),
            code=str(area_type.code),
            name=str(area_type.name),
            description=str(area_type.description) if area_type.description else None,
        ),
        items=[
            AreaCountItem(area_name=item["area_name"], count=item["count"])
            for item in counts
        ],
    )


@router.get(
    "/{user_id}/badge",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "User statistics badge as PNG image",
        }
    },
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Generates a 200x50px PNG badge showing user statistics including nickname, trigpoints logged, and photos uploaded.",
    ),
)
@cached(
    resource_type="user", ttl=300, resource_id_param="user_id", subresource="badge"
)  # 5 minutes
def get_user_badge(
    user_id: int,
    scale: float = Query(
        1.0,
        ge=0.1,
        le=5.0,
        description="Scale factor for badge size (0.1-5.0, default: 1.0)",
    ),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    Generate a PNG badge for a user showing their statistics.

    Returns a scalable PNG image (default 200x50px) with:
    - TrigpointingUK logo on the left (20%)
    - User's nickname on the first line (right 80%)
    - "logged: X / photos: Y" on the second line
    - "Trigpointing.UK" on the third line

    Scale parameter allows resizing from 0.1x to 5.0x (e.g., scale=2.0 returns 400x100px)
    """
    try:
        badge_service = BadgeService()
        badge_bytes = badge_service.generate_badge(db, user_id, scale=scale)

        return StreamingResponse(
            badge_bytes,
            media_type="image/png",
            headers={
                "Content-Disposition": f"inline; filename=user_{user_id}_badge.png",
                "Cache-Control": "public, max-age=300",  # Cache for 5 minutes
            },
        )
    except ValueError:
        # Normalise not-found message for consistency across tests
        raise HTTPException(status_code=404, detail="User not found")
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Server configuration error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating badge: {e}")


@router.get(
    "/browse",
    response_model=UserListResponse,
    openapi_extra=openapi_lifecycle(
        "beta",
        note=(
            "Cursor-based directory of public users with sortable metrics. "
            "Supports substring filtering and highlights trig logs plus uploaded photos."
        ),
    ),
)
def browse_users(
    cursor: Optional[str] = Query(
        None, description="Opaque cursor token returned by the previous response"
    ),
    q: Optional[str] = Query(
        None, description="Case-insensitive substring match against usernames"
    ),
    limit: int = Query(
        40, ge=1, le=100, description="Maximum number of users returned per page"
    ),
    sort: UserSortField = Query(
        UserSortField.TRIGPOINTS,
        description="Sort field: trigs, photos, joined, or name",
    ),
    direction: SortDirection = Query(
        SortDirection.DESC, description="Sort direction: asc or desc"
    ),
    db: Session = Depends(get_db),
) -> UserListResponse:
    """
    Return a cursor-based listing of users with aggregated activity metrics.

    The endpoint favours deterministic ordering so that the frontend can implement
    infinite scrolling without relying on brittle offsets.
    """

    activity_summary = USER_ACTIVITY_SUMMARY.alias("uas")
    total_logs_column = activity_summary.c.total_logs.label("total_logs")
    total_trigs_column = activity_summary.c.total_trigs_logged.label(
        "total_trigs_logged"
    )
    total_photos_column = activity_summary.c.total_photos.label("total_photos")
    member_since_column = activity_summary.c.member_since.label("member_since")

    query = db.query(
        User.id.label("id"),
        User.name.label("name"),
        User.has_avatar.label("has_avatar"),
        User.firstname,
        User.surname,
        member_since_column,
        total_logs_column,
        total_trigs_column,
        total_photos_column,
    ).join(activity_summary, activity_summary.c.user_id == User.id)

    search_term = q.strip() if q else None
    like_pattern = f"%{search_term}%" if search_term else None
    if like_pattern:
        query = query.filter(User.name.ilike(like_pattern))

    count_query = db.query(func.count(User.id)).join(
        activity_summary, activity_summary.c.user_id == User.id
    )
    if like_pattern:
        count_query = count_query.filter(User.name.ilike(like_pattern))
    total_count = int(count_query.scalar() or 0)

    sort_expression_map = {
        UserSortField.TRIGPOINTS: total_trigs_column,
        UserSortField.PHOTOS: total_photos_column,
        UserSortField.LOGS: total_logs_column,
        UserSortField.JOINED: func.coalesce(member_since_column, _DEFAULT_JOINED_DATE),
        UserSortField.NAME: func.lower(User.name),
    }
    sort_expression = sort_expression_map.get(sort, total_trigs_column)

    if cursor:
        cursor_payload = _decode_cursor_token(cursor)
        if cursor_payload.get("sort") != sort.value:
            raise HTTPException(
                status_code=400,
                detail="Cursor sort does not match the current request parameters",
            )
        if cursor_payload.get("direction") != direction.value:
            raise HTTPException(
                status_code=400,
                detail="Cursor direction does not match the current request parameters",
            )
        cursor_value = _coerce_cursor_value(sort, cursor_payload.get("sort_value"))
        raw_user_id = cursor_payload.get("user_id")
        if raw_user_id is None:
            raise HTTPException(status_code=400, detail="Invalid cursor token")
        try:
            cursor_user_id = int(raw_user_id)
        except (TypeError, ValueError) as exc:  # pragma: no cover - defensive branch
            raise HTTPException(status_code=400, detail="Invalid cursor token") from exc

        if direction == SortDirection.DESC:
            cursor_condition = or_(
                sort_expression < cursor_value,
                and_(sort_expression == cursor_value, User.id < cursor_user_id),
            )
        else:
            cursor_condition = or_(
                sort_expression > cursor_value,
                and_(sort_expression == cursor_value, User.id > cursor_user_id),
            )
        query = query.filter(cursor_condition)

    primary_order = (
        sort_expression.desc()
        if direction == SortDirection.DESC
        else sort_expression.asc()
    )
    secondary_order = (
        User.id.desc() if direction == SortDirection.DESC else User.id.asc()
    )

    rows = query.order_by(primary_order, secondary_order).limit(limit + 1).all()
    page_rows = rows[:limit]

    def _extract_sort_value(row_data: Mapping[str, Any]) -> Any:
        if sort == UserSortField.TRIGPOINTS:
            return int(row_data["total_trigs_logged"])
        if sort == UserSortField.PHOTOS:
            return int(row_data["total_photos"])
        if sort == UserSortField.JOINED:
            return row_data["member_since"] or _DEFAULT_JOINED_DATE
        return str(row_data["name"]).lower()

    items: list[UserListItem] = []
    for row in page_rows:
        data = dict(row._mapping)
        stats = UserStats(
            total_logs=int(data["total_logs"]),
            total_trigs_logged=int(data["total_trigs_logged"]),
            total_photos=int(data["total_photos"]),
        )
        items.append(
            UserListItem(
                id=int(data["id"]),
                name=str(data["name"]),
                has_avatar=bool(data.get("has_avatar", False)),
                member_since=data["member_since"],
                stats=stats,
                profile_path=f"/profile/{int(data['id'])}",
            )
        )

    next_cursor = None
    if len(rows) > limit and page_rows:
        last_row_data = dict(page_rows[-1]._mapping)
        sort_value = _extract_sort_value(last_row_data)
        next_cursor = _encode_cursor_token(
            sort_value=sort_value,
            user_id=int(last_row_data["id"]),
            sort=sort,
            direction=direction,
        )

    return UserListResponse(
        items=items,
        next_cursor=next_cursor,
        total=total_count,
        applied_filters=UserListFilters(
            query=search_term,
            sort=sort,
            direction=direction,
            limit=limit,
        ),
    )


@router.get("/{user_id}", response_model=UserWithIncludes)
@cached(resource_type="user", ttl=21600, resource_id_param="user_id")  # 6 hours
def get_user(
    user_id: int,
    include: Optional[str] = Query(
        None, description="Comma-separated includes: stats,breakdown"
    ),
    db: Session = Depends(get_db),
):
    """
    Get a user by ID - public data only.

    - Supports optional includes via the `include` query parameter:
      - stats: adds basic log stats (totals only) for the user
      - breakdown: adds detailed breakdown statistics

    For private data including preferences, use GET /users/me
    """
    user = user_crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Build base response using Pydantic model validation with member_since field
    user_response = UserResponse.model_validate(user)
    user_response.member_since = user.crt_date  # type: ignore
    result = UserWithIncludes(**user_response.model_dump())

    # Handle includes...
    tokens = {t.strip() for t in include.split(",")} if include else set()

    # Validate include tokens
    valid_includes = {"stats", "breakdown"}
    invalid_tokens = tokens - valid_includes
    if invalid_tokens:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
        )

    if "stats" in tokens:
        # Calculate basic stats
        total_logs = (
            db.query(user_crud.TLog).filter(user_crud.TLog.user_id == user_id).count()
        )
        total_trigs = (
            db.query(user_crud.TLog.trig_id)
            .filter(user_crud.TLog.user_id == user_id)
            .distinct()
            .count()
        )
        total_photos = (
            db.query(TPhoto)
            .join(user_crud.TLog, TPhoto.tlog_id == user_crud.TLog.id)
            .filter(user_crud.TLog.user_id == user_id, TPhoto.deleted_ind != "Y")
            .count()
        )

        result.stats = UserStats(
            total_logs=int(total_logs),
            total_trigs_logged=int(total_trigs),
            total_photos=int(total_photos),
        )

    if "breakdown" in tokens:
        # Calculate breakdowns by trig characteristics (distinct trigpoints only)
        by_current_use_raw = (
            db.query(
                Trig.current_use, func.count(func.distinct(user_crud.TLog.trig_id))
            )
            .join(user_crud.TLog, user_crud.TLog.trig_id == Trig.id)
            .filter(user_crud.TLog.user_id == user_id)
            .group_by(Trig.current_use)
            .all()
        )
        by_current_use: Dict[str, int] = {
            str(use): int(count) for use, count in by_current_use_raw
        }

        by_historic_use_raw = (
            db.query(
                Trig.historic_use, func.count(func.distinct(user_crud.TLog.trig_id))
            )
            .join(user_crud.TLog, user_crud.TLog.trig_id == Trig.id)
            .filter(user_crud.TLog.user_id == user_id)
            .group_by(Trig.historic_use)
            .all()
        )
        by_historic_use: Dict[str, int] = {
            str(use): int(count) for use, count in by_historic_use_raw
        }

        # Calculate breakdown by type grouped by category
        by_type_raw = (
            db.query(
                TrigCategory.code.label("category_code"),
                TrigCategory.name.label("category_name"),
                TrigCategory.sort_order.label("sort_order"),
                TrigType.code.label("type_code"),
                TrigType.name.label("type_name"),
                func.count(func.distinct(user_crud.TLog.trig_id)).label("trig_count"),
            )
            .select_from(Trig)
            .join(user_crud.TLog, user_crud.TLog.trig_id == Trig.id)
            .join(TrigType, Trig.type_id == TrigType.id)
            .join(TrigCategory, TrigType.category_id == TrigCategory.id)
            .filter(user_crud.TLog.user_id == user_id)
            .group_by(
                TrigCategory.code,
                TrigCategory.name,
                TrigCategory.sort_order,
                TrigType.code,
                TrigType.name,
            )
            .all()
        )

        # Group by category and build the structured response
        categories_dict: Dict[str, CategoryTypeBreakdown] = {}
        for row in by_type_raw:
            cat_code = str(row.category_code)
            if cat_code not in categories_dict:
                categories_dict[cat_code] = CategoryTypeBreakdown(
                    category_code=cat_code,
                    category_name=str(row.category_name),
                    sort_order=int(row.sort_order),
                    types=[],
                )
            categories_dict[cat_code].types.append(
                TypeCount(
                    type_code=str(row.type_code),
                    type_name=str(row.type_name),
                    count=int(row.trig_count),
                )
            )

        # Sort types within each category by count descending
        for cat in categories_dict.values():
            cat.types.sort(key=lambda t: t.count, reverse=True)

        # Sort categories by sort_order
        by_type = sorted(categories_dict.values(), key=lambda c: c.sort_order)

        # Calculate breakdown by log condition (all logs counted)
        condition_counts_raw = (
            db.query(user_crud.TLog.condition, func.count(user_crud.TLog.id))
            .filter(user_crud.TLog.user_id == user_id)
            .group_by(user_crud.TLog.condition)
            .all()
        )
        condition_counts: Dict[str, int] = {
            str(cond): int(count) for cond, count in condition_counts_raw
        }
        by_condition = get_condition_counts_by_description(condition_counts, db)

        result.breakdown = UserBreakdown(
            by_current_use=by_current_use,
            by_historic_use=by_historic_use,
            by_type=by_type,
            by_condition=by_condition,
        )

    return result


@router.get("")
@cached(resource_type="users", ttl=43200, subresource="list")  # 12 hours
def list_users(
    name: Optional[str] = Query(None, description="Filter by username (contains)"),
    include: Optional[str] = Query(None, description="Comma-separated includes: stats"),
    skip: int = Query(0, ge=0, description="Number of records to skip"),
    limit: int = Query(
        10, ge=1, le=100, description="Maximum number of records to return"
    ),
    db: Session = Depends(get_db),
):
    """Filtered collection endpoint for users returning envelope with items and pagination.

    - Supports optional includes via the `include` query parameter:
      - stats: adds basic log stats (totals only) for each user
    """
    # Explicit empty string should mean: return all users (no name filter)
    if name is not None and name.strip() == "":
        query = db.query(user_crud.User)
        total = query.count()
        items = query.offset(skip).limit(limit).all()
    elif name:
        items = user_crud.search_users_by_name(
            db, name_pattern=name, skip=skip, limit=limit
        )
        # Estimate total via a count query matching the filter
        total = (
            db.query(user_crud.User)
            .filter(user_crud.User.name.ilike(f"%{name}%"))
            .count()
            if hasattr(user_crud, "User")
            else len(items)
        )
    else:
        # No name filter provided -> return all users with pagination
        if hasattr(user_crud, "User"):
            total = db.query(user_crud.User).count()
            items = db.query(user_crud.User).offset(skip).limit(limit).all()
        else:
            items = []
            total = 0

    has_more = (skip + len(items)) < total
    base = "/v1/users"
    params = [f"limit={limit}"]
    if name:
        params.insert(0, f"name={name}")
    self_link = base + "?" + "&".join(params + [f"skip={skip}"])
    next_link = (
        base + "?" + "&".join(params + [f"skip={skip + limit}"]) if has_more else None
    )
    prev_offset = max(skip - limit, 0)
    prev_link = (
        base + "?" + "&".join(params + [f"skip={prev_offset}"]) if skip > 0 else None
    )

    # Parse include tokens
    tokens = {t.strip() for t in include.split(",")} if include else set()

    # Validate include tokens (only 'stats' supported for list endpoint)
    valid_includes = {"stats"}
    invalid_tokens = tokens - valid_includes
    if invalid_tokens:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options for user list: {', '.join(sorted(valid_includes))}",
        )

    # If stats are requested, get user IDs for bulk stats calculation
    user_stats: Dict[int, UserStats] = {}
    if "stats" in tokens:
        user_ids = [int(u.id) for u in items]
        if user_ids:
            # Calculate basic stats for all users at once
            total_logs_query = (
                db.query(user_crud.TLog.user_id, func.count(user_crud.TLog.id))
                .filter(user_crud.TLog.user_id.in_(user_ids))
                .group_by(user_crud.TLog.user_id)
                .all()
            )

            total_trigs_query = (
                db.query(
                    user_crud.TLog.user_id,
                    func.count(func.distinct(user_crud.TLog.trig_id)),
                )
                .filter(user_crud.TLog.user_id.in_(user_ids))
                .group_by(user_crud.TLog.user_id)
                .all()
            )

            total_photos_query = (
                db.query(user_crud.TLog.user_id, func.count(TPhoto.id))
                .join(TPhoto, TPhoto.tlog_id == user_crud.TLog.id)
                .filter(user_crud.TLog.user_id.in_(user_ids), TPhoto.deleted_ind != "Y")
                .group_by(user_crud.TLog.user_id)
                .all()
            )

            # Convert to dictionaries for fast lookup
            logs_by_user: Dict[int, int] = {
                user_id: count for user_id, count in total_logs_query
            }
            trigs_by_user: Dict[int, int] = {
                user_id: count for user_id, count in total_trigs_query
            }
            photos_by_user: Dict[int, int] = {
                user_id: count for user_id, count in total_photos_query
            }

            for user_id in user_ids:
                user_stats[user_id] = UserStats(
                    total_logs=logs_by_user.get(user_id, 0),
                    total_trigs_logged=trigs_by_user.get(user_id, 0),
                    total_photos=photos_by_user.get(user_id, 0),
                )

    # Serialize users with optional stats
    items_serialized = []
    for u in items:
        user_response = UserResponse.model_validate(u)
        user_response.member_since = u.crt_date  # type: ignore

        # Create UserWithIncludes response
        result = UserWithIncludes(**user_response.model_dump())

        # Add stats if requested
        if "stats" in tokens and int(u.id) in user_stats:
            result.stats = user_stats[int(u.id)]

        items_serialized.append(result.model_dump())
    return {
        "items": items_serialized,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }


@router.get("/{user_id}/logs", openapi_extra=openapi_lifecycle("beta"))
@cached(
    resource_type="user", ttl=7200, resource_id_param="user_id", subresource="logs"
)  # 2 hours
def list_logs_for_user(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    include: Optional[str] = Query(
        None, description="Comma-separated list of includes: photos"
    ),
    lat: Optional[float] = Query(
        None, description="Centre latitude for distance filtering"
    ),
    lon: Optional[float] = Query(
        None, description="Centre longitude for distance filtering"
    ),
    max_km: Optional[float] = Query(
        None, description="Maximum distance from centre in kilometres"
    ),
    groups: Optional[str] = Query(
        None,
        description="Comma-separated group codes to filter by (e.g., 'PILLAR,FBM')",
    ),
    area_id: Optional[int] = Query(
        None, description="Filter to logs for trigpoints within a specific area"
    ),
    from_date: Optional[date_type] = Query(
        None, description="Filter logs from this date (inclusive, YYYY-MM-DD)"
    ),
    to_date: Optional[date_type] = Query(
        None, description="Filter logs to this date (inclusive, YYYY-MM-DD)"
    ),
    db: Session = Depends(get_db),
):
    # Parse groups from comma-separated string
    parsed_groups: Optional[list[str]] = None
    if groups:
        parsed_groups = [g.strip().upper() for g in groups.split(",") if g.strip()]

    items = tlog_crud.list_logs_filtered(
        db,
        user_id=user_id,
        skip=skip,
        limit=limit,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        category_codes=parsed_groups,
        area_id=area_id,
        from_date=from_date,
        to_date=to_date,
    )
    total = tlog_crud.count_logs_filtered(
        db,
        user_id=user_id,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        category_codes=parsed_groups,
        area_id=area_id,
        from_date=from_date,
        to_date=to_date,
    )

    # Import helper from logs endpoint
    from api.api.v1.endpoints.logs import enrich_logs_with_names

    items_serialized = enrich_logs_with_names(db, items, center_lat=lat, center_lon=lon)

    # Handle includes
    if include:
        tokens = {t.strip() for t in include.split(",") if t.strip()}

        # Validate include tokens
        valid_includes = {"photos"}
        invalid_tokens = tokens - valid_includes
        if invalid_tokens:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid include parameter(s): {', '.join(sorted(invalid_tokens))}. Valid options: {', '.join(sorted(valid_includes))}",
            )
        if "photos" in tokens:
            # Attach photos list for each log item
            for out, orig in zip(items_serialized, items):
                photos = tphoto_crud.list_all_photos_for_log(db, log_id=int(orig.id))
                # Build base URLs per photo server
                out["photos"] = []
                for p in photos:
                    server: Server | None = (
                        db.query(Server).filter(Server.id == p.server_id).first()
                    )
                    base_url = str(server.url) if server and server.url else ""
                    # Handle empty type field by defaulting to 'O' (other)
                    photo_type = str(p.type) if p.type and p.type.strip() else "O"
                    out["photos"].append(
                        TPhotoResponse(
                            id=int(p.id),
                            log_id=int(p.tlog_id),
                            user_id=int(orig.user_id),
                            type=photo_type,
                            filesize=int(p.filesize),
                            height=int(p.height),
                            width=int(p.width),
                            icon_filesize=int(p.icon_filesize),
                            icon_height=int(p.icon_height),
                            icon_width=int(p.icon_width),
                            name=str(p.name),
                            text_desc=str(p.text_desc),
                            public_ind=str(p.public_ind),
                            photo_url=join_url(base_url, str(p.filename)),
                            icon_url=join_url(base_url, str(p.icon_filename)),
                        ).model_dump(by_alias=True)
                    )

    has_more = (skip + len(items)) < total
    base = f"/v1/users/{user_id}/logs"
    params = [f"limit={limit}"]
    if lat is not None:
        params.append(f"lat={lat}")
    if lon is not None:
        params.append(f"lon={lon}")
    if max_km is not None:
        params.append(f"max_km={max_km}")
    if groups is not None:
        params.append(f"groups={groups}")
    if area_id is not None:
        params.append(f"area_id={area_id}")
    if from_date is not None:
        params.append(f"from_date={from_date.isoformat()}")
    if to_date is not None:
        params.append(f"to_date={to_date.isoformat()}")
    self_link = base + "?" + "&".join(params + [f"skip={skip}"])
    next_link = (
        base + "?" + "&".join(params + [f"skip={skip + limit}"]) if has_more else None
    )
    prev_offset = max(skip - limit, 0)
    prev_link = (
        base + "?" + "&".join(params + [f"skip={prev_offset}"]) if skip > 0 else None
    )
    return {
        "items": items_serialized,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }


@router.get("/{user_id}/photos", openapi_extra=openapi_lifecycle("beta"))
@cached(
    resource_type="user", ttl=7200, resource_id_param="user_id", subresource="photos"
)  # 2 hours
def list_photos_for_user(
    user_id: int,
    skip: int = Query(0, ge=0),
    limit: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    items = tphoto_crud.list_photos_filtered(
        db, user_id=user_id, skip=skip, limit=limit
    )
    total = (
        db.query(tphoto_crud.TPhoto)
        .join(user_crud.TLog, user_crud.TLog.id == tphoto_crud.TPhoto.tlog_id)
        .filter(
            user_crud.TLog.user_id == user_id, tphoto_crud.TPhoto.deleted_ind != "Y"
        )
        .count()
    )
    result_items = []
    for p in items:
        # Get log and trig info for this photo
        tlog = db.query(TLog).filter(TLog.id == p.tlog_id).first()
        trig = (
            db.query(Trig).filter(Trig.id == tlog.trig_id).first()
            if tlog and tlog.trig_id
            else None
        )
        user = db.query(User).filter(User.id == user_id).first()

        server: Server | None = (
            db.query(Server).filter(Server.id == p.server_id).first()
        )
        base_url = str(server.url) if server and server.url else ""
        # Handle empty type field by defaulting to 'O' (other)
        photo_type = str(p.type) if p.type and p.type.strip() else "O"
        result_items.append(
            TPhotoResponse(
                id=int(p.id),
                log_id=int(p.tlog_id),
                user_id=user_id,
                type=photo_type,
                filesize=int(p.filesize),
                height=int(p.height),
                width=int(p.width),
                icon_filesize=int(p.icon_filesize),
                icon_height=int(p.icon_height),
                icon_width=int(p.icon_width),
                name=str(p.name),
                text_desc=str(p.text_desc),
                public_ind=str(p.public_ind),
                photo_url=join_url(base_url, str(p.filename)),
                icon_url=join_url(base_url, str(p.icon_filename)),
                user_name=str(user.name) if user else None,
                trig_id=int(tlog.trig_id) if tlog and tlog.trig_id else None,
                trig_name=str(trig.name) if trig else None,
                log_date=(
                    date_type(tlog.date.year, tlog.date.month, tlog.date.day)
                    if tlog and tlog.date
                    else None
                ),
            ).model_dump(by_alias=True)
        )
    has_more = (skip + len(items)) < total
    base = f"/v1/users/{user_id}/photos"
    self_link = base + f"?limit={limit}&skip={skip}"
    next_link = base + f"?limit={limit}&skip={skip + limit}" if has_more else None
    prev_offset = max(skip - limit, 0)
    prev_link = base + f"?limit={limit}&skip={prev_offset}" if skip > 0 else None
    return {
        "items": result_items,
        "pagination": {
            "total": total,
            "limit": limit,
            "offset": skip,
            "has_more": has_more,
        },
        "links": {"self": self_link, "next": next_link, "prev": prev_link},
    }


@router.get(
    "/{user_id}/map",
    responses={
        200: {
            "content": {"image/png": {}},
            "description": "Rendered user trigpoint map overlay as PNG",
        }
    },
    openapi_extra=openapi_lifecycle(
        "beta",
        note=(
            "Generates a PNG map with dots for found/notfound/notlogged trigpoints. "
            "Colours may be provided as hex strings. Rendering order: notlogged (bottom), notfound (middle), found (top)."
        ),
    ),
)
@cached(
    resource_type="user", ttl=14400, resource_id_param="user_id", subresource="map"
)  # 4 hours
def get_user_map(
    user_id: int,
    found_colour: Optional[str] = Query(
        None,
        description="Hex #RRGGBB or 'none' for found trigs (blank → default)",
    ),
    notfound_colour: Optional[str] = Query(
        None,
        description="Hex #RRGGBB or 'none' for not-found trigs (blank → default)",
    ),
    notlogged_colour: Optional[str] = Query(
        None,
        description="Hex #RRGGBB or 'none' for not-logged trigs (blank → default)",
    ),
    map_variant: Optional[str] = Query(
        "stretched53",
        description="Map variant: stretched53 (default) or wgs84",
    ),
    # Re-add configurable dot size (diameter, default 10px)
    dot_diameter: int = Query(
        50, ge=1, le=100, description="Diameter of plotted dots in pixels (default 50)"
    ),
    # Optional alpha for dots to allow visual stacking
    dot_alpha: Optional[int] = Query(
        40, ge=1, le=255, description="Per-dot alpha increment (default 40)"
    ),
    # Optional land recolour; sea remains transparent
    land_colour: Optional[str] = Query(
        "#dddddd", description="Hex fill for land; 'none' to keep original"
    ),
    coastline_colour: Optional[str] = Query(
        "#666666", description="Stroke colour for coastline edges"
    ),
    height: int = Query(
        110, ge=10, le=4000, description="Output image height in pixels (default 110)"
    ),
    db: Session = Depends(get_db),
):
    """
    Render a user map overlay using `res/ukmap.jpg` and `res/uk_map_calibration.json`.

    Expensive full-trig-table query is performed only when `notlogged_colour` is provided.
    """
    try:
        # Resolve colours: blank → default; 'none' → disable
        def _norm(cval: Optional[str], default_hex: Optional[str]) -> Optional[str]:
            s = (cval or "").strip()
            if not s:
                return default_hex
            if s.lower() == "none":
                return None
            return s

        found_hex = _norm(found_colour, "#ff0000")
        notfound_hex = _norm(notfound_colour, "#0000ff")
        notlogged_hex = _norm(notlogged_colour, None)

        # Load base map image (fallback if missing)
        image_filename = (
            "ukmap_wgs84_stretched53.png"
            if map_variant == "stretched53"
            else "ukmap_wgs84.png"
        )
        calib_filename = (
            "uk_map_calibration_wgs84_stretched53.json"
            if map_variant == "stretched53"
            else "uk_map_calibration_wgs84.json"
        )
        map_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "..",
            "..",
            "res",
            image_filename,
        )
        map_path = os.path.normpath(map_path)
        if os.path.isfile(map_path):
            # Preserve alpha from the asset (transparent sea)
            base = Image.open(map_path).convert("RGBA")
        else:
            # Fallback transparent canvas
            base = Image.new("RGBA", (800, 900), color=(0, 0, 0, 0))

        # Load calibration
        calib_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
            "..",
            "..",
            "res",
            calib_filename,
        )
        calib_path = os.path.normpath(calib_path)
        with open(calib_path, "r") as f:
            d = json.load(f)
        calib = CalibrationResult(
            affine=np.array(d["affine"], dtype=float),
            inverse=np.array(d["inverse"], dtype=float),
            pixel_bbox=tuple(d.get("pixel_bbox", (0, 0, base.size[0], base.size[1]))),
            bounds_geo=tuple(d.get("bounds_geo", (-11.0, 49.0, 2.5, 61.5))),
        )

        # If a land colour is provided, recolour the land using the alpha mask,
        # then re-apply a coastline stroke extracted from the alpha edges.
        if land_colour and land_colour.strip():
            hc = land_colour.strip()
            if hc.startswith("#"):
                hc = hc[1:]
            if len(hc) == 6:
                r = int(hc[0:2], 16)
                g = int(hc[2:4], 16)
                b = int(hc[4:6], 16)
                alpha_ch = base.getchannel("A")
                recol = Image.new("RGBA", base.size, (r, g, b, 255))
                recol.putalpha(alpha_ch)
                base = recol

                # Coastline stroke from alpha edge
                edge_mask = alpha_ch.filter(ImageFilter.FIND_EDGES)
                # Thicken slightly for visibility
                try:
                    edge_mask = edge_mask.filter(ImageFilter.MaxFilter(3))
                except Exception:
                    # If MaxFilter is unavailable in this Pillow build, continue with the thin edge
                    edge_mask = edge_mask
                sc = (40, 40, 40, 255)
                if coastline_colour:
                    s = coastline_colour.strip()
                    if s.startswith("#"):
                        s = s[1:]
                    if len(s) == 6:
                        sc = (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16), 255)
                stroke_layer = Image.new("RGBA", base.size, sc)
                base.paste(stroke_layer, (0, 0), edge_mask)

        draw = ImageDraw.Draw(base)

        def draw_dot(px: float, py: float, hex_colour: str) -> None:
            if not hex_colour:
                return
            r = max(1, int(round(dot_diameter / 2)))
            x = int(round(px))
            y = int(round(py))
            if x < 0 or y < 0 or x >= base.size[0] or y >= base.size[1]:
                return
            bbox = [x - r, y - r, x + r, y + r]
            # Support optional alpha override for stacking
            fill: Union[str, tuple[int, int, int, int]] = hex_colour
            if dot_alpha is not None:
                s = hex_colour.strip()
                if s.startswith("#"):
                    s = s[1:]
                if len(s) == 6:
                    rr = int(s[0:2], 16)
                    gg = int(s[2:4], 16)
                    bb = int(s[4:6], 16)
                    fill = (rr, gg, bb, int(dot_alpha))
            draw.ellipse(bbox, fill=fill, outline=None)

        def _hex_to_rgb(hex_str: str) -> tuple[int, int, int]:
            s = hex_str.strip()
            if s.startswith("#"):
                s = s[1:]
            if len(s) >= 6:
                return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
            return (255, 0, 0)

        def accumulate_and_paste(
            points: list[tuple[float, float]], colour_hex: str
        ) -> None:
            if not points:
                return
            r = max(1, int(round(dot_diameter / 2)))
            inc = int(dot_alpha) if dot_alpha is not None else 64
            w, h = base.size
            accum = Image.new("L", (w, h), 0)
            for px, py in points:
                x = int(round(px))
                y = int(round(py))
                if x < 0 or y < 0 or x >= w or y >= h:
                    continue
                left = max(0, x - r)
                right = min(w, x + r)
                top = max(0, y - r)
                bottom = min(h, y + r)
                if right <= left or bottom <= top:
                    continue
                dot_w = right - left
                dot_h = bottom - top
                dot = Image.new("L", (dot_w, dot_h), 0)
                ddraw = ImageDraw.Draw(dot)
                ddraw.ellipse([0, 0, dot_w - 1, dot_h - 1], fill=inc)
                region = accum.crop((left, top, right, bottom))
                added = ImageChops.add(region, dot)
                accum.paste(added, (left, top))

            rgb = _hex_to_rgb(colour_hex)
            overlay = Image.new("RGBA", (w, h), (rgb[0], rgb[1], rgb[2], 255))
            base.paste(overlay, (0, 0), accum)

        GOOD = {"G", "S", "D", "T"}

        # Query user's tlogs with trig coords
        tlog_rows = (
            db.query(
                user_crud.TLog.trig_id,
                user_crud.TLog.condition,
                Trig.wgs_lat,
                Trig.wgs_long,
            )
            .join(Trig, Trig.id == user_crud.TLog.trig_id)
            .filter(user_crud.TLog.user_id == user_id)
            .all()
        )

        # Prepare sets and lists
        logged_ids = set()
        found_pts: list[tuple[float, float]] = []
        notfound_pts: list[tuple[float, float]] = []
        notlogged_pts: list[tuple[float, float]] = []
        for trig_id, condition, lat, lon in tlog_rows:
            logged_ids.add(int(trig_id))
            lat_f = float(lat)
            lon_f = float(lon)
            x, y = calib.lonlat_to_xy(lon_f, lat_f)
            if str(condition) in GOOD:
                found_pts.append((x, y))
            else:
                notfound_pts.append((x, y))

        # Only if notlogged requested, query all trigpoints
        if notlogged_hex:
            all_trigs = db.query(Trig.id, Trig.wgs_lat, Trig.wgs_long).all()
            for tid, lat, lon in all_trigs:
                if int(tid) in logged_ids:
                    continue
                x, y = calib.lonlat_to_xy(float(lon), float(lat))
                notlogged_pts.append((x, y))

        # Draw notfound beneath found
        if notlogged_hex:
            accumulate_and_paste(notlogged_pts, notlogged_hex)
        if notfound_hex:
            accumulate_and_paste(notfound_pts, notfound_hex)
        if found_hex:
            accumulate_and_paste(found_pts, found_hex)

        # Optional final scaling to requested height (preserve aspect, anti-aliased)
        if isinstance(height, int) and height > 0 and base.height != height:
            scale = float(height) / float(base.height)
            new_w = max(1, int(round(base.width * scale)))
            # Pillow>=10 recommends Image.Resampling.LANCZOS; keep compatibility
            try:
                resample = Image.Resampling.LANCZOS  # type: ignore[attr-defined]
            except Exception:
                try:
                    resample = Image.Resampling.NEAREST  # type: ignore[attr-defined]
                except Exception:
                    resample = 0  # type: ignore[assignment]
            base = base.resize((new_w, height), resample=resample)

        # Encode image (preserve alpha)
        buf = io.BytesIO()
        base.save(buf, format="PNG")
        buf.seek(0)
        return StreamingResponse(buf, media_type="image/png")
    except FileNotFoundError as e:
        raise HTTPException(status_code=500, detail=f"Server configuration error: {e}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rendering user map: {e}")


@router.get(
    "/{user_id}/log-timeline",
    openapi_extra=openapi_lifecycle(
        "beta",
        note="Lightweight timeline data for animated map visualisation. "
        "Returns coordinates, dates, and colours sorted chronologically.",
    ),
)
@cached(
    resource_type="user",
    ttl=7200,
    resource_id_param="user_id",
    subresource="log-timeline",
)  # 2 hours - invalidated by log CRUD operations
def get_user_log_timeline(
    user_id: int,
    db: Session = Depends(get_db),
):
    """
    Get lightweight log timeline data for animated map visualisation.

    Returns an array of {lat, lon, date, colour} tuples sorted by date ascending.
    The colour field is derived from the condition table's log_colour field.

    This endpoint is optimised for minimal payload size to support client-side
    rendering of animated user activity maps.
    """
    # Verify user exists
    user = user_crud.get_user_by_id(db, user_id=user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Query logs with trig coordinates and condition colour
    # Join: TLog -> Trig (for coordinates) -> Condition (for log_colour)
    logs = (
        db.query(
            Trig.wgs_lat,
            Trig.wgs_long,
            TLog.date,
            Condition.log_colour,
        )
        .select_from(TLog)
        .join(Trig, TLog.trig_id == Trig.id)
        .outerjoin(Condition, TLog.condition == Condition.code)
        .filter(TLog.user_id == user_id)
        .filter(Trig.wgs_lat.isnot(None))
        .filter(Trig.wgs_long.isnot(None))
        .order_by(TLog.date.asc(), TLog.id.asc())
        .all()
    )

    # Build lightweight response
    result = []
    for log in logs:
        # Normalise colour: green, yellow, red, or grey
        raw_colour = (log.log_colour or "").lower()
        if raw_colour in ("green", "lime"):
            colour = "green"
        elif raw_colour in ("yellow", "orange", "amber"):
            colour = "yellow"
        elif raw_colour in ("red", "maroon"):
            colour = "red"
        else:
            colour = "grey"

        result.append(
            {
                "lat": float(log.wgs_lat),
                "lon": float(log.wgs_long),
                "date": log.date.isoformat() if log.date else None,
                "colour": colour,
            }
        )

    return result
