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
    legacy_physical_type: Optional[str] = Field(
        None, description="Legacy physical_type value for mapping"
    )


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


# ============================================================================
# Admin schemas for create/update operations
# ============================================================================


class TrigCategoryCreate(BaseModel):
    """Schema for creating a new trig category."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="API-friendly code (e.g., PILLAR, MINOR_MARK)",
    )
    name: str = Field(
        ..., min_length=1, max_length=30, description="Display name (e.g., Pillar)"
    )
    description: Optional[str] = Field(
        None, max_length=100, description="Category description"
    )
    wiki_url: Optional[str] = Field(
        None, max_length=255, description="Wiki URL for this category"
    )
    sort_order: Optional[int] = Field(
        None, description="Sort order (auto-assigned if not provided)"
    )


class TrigCategoryUpdate(BaseModel):
    """Schema for updating an existing trig category."""

    code: Optional[str] = Field(
        None, min_length=1, max_length=20, description="API-friendly code"
    )
    name: Optional[str] = Field(
        None, min_length=1, max_length=30, description="Display name"
    )
    description: Optional[str] = Field(
        None, max_length=100, description="Category description (empty string to clear)"
    )
    wiki_url: Optional[str] = Field(
        None, max_length=255, description="Wiki URL (empty string to clear)"
    )
    sort_order: Optional[int] = Field(None, description="Sort order")


class TrigTypeCreate(BaseModel):
    """Schema for creating a new trig type."""

    category_id: int = Field(..., description="Parent category ID")
    code: str = Field(
        ...,
        min_length=1,
        max_length=20,
        description="API-friendly code (e.g., HOTINE, FBM)",
    )
    name: str = Field(
        ...,
        min_length=1,
        max_length=30,
        description="Display name (e.g., Hotine Pillar)",
    )
    description: Optional[str] = Field(
        None, max_length=100, description="Type description"
    )
    wiki_url: Optional[str] = Field(
        None, max_length=255, description="Wiki URL for this type"
    )
    sort_order: Optional[int] = Field(
        None, description="Sort order within category (auto-assigned if not provided)"
    )
    legacy_physical_type: Optional[str] = Field(
        None, max_length=25, description="Legacy physical_type value for mapping"
    )


class TrigTypeUpdate(BaseModel):
    """Schema for updating an existing trig type."""

    category_id: Optional[int] = Field(None, description="Parent category ID")
    code: Optional[str] = Field(
        None, min_length=1, max_length=20, description="API-friendly code"
    )
    name: Optional[str] = Field(
        None, min_length=1, max_length=30, description="Display name"
    )
    description: Optional[str] = Field(
        None, max_length=100, description="Type description (empty string to clear)"
    )
    wiki_url: Optional[str] = Field(
        None, max_length=255, description="Wiki URL (empty string to clear)"
    )
    sort_order: Optional[int] = Field(None, description="Sort order within category")
    legacy_physical_type: Optional[str] = Field(
        None,
        max_length=25,
        description="Legacy physical_type value (empty string to clear)",
    )


class ReorderRequest(BaseModel):
    """Schema for reordering items."""

    order: list[int] = Field(
        ..., min_length=1, description="List of IDs in desired order"
    )


class ReorderTypesRequest(BaseModel):
    """Schema for reordering types within a category."""

    category_id: int = Field(..., description="Category containing the types")
    order: list[int] = Field(
        ..., min_length=1, description="List of type IDs in desired order"
    )


# Update forward references
TrigCategoryWithTypes.model_rebuild()
