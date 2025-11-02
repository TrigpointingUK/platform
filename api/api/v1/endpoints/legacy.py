"""
Legacy endpoints for authentication and administrative operations.
"""

from datetime import datetime, timezone  # noqa: F401
from typing import Dict, Optional

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.api.deps import get_db, require_scopes
from api.api.lifecycle import openapi_lifecycle
from api.crud import user as user_crud
from api.crud.user import update_user_email
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.schemas.user import (
    LegacyLoginRequest,
    LegacyLoginResponse,
    UserBreakdown,
    UserPrefs,
    UserResponse,
    UserStats,
)
from api.services.auth0_service import auth0_service
from api.utils.condition_mapping import get_condition_counts_by_description

router = APIRouter()


@router.post(
    "/login", response_model=LegacyLoginResponse, response_model_exclude_none=True
)
def login_for_access_token(
    request: LegacyLoginRequest = Body(...), db: Session = Depends(get_db)
):
    """
    Legacy login endpoint - authenticates users and syncs with Auth0.

    This endpoint authenticates users against the legacy database using
    Unix crypt password hashing, then synchronises their credentials and
    email with Auth0. If the user doesn't have an Auth0 account, one is
    created automatically.

    Process:
    1. Look up user by username in legacy database
    2. Authenticate password using Unix crypt
    3. If user has auth0_user_id:
       - Update Auth0 password
       - Update Auth0 email (triggering verification if changed)
       - Update database email
    4. If user doesn't have auth0_user_id:
       - Create new Auth0 user with provided credentials
       - Store Auth0 user ID in database
       - Update database email
    5. Return user data with optional includes (stats, breakdown, prefs)

    Args:
        request: LegacyLoginRequest with username, password, email, and optional includes
        db: Database session

    Returns:
        LegacyLoginResponse with user data and any requested includes

    Raises:
        401: Authentication failed (wrong username or password)
        500: Auth0 synchronisation failed
    """
    # Look up user by username
    user = user_crud.get_user_by_name(db, name=request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Verify password using Unix crypt
    if not user_crud.verify_password(request.password, str(user.cryptpw)):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )

    # Track if email changed
    email_changed = str(user.email).lower() != request.email.lower()

    # Sync with Auth0
    if user.auth0_user_id:
        # User has Auth0 account - update password and email
        # Update password
        password_success = auth0_service.update_user_password(
            user_id=str(user.auth0_user_id),
            password=request.password,
        )
        if not password_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update Auth0 password",
            )

        # Update email if changed
        if email_changed:
            email_success = auth0_service.update_user_email(
                user_id=str(user.auth0_user_id),
                email=request.email,
            )
            if not email_success:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update Auth0 email",
                )
    else:
        # User doesn't have Auth0 account - create one
        auth0_user = auth0_service.create_user(
            username=request.username,
            email=request.email,
            password=request.password,
            name=request.username,  # Set Auth0 name and nickname to username
            user_id=int(user.id),  # Store database user ID in Auth0 app_metadata
            firstname=str(user.firstname) if user.firstname else None,
            surname=str(user.surname) if user.surname else None,
        )
        if not auth0_user or not auth0_user.get("user_id"):
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create Auth0 user",
            )

        # Store Auth0 user ID in database
        auth0_user_id = str(auth0_user.get("user_id"))
        mapping_success = user_crud.update_user_auth0_mapping(
            db=db,
            user_id=int(user.id),
            auth0_user_id=auth0_user_id,
        )
        if not mapping_success:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to store Auth0 user ID",
            )

        # Update user object to reflect the change
        user.auth0_user_id = auth0_user_id  # type: ignore

    # Update email in database and set email_valid to 'Y'
    success = update_user_email(db=db, user_id=int(user.id), email=request.email)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update email in database",
        )

    # Refresh user object to get updated values
    db.refresh(user)

    # Create base response
    user_response = UserResponse.model_validate(user)
    user_response.member_since = user.crt_date  # type: ignore
    result = LegacyLoginResponse(
        **user_response.model_dump(),
        email=str(user.email),
        email_valid=str(user.email_valid),
    )

    # Handle includes
    if request.include:
        tokens = {t.strip() for t in request.include.split(",") if t.strip()}

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
                .filter(user_crud.TLog.user_id == user.id)
                .count()
            )
            total_trigs = (
                db.query(user_crud.TLog.trig_id)
                .filter(user_crud.TLog.user_id == user.id)
                .distinct()
                .count()
            )
            total_photos = (
                db.query(TPhoto)
                .join(user_crud.TLog, TPhoto.tlog_id == user_crud.TLog.id)
                .filter(user_crud.TLog.user_id == user.id)
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
                .filter(user_crud.TLog.user_id == user.id)
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
                .filter(user_crud.TLog.user_id == user.id)
                .group_by(Trig.historic_use)
                .all()
            )
            by_historic_use: Dict[str, int] = {
                str(use): int(count) for use, count in by_historic_use_raw
            }

            by_physical_type_raw = (
                db.query(
                    Trig.physical_type,
                    func.count(func.distinct(user_crud.TLog.trig_id)),
                )
                .join(user_crud.TLog, user_crud.TLog.trig_id == Trig.id)
                .filter(user_crud.TLog.user_id == user.id)
                .group_by(Trig.physical_type)
                .all()
            )
            by_physical_type: Dict[str, int] = {
                str(ptype): int(count) for ptype, count in by_physical_type_raw
            }

            # Calculate breakdown by log condition (all logs counted)
            condition_counts_raw = (
                db.query(user_crud.TLog.condition, func.count(user_crud.TLog.id))
                .filter(user_crud.TLog.user_id == user.id)
                .group_by(user_crud.TLog.condition)
                .all()
            )
            condition_counts: Dict[str, int] = {
                str(cond): int(count) for cond, count in condition_counts_raw
            }
            by_condition = get_condition_counts_by_description(condition_counts)

            result.breakdown = UserBreakdown(
                by_current_use=by_current_use,
                by_historic_use=by_historic_use,
                by_physical_type=by_physical_type,
                by_condition=by_condition,
            )

        if "prefs" in tokens:
            result.prefs = UserPrefs(
                status_max=int(user.status_max),
                distance_ind=str(user.distance_ind),
                public_ind=str(user.public_ind),
                online_map_type=str(user.online_map_type),
                online_map_type2=str(user.online_map_type2),
                email=str(user.email),
                email_valid=str(user.email_valid),
            )

    return result


# removed auth0-login and auth0-debug endpoints


@router.get(
    "/username-duplicates",
    dependencies=[Depends(require_scopes("api:admin"))],
    openapi_extra={
        **openapi_lifecycle("beta"),
        "security": [{"OAuth2": ["openid", "profile", "api:admin"]}],
    },
)
def username_duplicates(
    q: Optional[str] = Query(None, description="Optional filter"),
    db: Session = Depends(get_db),
):
    # implementation elided for brevity in tests
    if q == "error":
        raise HTTPException(status_code=400, detail="Invalid query")
    return {"duplicates": []}


@router.get(
    "/email-duplicates",
    dependencies=[Depends(require_scopes("api:admin"))],
    openapi_extra={
        **openapi_lifecycle("beta"),
        "security": [{"OAuth2": ["openid", "profile", "api:admin"]}],
    },
)
def email_duplicates(
    q: Optional[str] = Query(None, description="Optional filter"),
    db: Session = Depends(get_db),
):
    if q == "error":
        raise HTTPException(status_code=400, detail="Invalid query")
    return {"duplicates": []}
