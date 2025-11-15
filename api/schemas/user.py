"""
Pydantic schemas for user endpoints with permission-based field filtering.
"""

import re
from datetime import date  # noqa: F401
from typing import Dict, Optional

from pydantic import BaseModel, Field, field_validator


class UserResponse(BaseModel):
    """Dynamic user response that adapts fields based on permissions."""

    # Always included
    id: int
    name: str
    firstname: str
    surname: str
    homepage: Optional[str] = Field(None, description="User homepage URL")
    about: Optional[str] = Field(None, description="About/description text")
    member_since: Optional[date] = Field(None, description="Date user joined")
    auth0_user_id: Optional[str] = Field(
        None, description="Auth0 user ID (own profile only)"
    )

    class Config:
        from_attributes = True


class UserStats(BaseModel):
    total_logs: int
    total_trigs_logged: int
    total_photos: int


class UserBreakdown(BaseModel):
    # Breakdown by trig characteristics (distinct trigpoints only)
    by_current_use: Dict[str, int] = Field(
        {}, description="Trigpoints logged grouped by current use"
    )
    by_historic_use: Dict[str, int] = Field(
        {}, description="Trigpoints logged grouped by historic use"
    )
    by_physical_type: Dict[str, int] = Field(
        {}, description="Trigpoints logged grouped by physical type"
    )

    # Breakdown by log condition (all logs counted)
    by_condition: Dict[str, int] = Field(
        {}, description="All logs grouped by condition"
    )


class UserPrefs(BaseModel):
    status_max: int
    distance_ind: str
    public_ind: str
    online_map_type: str
    online_map_type2: str
    email: str
    email_valid: str = Field(
        ..., description="Email validation status (Y/N) - read-only"
    )


class UserUpdate(BaseModel):
    """Schema for updating user preferences and profile information."""

    # Profile fields that sync to Auth0
    name: Optional[str] = Field(
        None,
        min_length=1,
        max_length=30,
        description="Username/nickname (syncs to Auth0)",
    )
    email: Optional[str] = Field(
        None, max_length=255, description="Email address (syncs to Auth0)"
    )

    # Profile fields (database only)
    firstname: Optional[str] = Field(
        None, max_length=30, description="First name (database only)"
    )
    surname: Optional[str] = Field(
        None, max_length=30, description="Surname (database only)"
    )
    homepage: Optional[str] = Field(
        None, max_length=255, description="User homepage URL"
    )
    about: Optional[str] = Field(None, description="About/description text")

    # Preference fields
    status_max: Optional[int] = Field(None, description="Status preference")
    distance_ind: Optional[str] = Field(
        None, pattern="^[KM]$", description="Distance units (K=km, M=miles)"
    )
    public_ind: Optional[str] = Field(
        None, pattern="^[YN]$", description="Public visibility (Y/N)"
    )
    online_map_type: Optional[str] = Field(
        None, max_length=10, description="Primary map type preference"
    )
    online_map_type2: Optional[str] = Field(
        None, max_length=10, description="Secondary map type preference"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v

        # Ban leading whitespace
        if v != v.lstrip():
            raise ValueError("Username cannot begin with whitespace")

        # Blacklist characters: @ and * (prevent SQL injection-like garbage)
        forbidden_chars = ["@", "*"]
        for char in forbidden_chars:
            if char in v:
                raise ValueError(f"Username cannot contain '{char}' character")

        return v

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v

        # Basic email format validation
        # Pattern: local@domain with reasonable restrictions
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email address format")

        return v


class UserWithIncludes(UserResponse):
    stats: Optional[UserStats] = None
    breakdown: Optional[UserBreakdown] = None
    prefs: Optional[UserPrefs] = None
    roles: Optional[list[str]] = Field(
        None, description="Auth0 roles (own profile only)"
    )

    class Config:
        from_attributes = True


class Auth0UserInfo(BaseModel):
    """Auth0 user information from token without database lookup."""

    # Auth0 user details
    auth0_user_id: str = Field(..., description="Auth0 user ID")
    email: Optional[str] = Field(None, description="Email address from Auth0")
    nickname: Optional[str] = Field(None, description="Nickname from Auth0")
    name: Optional[str] = Field(None, description="Display name from Auth0")
    given_name: Optional[str] = Field(None, description="Given name from Auth0")
    family_name: Optional[str] = Field(None, description="Family name from Auth0")
    email_verified: Optional[bool] = Field(None, description="Email verified status")

    # Token metadata
    token_type: str = Field(..., description="Token type (auth0)")
    audience: Optional[list[str] | str] = Field(
        None, description="Token audience (string or list as provided in token)"
    )
    issuer: Optional[str] = Field(None, description="Token issuer")
    expires_at: Optional[int] = Field(None, description="Token expiration timestamp")
    scopes: Optional[list[str]] = Field(None, description="Scopes/permissions in token")

    # Database lookup status
    database_user_found: bool = Field(
        ..., description="Whether user was found in database"
    )
    database_user_id: Optional[int] = Field(
        None, description="Database user ID if found"
    )
    database_username: Optional[str] = Field(
        None, description="Database username if found"
    )
    database_email: Optional[str] = Field(None, description="Database email if found")


class UserCreate(BaseModel):
    """Schema for creating a new user from Auth0 webhook."""

    username: str = Field(
        ..., min_length=1, max_length=30, description="Username/nickname from Auth0"
    )
    email: str = Field(
        ..., min_length=1, max_length=255, description="Email address from Auth0"
    )
    auth0_user_id: str = Field(
        ..., min_length=1, max_length=50, description="Auth0 user ID"
    )


class UserCreateResponse(BaseModel):
    """Response schema for created user."""

    id: int = Field(..., description="Database user ID")
    name: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    auth0_user_id: str = Field(..., description="Auth0 user ID")

    class Config:
        from_attributes = True


class LegacyLoginRequest(BaseModel):
    """Request schema for legacy login endpoint (bridge to Auth0)."""

    username: str = Field(
        ..., min_length=1, max_length=30, description="Username for login"
    )
    password: str = Field(..., min_length=1, description="Password for authentication")
    email: Optional[str] = Field(
        None,
        min_length=1,
        max_length=255,
        description="Optional email address for Auth0 sync",
    )
    include: Optional[str] = Field(
        None,
        description="Comma-separated list of includes: stats,breakdown,prefs",
    )

    @field_validator("username")
    @classmethod
    def validate_username_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Username is required")
        return v.strip()

    @field_validator("password")
    @classmethod
    def validate_password_required(cls, v: str) -> str:
        if not v:
            raise ValueError("Password is required")
        return v

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: Optional[str]) -> Optional[str]:
        # Email is optional, but if provided, must be valid
        if v is None or not v.strip():
            return None

        # Basic email format validation
        email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        if not re.match(email_pattern, v.strip()):
            raise ValueError("Invalid email address format")

        return v.strip()


