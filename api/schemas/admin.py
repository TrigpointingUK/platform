"""
Pydantic schemas for admin-specific operations.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class AdminUserSearchResult(BaseModel):
    """Schema representing a legacy user candidate for migration."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    email: str
    email_valid: str = Field(..., description="Legacy email verification flag (Y/N)")
    auth0_user_id: Optional[str] = Field(
        None, description="Auth0 user identifier if already migrated"
    )
    has_auth0_account: bool = Field(
        ..., description="Whether the user already has an Auth0 account"
    )


class AdminUserSearchResponse(BaseModel):
    """Collection wrapper for search results."""

    items: List[AdminUserSearchResult]


class AdminMigrationRequest(BaseModel):
    """Request payload for initiating an admin-triggered migration."""

    user_id: int = Field(..., description="Legacy database user identifier")
    email: EmailStr = Field(..., description="Email address to assign in Auth0")


class AdminReissueEmailRequest(BaseModel):
    """Request payload for re-issuing an Auth0 account against a new email."""

    user_id: int = Field(..., description="Legacy database user identifier")
    email: EmailStr = Field(..., description="New email address to assign in Auth0")


class AdminMigrationResponse(BaseModel):
    """Response payload for a successful migration."""

    user_id: int
    username: str
    email: EmailStr
    auth0_user_id: str
    message: str = Field(
        ...,
        description="Prepared message for the administrator to share with the user.",
    )


class AdminMergeUsersRequest(BaseModel):
    """Request to merge source user into target user."""

    target_user_id: int = Field(..., description="User ID to keep")
    source_user_id: int = Field(..., description="User ID to merge and delete")
    dry_run: bool = Field(
        True, description="If true, preview merge without executing it"
    )


class MergeRecordCounts(BaseModel):
    """Count of records affected during merge."""

    tlog: int = 0
    tphoto: int = 0  # Informational only (updated via tlog_id)
    tphotovote: int = 0


class AdminMergeUsersPreview(BaseModel):
    """Preview of merge operation showing what will change."""

    dry_run: bool = True
    target_user: Dict[str, Any] = Field(..., description="Current target user data")
    source_user: Dict[str, Any] = Field(..., description="Current source user data")
    estimated_records: MergeRecordCounts = Field(
        ..., description="Number of records that will be updated"
    )
    profile_updates: Dict[str, Optional[str]] = Field(
        ..., description="Profile fields that will be updated on target"
    )
    auth0_will_update: bool = Field(
        ..., description="Whether Auth0 synchronization will occur"
    )
    member_since: str = Field(
        ...,
        description="Earliest registration date/time across both accounts (YYYY-MM-DD HH:MM:SS)",
    )


class AdminMergeUsersResponse(BaseModel):
    """Result of successful merge execution."""

    success: bool = True
    target_user_id: int
    source_user_id: int
    updated_records: MergeRecordCounts = Field(
        ..., description="Number of records that were updated"
    )
    profile_updated: bool = Field(..., description="Whether target profile was updated")
    auth0_updated: bool = Field(..., description="Whether Auth0 was synchronized")
