"""
Pydantic schemas for status admin operations.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class StatusBase(BaseModel):
    """Base schema for status fields."""

    name: str = Field(
        ..., max_length=20, description="Short status name (max 20 characters)"
    )
    descr: str = Field(
        ..., max_length=50, description="Status description (max 50 characters)"
    )
    limit_descr: str = Field(
        ..., max_length=255, description="Limit description (max 255 characters)"
    )


class StatusCreate(StatusBase):
    """Schema for creating a new status."""

    id: int = Field(..., ge=0, description="Status ID (manually assigned)")


class StatusUpdate(BaseModel):
    """Schema for updating an existing status."""

    name: Optional[str] = Field(
        None, max_length=20, description="Short status name (max 20 characters)"
    )
    descr: Optional[str] = Field(
        None, max_length=50, description="Status description (max 50 characters)"
    )
    limit_descr: Optional[str] = Field(
        None, max_length=255, description="Limit description (max 255 characters)"
    )


class StatusResponse(StatusBase):
    """Response schema for status."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Status ID")


class StatusUsageResponse(BaseModel):
    """Response schema for status usage count."""

    status_id: int = Field(..., description="Status ID")
    usage_count: int = Field(..., description="Number of trigs using this status")
