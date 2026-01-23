"""
Pydantic schemas for condition admin operations.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class ConditionBase(BaseModel):
    """Base schema for condition fields."""

    name: str = Field(
        ...,
        max_length=50,
        description="Human-readable condition name (max 50 characters)",
    )
    sort_order: int = Field(..., ge=0, le=32767, description="Display sort order")


class ConditionCreate(ConditionBase):
    """Schema for creating a new condition."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=1,
        pattern=r"^[A-Z]$",
        description="Single uppercase letter code (primary key)",
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Optional description"
    )
    icon_file: Optional[str] = Field(
        None, max_length=100, description="Icon filename (e.g., 'c_good.png')"
    )
    trig_colour: Optional[str] = Field(
        None, max_length=20, description="Colour for trig display (e.g., 'green')"
    )
    log_colour: Optional[str] = Field(
        None, max_length=20, description="Colour for log display (e.g., 'red')"
    )
    similar_codes: Optional[str] = Field(
        None, max_length=10, description="Similar condition codes (e.g., 'GS')"
    )
    wiki_url: Optional[str] = Field(
        None, max_length=255, description="URL to wiki page"
    )


class ConditionUpdate(BaseModel):
    """Schema for updating an existing condition."""

    name: Optional[str] = Field(
        None, max_length=50, description="Human-readable condition name"
    )
    description: Optional[str] = Field(
        None, max_length=255, description="Optional description"
    )
    icon_file: Optional[str] = Field(None, max_length=100, description="Icon filename")
    trig_colour: Optional[str] = Field(
        None, max_length=20, description="Colour for trig display"
    )
    log_colour: Optional[str] = Field(
        None, max_length=20, description="Colour for log display"
    )
    similar_codes: Optional[str] = Field(
        None, max_length=10, description="Similar condition codes"
    )
    wiki_url: Optional[str] = Field(
        None, max_length=255, description="URL to wiki page"
    )
    sort_order: Optional[int] = Field(
        None, ge=0, le=32767, description="Display sort order"
    )


class ConditionResponse(BaseModel):
    """Response schema for condition."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., description="Single character condition code")
    name: str = Field(..., description="Human-readable condition name")
    description: Optional[str] = Field(None, description="Optional description")
    icon_file: Optional[str] = Field(None, description="Icon filename")
    trig_colour: Optional[str] = Field(None, description="Colour for trig display")
    log_colour: Optional[str] = Field(None, description="Colour for log display")
    similar_codes: Optional[str] = Field(None, description="Similar condition codes")
    wiki_url: Optional[str] = Field(None, description="URL to wiki page")
    sort_order: int = Field(..., description="Display sort order")


class ConditionUsageResponse(BaseModel):
    """Response schema for condition usage count."""

    code: str = Field(..., description="Condition code")
    usage_count: int = Field(..., description="Number of logs using this condition")
