"""
Pydantic schemas for admin trigpoint management endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer


class TrigNeedsAttentionSummary(BaseModel):
    """Summary statistics for trigpoints needing attention."""

    count: int = Field(..., description="Number of trigpoints needing attention")
    latest_update: Optional[datetime] = Field(
        None, description="Most recent update timestamp"
    )


class TrigNeedsAttentionListItem(BaseModel):
    """List item for trigpoints needing attention."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Trigpoint ID")
    waypoint: str = Field(..., description="Waypoint code")
    name: str = Field(..., description="Trigpoint name")
    condition: str = Field(..., description="Condition code")
    needs_attention: int = Field(..., description="Needs attention flag value")
    attention_comment: str = Field(..., description="Attention comment history")
    upd_timestamp: Optional[datetime] = Field(None, description="Last update timestamp")


class TrigAdminDetail(BaseModel):
    """Full trigpoint details for admin editing."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    waypoint: str
    name: str
    fb_number: Optional[str] = ""
    stn_number: Optional[str] = ""
    stn_number_active: Optional[str] = ""
    stn_number_passive: Optional[str] = ""
    stn_number_osgb36: Optional[str] = ""
    status_id: int
    type_id: Optional[int] = Field(None, description="Trig type ID (FK to trig_type)")
    current_use: Optional[str] = "none"
    historic_use: Optional[str] = "none"
    condition: Optional[str] = "G"
    wgs_lat: Decimal
    wgs_long: Decimal
    wgs_height: Optional[Decimal] = None
    osgb_eastings: Decimal
    osgb_northings: Decimal
    osgb_gridref: Optional[str] = ""
    osgb_height: Optional[Decimal] = None
    postcode: Optional[str] = ""
    # Note: county is now derived from trig_area join in the /trigs endpoint
    town: Optional[str] = ""
    needs_attention: int
    attention_comment: Optional[str] = ""
    upd_timestamp: Optional[datetime] = None
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

    @field_serializer("wgs_lat", "wgs_long")
    def serialize_wgs_coords(self, value: Decimal) -> float:
        """Serialize WGS84 coordinates as float."""
        return float(value)

    @field_serializer("osgb_eastings", "osgb_northings")
    def serialize_osgb_coords(self, value: Decimal) -> float:
        """Serialize OSGB coordinates as float."""
        return float(value)

    @field_serializer("wgs_height", "osgb_height")
    def serialize_height(self, value: Optional[Decimal]) -> Optional[float]:
        """Serialize height as float."""
        return float(value) if value is not None else None

    @field_serializer("original_wgs_lat", "original_wgs_long")
    def serialize_original_wgs_coords(
        self, value: Optional[Decimal]
    ) -> Optional[float]:
        """Serialize original WGS84 coordinates as float."""
        return float(value) if value is not None else None

    @field_serializer("original_wgs_height", "original_osgb_height")
    def serialize_original_height(self, value: Optional[Decimal]) -> Optional[float]:
        """Serialize original height as float."""
        return float(value) if value is not None else None

    @field_serializer("original_osgb_eastings", "original_osgb_northings")
    def serialize_original_osgb_coords(
        self, value: Optional[Decimal]
    ) -> Optional[float]:
        """Serialize original OSGB coordinates as float."""
        return float(value) if value is not None else None


class TrigAdminUpdate(BaseModel):
    """Request schema for updating trigpoint via admin PATCH."""

    # Basic fields
    name: str = Field(..., min_length=1, max_length=50)
    fb_number: Optional[str] = Field(default="", max_length=10)
    stn_number: Optional[str] = Field(default="", max_length=20)
    stn_number_active: Optional[str] = Field(default="", max_length=20)
    stn_number_passive: Optional[str] = Field(default="", max_length=20)
    stn_number_osgb36: Optional[str] = Field(default="", max_length=20)

    # Classification
    status_id: int = Field(..., ge=1)
    type_id: Optional[int] = Field(
        None,
        description="Trig type ID (FK to trig_type)",
    )
    current_use: Optional[str] = Field(default="none", max_length=25)
    historic_use: Optional[str] = Field(default="none", max_length=30)
    condition: Optional[str] = Field(default="G", min_length=1, max_length=1)

    # Coordinates - WGS84
    wgs_lat: Decimal = Field(..., ge=-90, le=90)
    wgs_long: Decimal = Field(..., ge=-180, le=180)
    wgs_height: Optional[Decimal] = None

    # Coordinates - OSGB (4dp for 0.1mm precision)
    osgb_eastings: Decimal = Field(..., ge=0)
    osgb_northings: Decimal = Field(..., ge=0)
    osgb_gridref: Optional[str] = Field(default="", max_length=14)
    osgb_height: Optional[Decimal] = None

    # Original location fields - official OS-published location
    original_wgs_lat: Optional[Decimal] = Field(
        default=None, ge=-90, le=90, description="Official OS WGS84 latitude"
    )
    original_wgs_long: Optional[Decimal] = Field(
        default=None, ge=-180, le=180, description="Official OS WGS84 longitude"
    )
    original_osgb_eastings: Optional[Decimal] = Field(
        default=None, ge=0, description="Official OS grid eastings"
    )
    original_osgb_northings: Optional[Decimal] = Field(
        default=None, ge=0, description="Official OS grid northings"
    )
    original_osgb_gridref: Optional[str] = Field(
        default=None, max_length=14, description="Official OS grid reference"
    )
    original_grid_system: Optional[str] = Field(
        default=None, max_length=2, description="Grid system: 'gb' or 'ie'"
    )
    original_provenance: Optional[str] = Field(
        default=None, description="Notes for data cleansing tracking"
    )
    original_wgs_height: Optional[Decimal] = Field(
        default=None, description="Official OS WGS84 height in metres"
    )
    original_osgb_height: Optional[Decimal] = Field(
        default=None, description="Official OS OSGB height in metres"
    )

    # Legal/access information
    legal_message: Optional[str] = Field(
        default=None, description="Optional legal/access message (HTML)"
    )

    # Admin action
    action: str = Field(
        ...,
        description="Action to take: 'solved', 'revisit', or 'cant_fix'",
        pattern="^(solved|revisit|cant_fix)$",
    )
    admin_comment: str = Field(
        ..., min_length=1, description="Admin comment to append to history"
    )


class TrigAdminCreate(BaseModel):
    """Request schema for creating a new trigpoint via admin POST."""

    # Basic fields
    name: str = Field(..., min_length=1, max_length=50)
    fb_number: Optional[str] = Field(default="", max_length=10)
    stn_number: Optional[str] = Field(default="", max_length=20)
    stn_number_active: Optional[str] = Field(default="", max_length=20)
    stn_number_passive: Optional[str] = Field(default="", max_length=20)
    stn_number_osgb36: Optional[str] = Field(default="", max_length=20)

    # Classification
    status_id: int = Field(..., ge=1)
    type_id: Optional[int] = Field(
        None,
        description="Trig type ID (FK to trig_type)",
    )
    current_use: Optional[str] = Field(default="none", max_length=25)
    historic_use: Optional[str] = Field(default="none", max_length=30)
    condition: Optional[str] = Field(default="G", min_length=1, max_length=1)

    # Coordinates - WGS84
    wgs_lat: Decimal = Field(..., ge=-90, le=90)
    wgs_long: Decimal = Field(..., ge=-180, le=180)
    wgs_height: Optional[Decimal] = None

    # Coordinates - OSGB (4dp for 0.1mm precision)
    osgb_eastings: Decimal = Field(..., ge=0)
    osgb_northings: Decimal = Field(..., ge=0)
    osgb_gridref: Optional[str] = Field(default="", max_length=14)
    osgb_height: Optional[Decimal] = None

    # Legal/access information
    legal_message: Optional[str] = Field(
        default=None, description="Optional legal/access message (HTML)"
    )

    # Admin comment for audit trail
    admin_comment: str = Field(
        ..., min_length=1, description="Admin comment for the creation audit trail"
    )


class StatusResponse(BaseModel):
    """Status record for dropdowns."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    descr: str
    limit_descr: str
