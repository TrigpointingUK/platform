"""
API dependencies for authentication and database access.
"""

# from typing import Generator  # Currently unused

from typing import Optional

# from api.schemas.user import TokenData
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.core.security import auth0_validator, extract_scopes
from api.crud.user import (
    get_user_by_auth0_id,
    get_user_by_email,
    get_user_by_name,
    update_user_auth0_mapping,
)
from api.db.database import get_db
from api.models.user import User

security = HTTPBearer(auto_error=False)


def get_current_user(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Get current authenticated user (Auth0 bearer only when enabled)."""
    from api.core.logging import get_logger

    logger = get_logger(__name__)
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        logger.warning("No credentials provided to get_current_user")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token (Auth0-only when enabled)
    token_payload = auth0_validator.validate_auth0_token(credentials.credentials)
    if not token_payload:
        logger.warning("Token validation failed in get_current_user")
        raise credentials_exception

    logger.info(
        "Auth0 token validated successfully",
        extra={
            "auth0_user_id": token_payload.get("auth0_user_id"),
        },
    )

    # For Auth0 tokens, find user by Auth0 user ID
    if token_payload.get("token_type") == "auth0":
        auth0_user_id = token_payload.get("auth0_user_id")
        if not auth0_user_id:
            raise credentials_exception
        user = get_user_by_auth0_id(db, auth0_user_id=auth0_user_id)
        if user is None:
            # User not found in database - try to sync from Auth0
            from api.core.logging import get_logger
            from api.services.auth0_service import auth0_service

            logger = get_logger(__name__)
            logger.info(
                f"Auth0 user not found in database, attempting sync: {auth0_user_id}",
                extra={
                    "auth0_user_id": auth0_user_id,
                    "token_email": token_payload.get("email"),
                    "token_nickname": token_payload.get("nickname"),
                    "token_name": token_payload.get("name"),
                },
            )

            # Get Auth0 user details
            auth0_user = auth0_service.find_user_by_auth0_id(auth0_user_id)
            if auth0_user:
                # Try to find user by email or display name from Auth0 data
                email = auth0_user.get("email")
                display_name = auth0_user.get("nickname") or auth0_user.get("name")

                logger.info(
                    "Auth0 user details retrieved, searching database",
                    extra={
                        "auth0_email": email,
                        "auth0_display_name": display_name,
                    },
                )

                # Try to find existing user by email first
                if email:
                    user = get_user_by_email(db, email)
                    if user:
                        logger.info(
                            f"Found user by email: {email} -> user_id {user.id}"
                        )

                # If not found by email, try by display name (nickname/name)
                if not user and display_name:
                    user = get_user_by_name(db, display_name)
                    if user:
                        logger.info(
                            f"Found user by name: {display_name} -> user_id {user.id}"
                        )

                # If user found, update their Auth0 mapping (ID + username)
                if user:
                    update_user_auth0_mapping(
                        db,
                        int(user.id),
                        auth0_user_id,
                    )
                    logger.info(f"Updated user {user.id} with Auth0 ID {auth0_user_id}")
                    setattr(user, "_token_payload", token_payload)
                    return user
                else:
                    logger.warning(
                        f"No matching user found in database for Auth0 user {auth0_user_id}",
                        extra={
                            "auth0_email": email,
                            "auth0_display_name": display_name,
                        },
                    )
            else:
                logger.warning(
                    f"Could not retrieve Auth0 user details for {auth0_user_id}"
                )

            # If no user found or Auth0 sync failed, raise credentials exception
            raise credentials_exception
        setattr(user, "_token_payload", token_payload)
        return user

    # Only Auth0 tokens are supported
    raise credentials_exception


def get_current_user_optional(
    db: Session = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Get current user from token, returning None if not authenticated."""
    if credentials is None:
        return None

    try:
        token_payload = auth0_validator.validate_auth0_token(credentials.credentials)
        if not token_payload:
            return None

        if token_payload.get("token_type") == "auth0":
            auth0_user_id = token_payload.get("auth0_user_id")
            if not auth0_user_id:
                return None
            user = get_user_by_auth0_id(db, auth0_user_id=auth0_user_id)
            if user is None:
                # User not found in database - try to sync from Auth0
                from api.services.auth0_service import auth0_service

                # Get Auth0 user details
                auth0_user = auth0_service.find_user_by_auth0_id(auth0_user_id)
                if auth0_user:
                    # Try to find user by email or display name from Auth0 data
                    email = auth0_user.get("email")
                    display_name = auth0_user.get("nickname") or auth0_user.get("name")

                    # Try to find existing user by email first
                    if email:
                        user = get_user_by_email(db, email)

                    # If not found by email, try by display name (nickname/name)
                    if not user and display_name:
                        user = get_user_by_name(db, display_name)

                    # If user found, update their Auth0 mapping (ID + username)
                    if user:
                        update_user_auth0_mapping(
                            db,
                            int(user.id),
                            auth0_user_id,
                        )
                        setattr(user, "_token_payload", token_payload)
                        return user
            if user:
                setattr(user, "_token_payload", token_payload)
            return user

    except Exception:
        return None

    return None


class _TokenContext(BaseModel):
    token_payload: dict


def get_token_context(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> _TokenContext:
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token_payload = auth0_validator.validate_auth0_token(credentials.credentials)
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return _TokenContext(token_payload=token_payload)


def require_scopes(*required_scopes: str):
    def _dep(
        ctx: _TokenContext = Depends(get_token_context),
        db: Session = Depends(get_db),
    ) -> User:
        token_payload = ctx.token_payload
        token_type = token_payload.get("token_type")

        if token_type == "auth0":  # nosec B105
            scopes = extract_scopes(token_payload)
            missing = [s for s in required_scopes if s not in scopes]
            if missing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Missing required scope(s): {', '.join(missing)}",
                )
            auth0_user_id = token_payload.get("auth0_user_id")
            user = (
                get_user_by_auth0_id(db, auth0_user_id=auth0_user_id)
                if auth0_user_id
                else None
            )
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found",
                )
        else:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Only Auth0 tokens are supported",
            )

        setattr(user, "_token_payload", token_payload)
        return user

    return _dep


