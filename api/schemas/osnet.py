"""
Pydantic schemas for OS Net comparison API.
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

# Section constants matching the service
SECTION_CURRENT = 1
SECTION_LEGACY = 2
SECTION_DESTROYED = 3

SECTION_NAMES = {
    SECTION_CURRENT: "Current (v2009)",
    SECTION_LEGACY: "Legacy (v2001)",
    SECTION_DESTROYED: "Destroyed/Moved",
}


class OSNetStationData(BaseModel):
    """OS Net station coordinate data."""

    code: Optional[str] = Field(None, description="4-letter OS Net station code")
    easting: Optional[float] = Field(None, description="OSGB36 easting")
    northing: Optional[float] = Field(None, description="OSGB36 northing")
    gridref: Optional[str] = Field(None, description="OS grid reference")
    height: Optional[float] = Field(None, description="Orthometric height")
    lat_dms: Optional[str] = Field(None, description="Latitude in DMS format")
    lon_dms: Optional[str] = Field(None, description="Longitude in DMS format")


class DBStationData(BaseModel):
    """Database active station data."""

    trig_id: Optional[int] = Field(None, description="Trigpoint database ID")
    waypoint: Optional[str] = Field(None, description="Trigpoint waypoint code")
    name: Optional[str] = Field(None, description="Trigpoint name")
    stn_number_active: Optional[str] = Field(None, description="Active station number")
    easting: Optional[float] = Field(None, description="OSGB36 easting")
    northing: Optional[float] = Field(None, description="OSGB36 northing")
    gridref: Optional[str] = Field(None, description="OS grid reference")
    height: Optional[float] = Field(None, description="Height in metres")


class StationDifferenceResponse(BaseModel):
    """A difference found between OS Net and database."""

    station_code: str = Field(..., description="Station code (OS Net or database)")
    difference_type: str = Field(
        ...,
        description=(
            "Type of difference: new_in_osnet, missing_from_osnet, coordinate_mismatch, "
            "unmatched_db, destroyed_not_in_db, legacy_not_in_db"
        ),
    )
    description: str = Field(
        ..., description="Human-readable description of the difference"
    )
    osnet_data: Optional[OSNetStationData] = Field(
        None, description="OS Net station data if available"
    )
    db_data: Optional[DBStationData] = Field(
        None, description="Database station data if available"
    )
    distance_metres: Optional[float] = Field(
        None, description="Distance between coordinates in metres (for mismatches)"
    )
    osnet_section: Optional[int] = Field(
        None,
        description="OS Net file section: 1=Current (v2009), 2=Legacy (v2001), 3=Destroyed/Moved",
    )
    osnet_section_name: Optional[str] = Field(
        None, description="Human-readable section name"
    )


class OSNetComparisonResponse(BaseModel):
    """Response from OS Net comparison endpoint."""

    osnet_count: int = Field(..., description="Total number of stations in OS Net file")
    osnet_current_count: int = Field(
        ..., description="Number of current stations (Part i - v2009)"
    )
    osnet_legacy_count: int = Field(
        ..., description="Number of legacy stations (Part ii - v2001)"
    )
    osnet_destroyed_count: int = Field(
        ..., description="Number of destroyed/moved stations (Part iii)"
    )
    db_count: int = Field(..., description="Number of active stations in database")
    matched_count: int = Field(
        ..., description="Number of stations successfully matched"
    )
    differences: list[StationDifferenceResponse] = Field(
        ..., description="List of all differences found"
    )
    osnet_fetch_time: datetime = Field(
        ..., description="When the OS Net file was fetched"
    )
    changelog_entries: list[str] = Field(
        ..., description="Recent changelog entries from OS Net file header"
    )

    # Summary counts by difference type
    new_in_osnet_count: int = Field(
        ..., description="Count of current stations in OS Net but not in database"
    )
    missing_from_osnet_count: int = Field(
        ..., description="Count of database stations not found in OS Net"
    )
    coordinate_mismatch_count: int = Field(
        ..., description="Count of stations with coordinate differences"
    )
    unmatched_db_count: int = Field(
        ..., description="Count of database stations without stn_number_active"
    )
    destroyed_not_in_db_count: int = Field(
        ..., description="Count of destroyed stations not in database (informational)"
    )
    legacy_not_in_db_count: int = Field(
        ..., description="Count of legacy stations not in database (informational)"
    )
