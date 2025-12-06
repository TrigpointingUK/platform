"""
Pydantic schemas for trig endpoints.
"""

from datetime import date
from decimal import Decimal
from typing import Optional

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_serializer,
    field_validator,
    model_validator,
)


class AttrSourceInfo(BaseModel):
    """Information about an attribute source."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Attribute source ID")
    name: str = Field(..., description="Source name")
    url: Optional[str] = Field(None, description="Source URL")


class AttrSetData(BaseModel):
    """Attribute set data - values for one row of attributes."""

    model_config = ConfigDict(from_attributes=True)

    values: dict[int, str] = Field(
        ..., description="Dictionary mapping attr_id to value_string"
    )


class TrigAttrsData(BaseModel):
    """Attribute data for a trigpoint from a specific source."""

    model_config = ConfigDict(from_attributes=True)

    source: AttrSourceInfo = Field(..., description="Attribute source information")
    attr_names: dict[int, str] = Field(
        ..., description="Dictionary mapping attr_id to attr name"
    )
    attribute_sets: list[AttrSetData] = Field(
        ..., description="List of attribute sets (rows)"
    )


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

    model_config = ConfigDict(from_attributes=True)


class TrigDetails(BaseModel):
    """Details sub-object for /trig/{id}/details or include=details."""

    current_use: Optional[str] = None
    historic_use: Optional[str] = None
    wgs_height: int
    osgb_height: int
    postcode: Optional[str] = None
    county: Optional[str] = None
    town: Optional[str] = None
    fb_number: Optional[str] = None
    stn_number: Optional[str] = None
    stn_number_active: Optional[str] = None
    stn_number_passive: Optional[str] = None
    stn_number_osgb36: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("town")
    def serialize_town(self, value: Optional[str]) -> Optional[str]:
        """Convert town name from ALL CAPS to Mixed Case."""
        return value.title() if value else value


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
        """Convert invalid MySQL dates (0000-00-00) and epoch dates to None.

        MySQL uses '0000-00-00' for invalid/never dates, which SQLAlchemy may
        convert to epoch date (1970-01-01). Both represent "never" semantically.
        """
        if v in ("0000-00-00", "", None):
            return None
        # Handle epoch date as sentinel for "never"
        if isinstance(v, date) and v == date(1970, 1, 1):
            return None
        return v

    @model_validator(mode="after")
    def nullify_dates_when_count_is_zero(self):
        """Set date fields to None when corresponding count is zero.

        When found_count is 0, the trig has never been found, so found_last
        has no meaningful value. Similarly for logged_count and log dates.
        """
        if self.found_count == 0:
            self.found_last = None
        if self.logged_count == 0:
            self.logged_first = None
            self.logged_last = None
        return self

    model_config = ConfigDict(from_attributes=True)


class TrigWithIncludes(TrigMinimal):
    """Envelope for minimal trig with optional includes."""

    details: Optional[TrigDetails] = None
    stats: Optional[TrigStats] = None
    attrs: Optional[list[TrigAttrsData]] = None


class TrigCountResponse(BaseModel):
    """Response model for trigpoint count queries."""

    trig_id: int
    count: int
