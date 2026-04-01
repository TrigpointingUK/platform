from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.core.security import auth0_validator, extract_scopes
from api.crud.user import get_user_by_auth0_id, get_user_by_email, get_user_by_name
from api.schemas.user import Auth0UserInfo

router = APIRouter()
security = HTTPBearer(auto_error=False)


@router.get("/auth0", response_model=Auth0UserInfo)
def get_auth0_debug(
    credentials=Depends(security),
    db: Session = Depends(get_db),
):
    """
    Debug Auth0 token: echoes token claims and related DB mapping info.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_payload = auth0_validator.validate_auth0_token(credentials.credentials)
    if not token_payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token_type = token_payload.get("token_type", "auth0")
    auth0_user_id = token_payload.get("auth0_user_id") or token_payload.get("sub", "")

    database_user_found = False
    database_user_id: Optional[int] = None
    database_username: Optional[str] = None
    database_email: Optional[str] = None

    if token_type == "auth0" and auth0_user_id:  # nosec B105
        user = get_user_by_auth0_id(db, auth0_user_id=auth0_user_id)
        if user:
            database_user_found = True
            database_user_id = int(user.id)
            database_username = str(user.name)
            database_email = str(user.email) if user.email else None
        else:
            email = token_payload.get("email")
            display_name = token_payload.get("nickname") or token_payload.get("name")
            if email:
                user = get_user_by_email(db, email)
                if user:
                    database_user_found = True
                    database_user_id = int(user.id)
                    database_username = str(user.name)
                    database_email = str(user.email) if user.email else None
            if not database_user_found and display_name:
                user = get_user_by_name(db, display_name)
                if user:
                    database_user_found = True
                    database_user_id = int(user.id)
                    database_username = str(user.name)
                    database_email = str(user.email) if user.email else None

    return Auth0UserInfo(
        auth0_user_id=auth0_user_id,
        email=token_payload.get("email"),
        # Removed username field; rely on nickname/name
        nickname=token_payload.get("nickname"),
        name=token_payload.get("name"),
        given_name=token_payload.get("given_name"),
        family_name=token_payload.get("family_name"),
        email_verified=token_payload.get("email_verified"),
        token_type=token_type,
        audience=token_payload.get("aud"),
        issuer=token_payload.get("iss"),
        expires_at=token_payload.get("exp"),
        scopes=list(extract_scopes(token_payload)) if token_payload else [],
        database_user_found=database_user_found,
        database_user_id=database_user_id,
        database_username=database_username,
        database_email=database_email,
    )
