"""
Pydantic schemas for the co-op trigpointing experiment endpoint.
"""

import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_serializer


class CoopUser(BaseModel):
    """A user participating in the co-op comparison."""

    id: int
    name: str


class CoopVisit(BaseModel):
    """A single user's visit record for a trigpoint."""

    condition: str = Field(..., description="Condition code logged by this user")
    date: Optional[datetime.date] = Field(None, description="Date of the log entry")


class CoopTrigItem(BaseModel):
    """A trigpoint row in the co-op grid with per-user visit data."""

    id: int
    waypoint: str
    name: str
    condition: str = Field(..., description="Current trig condition code")
    type_code: Optional[str] = None
    type_name: Optional[str] = None
    category_code: Optional[str] = None
    category_name: Optional[str] = None
    wgs_lat: Decimal
    wgs_long: Decimal
    osgb_gridref: str
    distance_km: Optional[float] = None

    visits: dict[str, Optional[CoopVisit]] = Field(
        ...,
        description="Map of user_id (as string) to visit info, or null if not visited",
    )

    @field_serializer("wgs_lat", "wgs_long")
    def serialize_coords(self, value: Decimal) -> float:
        return round(float(value), 8)


class CoopResponse(BaseModel):
    """Response for the co-op trigpointing endpoint."""

    users: list[CoopUser]
    items: list[CoopTrigItem]
    total: int
    skip: int
    limit: int
    has_more: bool
