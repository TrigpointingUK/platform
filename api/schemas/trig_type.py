"""
Pydantic schemas for trig_type and trig_type_group endpoints.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TrigTypeGroupBase(BaseModel):
    """Base schema for trig type group."""

    code: str = Field(..., description="API-friendly code (e.g., PILLAR, MINOR_MARK)")
    name: str = Field(..., description="Display name (e.g., Pillar, Minor mark)")
    description: Optional[str] = Field(None, description="Group description")
    wiki_url: Optional[str] = Field(None, description="Wiki URL for this group")
    sort_order: int = Field(..., description="Sort order for threshold filtering")


class TrigTypeGroupResponse(TrigTypeGroupBase):
    """Response schema for trig type group."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Group ID")


class TrigTypeGroupWithTypes(TrigTypeGroupResponse):
    """Response schema for trig type group with nested types."""

    types: list["TrigTypeResponse"] = Field(
        default_factory=list, description="Types in this group"
    )


class TrigTypeBase(BaseModel):
    """Base schema for trig type."""

    code: str = Field(..., description="API-friendly code (e.g., HOTINE, FBM, BOLT)")
    name: str = Field(
        ..., description="Display name (e.g., Hotine Pillar, Flush Bracket)"
    )
    description: Optional[str] = Field(None, description="Type description")
    wiki_url: Optional[str] = Field(None, description="Wiki URL for this type")
    sort_order: int = Field(..., description="Sort order within group")


class TrigTypeResponse(TrigTypeBase):
    """Response schema for trig type."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Type ID")
    group_id: int = Field(..., description="Parent group ID")


class TrigTypeWithGroup(TrigTypeResponse):
    """Response schema for trig type with nested group."""

    group: TrigTypeGroupResponse = Field(..., description="Parent group")


class TrigTypeMinimal(BaseModel):
    """Minimal type info for embedding in trig responses."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., description="Type code")
    name: str = Field(..., description="Type display name")
    group_code: Optional[str] = Field(None, description="Parent group code")
    group_name: Optional[str] = Field(None, description="Parent group name")


# Update forward references
TrigTypeGroupWithTypes.model_rebuild()
