"""
Pydantic schemas for historic use / recent use admin operations.

Name lengths match the trig columns they populate: historic_use is
VARCHAR(30) and current_use VARCHAR(25). The endpoints check the limit for
the kind being edited.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TrigUseCreate(BaseModel):
    """Schema for creating a new use value."""

    name: str = Field(
        ..., min_length=1, max_length=30, description="Value as stored on trigs"
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Optional description"
    )
    sort_order: int = Field(..., ge=0, le=32767, description="Display sort order")


class TrigUseUpdate(BaseModel):
    """Schema for updating an existing use value. Renaming updates the trigs."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=30, description="Value as stored on trigs"
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Optional description"
    )
    sort_order: Optional[int] = Field(
        None, ge=0, le=32767, description="Display sort order"
    )


class TrigUseResponse(BaseModel):
    """Response schema for a use value."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Value ID")
    name: str = Field(..., description="Value as stored on trigs")
    description: Optional[str] = Field(None, description="Optional description")
    sort_order: int = Field(..., description="Display sort order")


class TrigUseUsageResponse(BaseModel):
    """Response schema for use value usage count."""

    id: int = Field(..., description="Value ID")
    usage_count: int = Field(..., description="Number of trigs using this value")