class LegacyLoginResponse(UserWithIncludes):
    """
    Response schema for legacy login endpoint.

    This endpoint serves as a bridge between the legacy login system
    and the new Auth0 system, synchronising user email addresses and
    triggering verification emails when needed.
    """

    email: str = Field(..., description="User email address")
    email_valid: str = Field(..., description="Email validation status (Y/N)")


class UserMigrationRequest(BaseModel):
    """Request schema for user migration to Auth0."""

    limit: int = Field(
        ...,
        ge=1,
        le=1000,
        description="Maximum number of unique email addresses to process",
    )
    dry_run: bool = Field(
        ..., description="If true, only simulate migration without making changes"
    )
    send_confirmation_email: bool = Field(
        default=False,
        description="If true, send verification email to migrated users",
    )


class UserMigrationAction(BaseModel):
    """Details about a single user migration action."""

    email: str = Field(..., description="Email address being migrated")
    database_user_id: int = Field(..., description="Database user ID")
    database_username: str = Field(..., description="Database username")
    action: str = Field(
        ...,
        description="Action taken: 'skipped_dry_run', 'created', 'failed', or 'skipped_error'",
    )
    auth0_user_id: Optional[str] = Field(
        None, description="Auth0 user ID if user was created"
    )
    verification_email_sent: Optional[bool] = Field(
        None, description="Whether verification email was sent"
    )
    error: Optional[str] = Field(None, description="Error message if action failed")


class UserMigrationResponse(BaseModel):
    """Response schema for user migration endpoint."""

    total_unique_emails_found: int = Field(
        ..., description="Total number of unique email addresses found for migration"
    )
    total_processed: int = Field(..., description="Total number of users processed")
    dry_run: bool = Field(..., description="Whether this was a dry run")
    actions: list[UserMigrationAction] = Field(
        ..., description="Detailed list of actions taken for each email"
    )
