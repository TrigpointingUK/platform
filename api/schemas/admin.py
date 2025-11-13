"""
Pydantic schemas for admin-specific operations.
"""

from typing import List, Optional

from pydantic import BaseModel, EmailStr, Field


class AdminUserSearchResult(BaseModel):
    """Schema representing a legacy user candidate for migration."""

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

    class Config:
        from_attributes = True


class AdminUserSearchResponse(BaseModel):
    """Collection wrapper for search results."""

    items: List[AdminUserSearchResult]


class AdminMigrationRequest(BaseModel):
    """Request payload for initiating an admin-triggered migration."""

    user_id: int = Field(..., description="Legacy database user identifier")
    email: EmailStr = Field(..., description="Email address to assign in Auth0")


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
