"""
Pydantic schemas for trig list endpoints.
"""

from datetime import datetime
from typing import Any, Dict, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_validator

VISIBILITY_VALUES = ("private", "public", "admins")
EDITABILITY_VALUES = ("private", "public", "admins")


# ---------------------------------------------------------------------------
# List schemas
# ---------------------------------------------------------------------------


class TrigListCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[Dict[str, Any]] = None
    visibility: Literal["private", "public", "admins"] = "private"
    editability: Literal["private", "public", "admins"] = "private"


class TrigListUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[Dict[str, Any]] = None
    visibility: Optional[Literal["private", "public", "admins"]] = None
    editability: Optional[Literal["private", "public", "admins"]] = None


class TrigListResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    owner_name: Optional[str] = None
    name: str
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata_")
    visibility: str
    editability: str
    position: int
    item_count: int = 0
    is_default: bool = False
    created_at: datetime
    updated_at: Optional[datetime] = None


class TrigListSummary(BaseModel):
    """Slim representation for dropdowns and the add-to-list UI."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    item_count: int = 0
    is_default: bool = False


class TrigListReorderRequest(BaseModel):
    ordering: list[dict] = Field(..., description="List of {list_id, position} objects")

    @field_validator("ordering")
    @classmethod
    def validate_ordering(cls, v: list[dict]) -> list[dict]:
        for entry in v:
            if "list_id" not in entry or "position" not in entry:
                raise ValueError("Each entry must have list_id and position")
        return v


# ---------------------------------------------------------------------------
# Item schemas
# ---------------------------------------------------------------------------


class TrigListItemCreate(BaseModel):
    trig_id: int
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[Dict[str, Any]] = None


class TrigListItemUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    metadata: Optional[Dict[str, Any]] = None
    position: Optional[int] = None


class TrigSummary(BaseModel):
    """Minimal trig info embedded in list item responses."""

    id: int
    waypoint: str
    name: str
    condition: Optional[str] = None
    osgb_gridref: Optional[str] = None
    wgs_lat: Optional[str] = None
    wgs_long: Optional[str] = None
    wgs_height: Optional[float] = None
    type_code: Optional[str] = None
    type_name: Optional[str] = None
    category_code: Optional[str] = None
    category_name: Optional[str] = None
    status_name: Optional[str] = None
    score: Optional[float] = None


class TrigListItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    list_id: int
    trig_id: int
    created_by: Optional[int] = None
    updated_by: Optional[int] = None
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = Field(None, alias="metadata_")
    position: int
    created_at: datetime
    updated_at: Optional[datetime] = None
    trig: Optional[TrigSummary] = None


class TrigListItemReorderRequest(BaseModel):
    ordering: list[dict] = Field(..., description="List of {item_id, position} objects")

    @field_validator("ordering")
    @classmethod
    def validate_ordering(cls, v: list[dict]) -> list[dict]:
        for entry in v:
            if "item_id" not in entry or "position" not in entry:
                raise ValueError("Each entry must have item_id and position")
        return v


# ---------------------------------------------------------------------------
# Batch membership
# ---------------------------------------------------------------------------


class TrigListMembership(BaseModel):
    """Which lists a single trig belongs to."""

    trig_id: int
    list_ids: list[int] = []


class TrigListMembershipResponse(BaseModel):
    items: list[TrigListMembership]


class DefaultListTrigIdsResponse(BaseModel):
    """Trig IDs in the current user's default list.

    Used to colour the quick-add star without per-row membership calls. Cached in
    Redis and React Query; invalidated on mutations that could change either the
    user's default list id or the contents of that list.
    """

    list_id: Optional[int] = Field(
        None,
        description="Default list id, or null if the user has no default list yet",
    )
    trig_ids: list[int] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Paginated response envelope
# ---------------------------------------------------------------------------


class TrigListItemsPage(BaseModel):
    items: list[TrigListItemResponse]
    total: int
    has_more: bool
