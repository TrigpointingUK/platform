"""
Pydantic schemas for trig variant admin operations.

Lengths match the trig_variant columns. Codes are fixed once created: the
variant code is used in `variants=` filter links and the group code in
trig_type.variant_group.
"""

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class TrigVariantCreate(BaseModel):
    """
    Schema for creating a variant. Naming a group code that doesn't exist yet
    starts a new group, which then needs a group name.
    """

    group_code: str = Field(
        ..., min_length=1, max_length=20, description="Group code, e.g. DETECTOR"
    )
    group_name: Optional[str] = Field(
        None,
        max_length=30,
        description="Group name, for a new group (an existing group keeps its own)",
    )
    code: str = Field(
        ..., min_length=1, max_length=20, description="Variant code, e.g. CONCRETE_RING"
    )
    name: str = Field(..., min_length=1, max_length=30, description="Display name")
    sort_order: int = Field(
        ..., ge=0, le=32767, description="Display order within the group"
    )


class TrigVariantUpdate(BaseModel):
    """Schema for updating a variant. Its code and group can't change."""

    name: Optional[str] = Field(
        None, min_length=1, max_length=30, description="Display name"
    )
    sort_order: Optional[int] = Field(
        None, ge=0, le=32767, description="Display order within the group"
    )


class VariantGroupUpdate(BaseModel):
    """Schema for renaming a variant group. Its code can't change."""

    name: str = Field(..., min_length=1, max_length=30, description="Group name")


class TrigVariantResponse(BaseModel):
    """Response schema for a variant."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Variant ID")
    group_code: str = Field(..., description="Group code")
    group_name: str = Field(..., description="Group name")
    code: str = Field(..., description="Variant code")
    name: str = Field(..., description="Display name")
    sort_order: int = Field(..., description="Display order within the group")


class TrigVariantAdmin(BaseModel):
    """A variant in the admin listing, with how many trigs record it."""

    id: int = Field(..., description="Variant ID")
    code: str = Field(..., description="Variant code")
    name: str = Field(..., description="Display name")
    sort_order: int = Field(..., description="Display order within the group")
    trig_count: int = Field(..., description="Number of trigs with this variant")


class VariantGroupAdmin(BaseModel):
    """A variant group in the admin listing."""

    code: str = Field(..., description="Group code")
    name: str = Field(..., description="Group name")
    type_names: list[str] = Field(
        ..., description="Types whose trigs may choose from this group"
    )
    variants: list[TrigVariantAdmin] = Field(..., description="Values in order")


class VariantGroupResponse(BaseModel):
    """Response schema for a renamed group."""

    code: str = Field(..., description="Group code")
    name: str = Field(..., description="Group name")
