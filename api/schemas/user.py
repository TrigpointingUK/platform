"""
Pydantic schemas for user endpoints with permission-based field filtering.
"""

import re
from datetime import date  # noqa: F401
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UserResponse(BaseModel):
    """Dynamic user response that adapts fields based on permissions."""

    model_config = ConfigDict(from_attributes=True)

    # Always included
    id: int
    name: str
    firstname: Optional[str] = None  # Nullable for PostgreSQL compatibility
    surname: Optional[str] = None  # Nullable for PostgreSQL compatibility
    homepage: Optional[str] = Field(None, description="User homepage URL")
    about: Optional[str] = Field(None, description="About/description text")
    has_avatar: bool = Field(False, description="Whether the user has a custom avatar")
    member_since: Optional[date] = Field(None, description="Date user joined")
    auth0_user_id: Optional[str] = Field(
        None, description="Auth0 user ID (own profile only)"
    )


class UserStats(BaseModel):
    total_logs: int
    total_trigs_logged: int
    total_photos: int


class UserSortField(str, Enum):
    """Supported sort keys for user listings."""

    TRIGPOINTS = "trigs"
    PHOTOS = "photos"
    LOGS = "logs"
    JOINED = "joined"
    NAME = "name"


class SortDirection(str, Enum):
    """Sort ordering for user listings."""

    ASC = "asc"
    DESC = "desc"


class UserListItem(BaseModel):
    """Slim user representation for directory responses."""

    id: int
    name: str
    has_avatar: bool = False
    member_since: Optional[date] = None
    stats: UserStats
    profile_path: str


class UserListFilters(BaseModel):
    """Echoed filter metadata for user directory responses."""

    query: Optional[str] = None
    sort: UserSortField = UserSortField.TRIGPOINTS
    direction: SortDirection = SortDirection.DESC
    limit: int = 40


class UserListResponse(BaseModel):
    """Cursor-based directory response."""

    items: list[UserListItem]
    next_cursor: Optional[str] = None
    total: int
    applied_filters: UserListFilters


class TypeCount(BaseModel):
    """Count of trigpoints logged for a specific type."""

    type_code: str = Field(..., description="Type code (e.g., HOTINE)")
    type_name: str = Field(..., description="Type display name")
    count: int = Field(..., description="Number of distinct trigpoints logged")


class CategoryTypeBreakdown(BaseModel):
    """Breakdown of types within a category."""

    category_code: str = Field(..., description="Category code (e.g., PILLAR)")
    category_name: str = Field(..., description="Category display name")
    sort_order: int = Field(..., description="Category sort order")
    types: list[TypeCount] = Field(
        [], description="Types within this category, sorted by count descending"
    )


class UserBreakdown(BaseModel):
    # Breakdown by trig characteristics (distinct trigpoints only)
    by_current_use: Dict[str, int] = Field(
        {}, description="Trigpoints logged grouped by current use"
    )
    by_historic_use: Dict[str, int] = Field(
        {}, description="Trigpoints logged grouped by historic use"
    )
    by_type: list[CategoryTypeBreakdown] = Field(
        [],
        description="Trigpoints logged grouped by category and type, sorted by category sort_order",
    )

    # Breakdown by log condition (all logs counted)
    by_condition: Dict[str, int] = Field(
        {}, description="All logs grouped by condition"
    )


class UserPrefs(BaseModel):
    distance_ind: str
    public_ind: str
    email: str
    email_valid: str = Field(
        ..., description="Email validation status (Y/N) - read-only"
    )
    archive_frequency: str = Field(
        "N",
        description="Archive email frequency: N=never, Y=yearly, M=monthly-if-active-else-yearly, W=weekly-if-active-else-monthly",
    )
    archive_format: str = Field(
        "C",
        description="Archive email format: C=CSV only, J=CSV+JSON, R=CSV+JSON+reader",
    )
    ui_prefs: Optional[Dict[str, Any]] = Field(
        None,
        description="UI preferences (distance_ind, show_trig_condition, default_groups, etc.)",
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
    distance_ind: Optional[str] = Field(
        None, pattern="^[KM]$", description="Distance units (K=km, M=miles)"
    )
    public_ind: Optional[str] = Field(
        None, pattern="^[YN]$", description="Public visibility (Y/N)"
    )
    archive_frequency: Optional[str] = Field(
        None,
        pattern="^[NYMW]$",
        description="Archive email frequency: N=never, Y=yearly, M=monthly-if-active, W=weekly-if-active",
    )
    archive_format: Optional[str] = Field(
        None,
        pattern="^[CJR]$",
        description="Archive email format: C=CSV only, J=CSV+JSON, R=CSV+JSON+reader",
    )
    ui_prefs: Optional[Dict[str, Any]] = Field(
        None,
        description="UI preferences (distance_ind, show_trig_condition, default_groups, etc.)",
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

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Database user ID")
    name: str = Field(..., description="Username")
    email: str = Field(..., description="Email address")
    auth0_user_id: str = Field(..., description="Auth0 user ID")


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
