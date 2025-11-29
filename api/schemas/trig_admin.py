"""
Pydantic schemas for admin trigpoint management endpoints.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class TrigNeedsAttentionSummary(BaseModel):
    """Summary statistics for trigpoints needing attention."""

    count: int = Field(..., description="Number of trigpoints needing attention")
    latest_update: Optional[datetime] = Field(
        None, description="Most recent update timestamp"
    )


class TrigNeedsAttentionListItem(BaseModel):
    """List item for trigpoints needing attention."""

    id: int = Field(..., description="Trigpoint ID")
    waypoint: str = Field(..., description="Waypoint code")
    name: str = Field(..., description="Trigpoint name")
    condition: str = Field(..., description="Condition code")
    needs_attention: int = Field(..., description="Needs attention flag value")
    attention_comment: str = Field(..., description="Attention comment history")
    upd_timestamp: Optional[datetime] = Field(None, description="Last update timestamp")

    class Config:
        from_attributes = True


class TrigAdminDetail(BaseModel):
    """Full trigpoint details for admin editing."""

    id: int
    waypoint: str
    name: str
    fb_number: Optional[str] = ""
    stn_number: Optional[str] = ""
    stn_number_active: Optional[str] = ""
    stn_number_passive: Optional[str] = ""
    stn_number_osgb36: Optional[str] = ""
    status_id: int
    current_use: Optional[str] = "none"
    historic_use: Optional[str] = "none"
    physical_type: Optional[str] = "Pillar"
    condition: Optional[str] = "G"
    wgs_lat: Decimal
    wgs_long: Decimal
    wgs_height: int
    osgb_eastings: int
    osgb_northings: int
    osgb_gridref: Optional[str] = ""
    osgb_height: int
    postcode: Optional[str] = ""
    county: Optional[str] = ""
    town: Optional[str] = ""
    needs_attention: int
    attention_comment: Optional[str] = ""
    upd_timestamp: Optional[datetime] = None

    class Config:
        from_attributes = True


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
    current_use: Optional[str] = Field(default="none", max_length=25)
    historic_use: Optional[str] = Field(default="none", max_length=30)
    physical_type: Optional[str] = Field(default="Pillar", max_length=25)
    condition: Optional[str] = Field(default="G", min_length=1, max_length=1)

    # Coordinates - WGS84
    wgs_lat: Decimal = Field(..., ge=-90, le=90)
    wgs_long: Decimal = Field(..., ge=-180, le=180)
    wgs_height: int

    # Coordinates - OSGB
    osgb_eastings: int = Field(..., ge=0)
    osgb_northings: int = Field(..., ge=0)
    osgb_gridref: Optional[str] = Field(default="", max_length=14)
    osgb_height: int

    # Admin action
    action: str = Field(
        ...,
        description="Action to take: 'solved', 'revisit', or 'cant_fix'",
        pattern="^(solved|revisit|cant_fix)$",
    )
    admin_comment: str = Field(
        ..., min_length=1, description="Admin comment to append to history"
    )


class StatusResponse(BaseModel):
    """Status record for dropdowns."""

    id: int
    name: str
    descr: str
    limit_descr: str

    class Config:
        from_attributes = True
