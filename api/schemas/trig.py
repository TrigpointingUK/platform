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


class TrigTypeInfo(BaseModel):
    """Embedded type information for trig responses."""

    model_config = ConfigDict(from_attributes=True)

    code: str = Field(..., description="Type code (e.g., HOTINE, FBM)")
    name: str = Field(..., description="Type display name")
    category_code: Optional[str] = Field(None, description="Parent category code")
    category_name: Optional[str] = Field(None, description="Parent category name")


class TrigMinimal(BaseModel):
    """Minimal trig response for /trig/{id} endpoints."""

    id: int = Field(..., description="Trigpoint ID")
    waypoint: str = Field(..., description="Waypoint code (e.g., TP0001)")
    name: str = Field(..., description="Trigpoint name")

    # Public basic classification/identity
    condition: str = Field(..., description="Condition code")

    # Type system
    type_code: Optional[str] = Field(None, description="Type code (e.g., HOTINE, FBM)")
    type_name: Optional[str] = Field(None, description="Type display name")
    type_wiki_url: Optional[str] = Field(None, description="Wiki URL for this type")
    category_code: Optional[str] = Field(None, description="Type category code")
    category_name: Optional[str] = Field(None, description="Type category display name")

    # Coordinates and grid ref
    wgs_lat: Decimal = Field(..., description="WGS84 latitude")
    wgs_long: Decimal = Field(..., description="WGS84 longitude")
    osgb_gridref: str = Field(..., description="Grid reference (OSGB or Irish format)")

    # Grid system classification
    grid_system: Optional[str] = Field(
        None,
        description="Grid system: 'gb' (British National Grid) or 'ie' (Irish Grid)",
    )
    country_name: Optional[str] = Field(
        None,
        description="Country name (e.g., 'England', 'Ireland', 'Northern Ireland')",
    )

    distance_km: Optional[float] = None  # populated only when lat/lon provided

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("wgs_lat", "wgs_long")
    def serialize_coords_8dp(self, value: Decimal) -> float:
        """Serialize coordinates with full 8dp precision."""
        return round(float(value), 8)


class TrigExport(BaseModel):
    """Trig response for /export endpoint (Android app compatibility).

    Separate from TrigMinimal to use 5dp coordinate serialization for
    backward compatibility with Android app.

    Minimal fields only - Android app uses its own hardcoded groupings.
    """

    id: int = Field(..., description="Trigpoint ID")
    waypoint: str = Field(..., description="Waypoint code (e.g., TP0001)")
    name: str = Field(..., description="Trigpoint name")
    condition: str = Field(..., description="Condition code")
    type_code: Optional[str] = Field(None, description="Type code (e.g., HOTINE, FBM)")
    type_name: Optional[str] = Field(None, description="Type display name")
    category_code: Optional[str] = Field(None, description="Type category code")
    category_name: Optional[str] = Field(None, description="Type category display name")
    physical_type: Optional[str] = Field(
        None, description="Legacy physical type (e.g., Pillar, Bolt)"
    )
    current_use: Optional[str] = Field(
        None, description="Current use (e.g., Passive station)"
    )
    historic_use: Optional[str] = Field(
        None, description="Historic use (e.g., Primary)"
    )
    wgs_lat: Decimal = Field(..., description="WGS84 latitude")
    wgs_long: Decimal = Field(..., description="WGS84 longitude")
    osgb_gridref: str = Field(..., description="Grid reference (OSGB or Irish format)")
    fb_number: Optional[str] = Field(None, description="Flush bracket number")

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("wgs_lat", "wgs_long")
    def serialize_coords_5dp(self, value: Decimal) -> float:
        """Round to 5dp for backward compatibility with Android app."""
        return round(float(value), 5)


class TrigDetails(BaseModel):
    """Details sub-object for /trig/{id}/details or include=details."""

    current_use: Optional[str] = None
    historic_use: Optional[str] = None
    wgs_height: Optional[Decimal] = None
    osgb_eastings: Optional[Decimal] = None
    osgb_northings: Optional[Decimal] = None
    osgb_height: Optional[Decimal] = None
    postcode: Optional[str] = None
    county: Optional[str] = None
    town: Optional[str] = None
    fb_number: Optional[str] = None
    stn_number: Optional[str] = None
    stn_number_active: Optional[str] = None
    stn_number_passive: Optional[str] = None
    stn_number_osgb36: Optional[str] = None
    legal_message: Optional[str] = Field(
        None, description="Optional legal/access message (HTML)"
    )

    # Original location fields - official OS-published location
    original_wgs_lat: Optional[Decimal] = Field(
        None, description="Official OS WGS84 latitude"
    )
    original_wgs_long: Optional[Decimal] = Field(
        None, description="Official OS WGS84 longitude"
    )
    original_osgb_eastings: Optional[Decimal] = Field(
        None, description="Official OS grid eastings"
    )
    original_osgb_northings: Optional[Decimal] = Field(
        None, description="Official OS grid northings"
    )
    original_osgb_gridref: Optional[str] = Field(
        None, description="Official OS grid reference"
    )
    original_grid_system: Optional[str] = Field(
        None, description="Grid system for original location: 'gb' or 'ie'"
    )
    original_provenance: Optional[str] = Field(
        None, description="Notes for data cleansing tracking"
    )
    original_wgs_height: Optional[Decimal] = Field(
        None, description="Official OS WGS84 height in metres"
    )
    original_osgb_height: Optional[Decimal] = Field(
        None, description="Official OS OSGB height in metres"
    )

    model_config = ConfigDict(from_attributes=True)

    @field_serializer("town")
    def serialize_town(self, value: Optional[str]) -> Optional[str]:
        """Convert town name from ALL CAPS to Mixed Case."""
        return value.title() if value else value

    @field_serializer("wgs_height", "osgb_height")
    def serialize_height(self, value: Optional[Decimal]) -> Optional[float]:
        """Serialize height as float for JSON output."""
        return float(value) if value is not None else None

    @field_serializer("osgb_eastings", "osgb_northings")
    def serialize_coords_4dp(self, value: Optional[Decimal]) -> Optional[float]:
        """Serialize coordinates with 4dp precision."""
        return round(float(value), 4) if value is not None else None

    @field_serializer("original_wgs_lat", "original_wgs_long")
    def serialize_original_wgs_8dp(self, value: Optional[Decimal]) -> Optional[float]:
        """Serialize original WGS84 coordinates with 8dp precision."""
        return round(float(value), 8) if value is not None else None

    @field_serializer("original_osgb_eastings", "original_osgb_northings")
    def serialize_original_osgb_4dp(self, value: Optional[Decimal]) -> Optional[float]:
        """Serialize original grid coordinates with 4dp precision."""
        return round(float(value), 4) if value is not None else None

    @field_serializer("original_wgs_height", "original_osgb_height")
    def serialize_original_height(self, value: Optional[Decimal]) -> Optional[float]:
        """Serialize original height as float for JSON output."""
        return float(value) if value is not None else None


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