def has_scope(token_payload: dict, scope: str) -> bool:
    """Check if token has specific scope."""
    scopes = extract_scopes(token_payload)
    return scope in scopes


def require_admin():
    """Require api:admin scope."""

    def _dep(
        current_user: User = Depends(get_current_user),
    ) -> User:
        token_payload = getattr(current_user, "_token_payload", None)
        if not token_payload:
            raise HTTPException(status_code=403, detail="Access denied")

        if not has_scope(token_payload, "api:admin"):
            raise HTTPException(
                status_code=403, detail="Missing required scope: api:admin"
            )
        return current_user

    return _dep


def require_owner_or_admin(resource_user_id: int):
    """Require ownership of resource OR api:admin scope."""

    def _dep(
        current_user: User = Depends(get_current_user),
    ) -> User:
        if int(current_user.id) == int(resource_user_id):
            return current_user

        token_payload = getattr(current_user, "_token_payload", None)
        if not token_payload:
            raise HTTPException(status_code=403, detail="Access denied")

        if not has_scope(token_payload, "api:admin"):
            raise HTTPException(
                status_code=403,
                detail="Must be resource owner or have api:admin scope",
            )
        return current_user

    return _dep


def verify_m2m_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """
    Verify M2M (Machine-to-Machine) token for Auth0 webhook endpoints.

    This dependency validates tokens from Auth0 Actions calling the webhook endpoint.
    Uses the Management API audience for validation.

    Fallback: If M2M token validation fails, checks for X-Webhook-Secret header
    with shared secret (for quota exhaustion scenarios).

    Returns:
        dict: Token payload (or mock payload if using shared secret)

    Raises:
        HTTPException: If token is missing or invalid
    """
    from api.core.logging import get_logger

    logger = get_logger(__name__)

    if credentials is None:
        logger.warning("M2M token validation failed: no credentials provided")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Validate token using auth0_validator with Management API audience
    # The validator will check against AUTH0_API_AUDIENCE
    token_payload = auth0_validator.validate_m2m_token(credentials.credentials)

    if not token_payload:
        logger.warning("M2M token validation failed: invalid token")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid M2M token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    logger.info(
        "M2M token validated successfully",
        extra={
            "audience": token_payload.get("aud"),
            "client_id": token_payload.get("azp", token_payload.get("client_id")),
        },
    )

    return token_payload


def verify_webhook_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    x_webhook_secret: Optional[str] = Header(None),
) -> dict:
    """
    Verify authentication for Auth0 webhook endpoints with shared secret fallback.

    Primary: M2M token validation
    Fallback: Shared secret in X-Webhook-Secret header (for M2M quota exhaustion)

    Args:
        credentials: Bearer token credentials
        x_webhook_secret: Value from X-Webhook-Secret header

    Returns:
        dict: Token payload (or mock payload if using shared secret)

    Raises:
        HTTPException: If authentication fails
    """
    from api.core.config import settings
    from api.core.logging import get_logger

    logger = get_logger(__name__)

    # Try M2M token first
    if credentials is not None:
        token_payload = auth0_validator.validate_m2m_token(credentials.credentials)
        if token_payload:
            logger.info(
                "Webhook authenticated via M2M token",
                extra={
                    "audience": token_payload.get("aud"),
                    "client_id": token_payload.get(
                        "azp", token_payload.get("client_id")
                    ),
                },
            )
            return token_payload

    # Fallback to shared secret if configured
    if settings.WEBHOOK_SHARED_SECRET and x_webhook_secret:
        if x_webhook_secret == settings.WEBHOOK_SHARED_SECRET:
            logger.warning(
                "Webhook authenticated via shared secret fallback",
                extra={"note": "M2M token quota may be exhausted"},
            )
            # Return mock payload for webhook
            return {"token_type": "webhook_shared_secret", "client_id": "webhook"}

    logger.error("Webhook authentication failed: no valid token or shared secret")
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication - provide valid M2M token or shared secret",
        headers={"WWW-Authenticate": "Bearer"},
    )
