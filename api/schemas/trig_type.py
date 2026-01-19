"""
Pydantic schemas for trig_type and trig_category endpoints.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TrigCategoryBase(BaseModel):
    """Base schema for trig category."""

    code: str = Field(..., description="API-friendly code (e.g., PILLAR, MINOR_MARK)")
    name: str = Field(..., description="Display name (e.g., Pillar, Minor mark)")
    description: Optional[str] = Field(None, description="Category description")
    wiki_url: Optional[str] = Field(None, description="Wiki URL for this category")
    sort_order: int = Field(..., description="Sort order for threshold filtering")


class TrigCategoryResponse(TrigCategoryBase):
    """Response schema for trig category."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Category ID")


class TrigCategoryWithTypes(TrigCategoryResponse):
    """Response schema for trig category with nested types."""

    types: list["TrigTypeResponse"] = Field(
        default_factory=list, description="Types in this category"
    )


class TrigTypeBase(BaseModel):
    """Base schema for trig type."""

    code: str = Field(..., description="API-friendly code (e.g., HOTINE, FBM, BOLT)")
    name: str = Field(
        ..., description="Display name (e.g., Hotine Pillar, Flush Bracket)"
    )
    description: Optional[str] = Field(None, description="Type description")
    wiki_url: Optional[str] = Field(None, description="Wiki URL for this type")
    sort_order: int = Field(..., description="Sort order within category")


class TrigTypeResponse(TrigTypeBase):
    """Response schema for trig type."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Type ID")
    category_id: int = Field(..., description="Parent category ID")


class TrigTypeWithCategory(TrigTypeResponse):
    """Response schema for trig type with nested category."""

    category: TrigCategoryResponse = Field(..., description="Parent category")


class TrigTypeMinimal(BaseModel):
    """Minimal type info for embedding in trig responses."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., description="Type code")
    name: str = Field(..., description="Type display name")
    category_code: Optional[str] = Field(None, description="Parent category code")
    category_name: Optional[str] = Field(None, description="Parent category name")


# Update forward references
TrigCategoryWithTypes.model_rebuild()
