"""
Pydantic schemas for area endpoints.
"""

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, Field


class AreaTypeResponse(BaseModel):
    """Response model for area type."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Area type ID")
    code: str = Field(..., description="Area type code (e.g., historic_county)")
    name: str = Field(..., description="Area type display name")
    description: Optional[str] = Field(None, description="Area type description")


class AreaResponse(BaseModel):
    """Response model for an area."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Area ID")
    name: str = Field(..., description="Area name")
    code: Optional[str] = Field(None, description="External code (ONS, OS, etc.)")
    area_type: AreaTypeResponse = Field(..., description="Area type information")


class AreaGroupResponse(BaseModel):
    """Response model for areas grouped by type."""

    area_type: AreaTypeResponse = Field(..., description="Area type information")
    areas: list[AreaResponse] = Field(..., description="Areas of this type")


class AreasContainingResponse(BaseModel):
    """Response model for areas containing a point."""

    lat: float = Field(..., description="Query latitude")
    lon: float = Field(..., description="Query longitude")
    groups: list[AreaGroupResponse] = Field(
        ..., description="Areas grouped by type containing the point"
    )
    total_areas: int = Field(..., description="Total number of areas found")


class AreaBoundaryResponse(BaseModel):
    """Response model for area boundary as GeoJSON."""

    id: int = Field(..., description="Area ID")
    name: str = Field(..., description="Area name")
    code: Optional[str] = Field(None, description="External code (ONS, OS, etc.)")
    area_type: AreaTypeResponse = Field(..., description="Area type information")
    boundary: dict[str, Any] = Field(
        ..., description="GeoJSON geometry (MultiPolygon or Polygon)"
    )


class AreaCountItem(BaseModel):
    """Response model for area count item in user breakdown."""

    area_name: str = Field(..., description="Area name")
    count: int = Field(
        ..., description="Number of distinct trigpoints logged in this area"
    )


class UserAreaBreakdownResponse(BaseModel):
    """Response model for user log counts grouped by area."""

    area_type: AreaTypeResponse = Field(..., description="Area type information")
    items: list[AreaCountItem] = Field(
        ..., description="Areas with log counts, ordered by count descending"
    )
