"""
Pydantic schemas for trig endpoints.
"""

from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field, field_serializer, field_validator


class AttrSourceInfo(BaseModel):
    """Information about an attribute source."""

    id: int = Field(..., description="Attribute source ID")
    name: str = Field(..., description="Source name")
    url: Optional[str] = Field(None, description="Source URL")

    class Config:
        from_attributes = True


class AttrSetData(BaseModel):
    """Attribute set data - values for one row of attributes."""

    values: dict[int, str] = Field(
        ..., description="Dictionary mapping attr_id to value_string"
    )

    class Config:
        from_attributes = True


class TrigAttrsData(BaseModel):
    """Attribute data for a trigpoint from a specific source."""

    source: AttrSourceInfo = Field(..., description="Attribute source information")
    attr_names: dict[int, str] = Field(
        ..., description="Dictionary mapping attr_id to attr name"
    )
    attribute_sets: list[AttrSetData] = Field(
        ..., description="List of attribute sets (rows)"
    )

    class Config:
        from_attributes = True


class TrigMinimal(BaseModel):
    """Minimal trig response for /trig/{id}."""

    id: int = Field(..., description="Trigpoint ID")
    waypoint: str = Field(..., description="Waypoint code (e.g., TP0001)")
    name: str = Field(..., description="Trigpoint name")

    # Public basic classification/identity
    status_name: Optional[str] = Field(
        None, description="Human-readable status derived from status_id"
    )
    physical_type: str = Field(..., description="Physical type (e.g., Pillar)")
    condition: str = Field(..., description="Condition code")

    # Coordinates and grid ref
    wgs_lat: Decimal = Field(..., description="WGS84 latitude")
    wgs_long: Decimal = Field(..., description="WGS84 longitude")
    osgb_gridref: str = Field(..., description="OSGB grid reference")

    distance_km: Optional[float] = None  # populated only when lat/lon provided

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: str,
        }


class TrigDetails(BaseModel):
    """Details sub-object for /trig/{id}/details or include=details."""

    current_use: str
    historic_use: str
    wgs_height: int
    osgb_height: int
    postcode: str
    county: str
    town: str
    fb_number: str
    stn_number: str
    stn_number_active: Optional[str] = None
    stn_number_passive: Optional[str] = None
    stn_number_osgb36: Optional[str] = None

    @field_serializer("town")
    def serialize_town(self, value: str) -> str:
        """Convert town name from ALL CAPS to Mixed Case."""
        return value.title() if value else value

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: str,
        }


class TrigStats(BaseModel):
    """Statistics for a trigpoint."""

    logged_first: Optional[date] = None
    logged_last: Optional[date] = None
    logged_count: int
    found_last: Optional[date] = None
    found_count: int
    photo_count: int
    score_mean: Decimal
    score_baysian: Decimal

    @field_validator("logged_first", "logged_last", "found_last", mode="before")
    @classmethod
    def handle_invalid_dates(cls, v):
        """Convert invalid MySQL dates (0000-00-00) to None."""
        if v in ("0000-00-00", "", None):
            return None
        return v

    class Config:
        from_attributes = True
        json_encoders = {
            Decimal: str,
            date: lambda v: v.isoformat() if v else None,
            datetime: lambda v: v.isoformat() if v else None,
        }


class TrigWithIncludes(TrigMinimal):
    """Envelope for minimal trig with optional includes."""

    details: Optional[TrigDetails] = None
    stats: Optional[TrigStats] = None
    attrs: Optional[list[TrigAttrsData]] = None


class TrigCountResponse(BaseModel):
    """Response model for trigpoint count queries."""

    trig_id: int
    count: int
