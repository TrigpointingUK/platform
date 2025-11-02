"""
Pydantic schemas for location search endpoints.
"""

from typing import Optional

from pydantic import BaseModel, Field


class LocationSearchResult(BaseModel):
    """Result from location search endpoint."""

    type: str = Field(
        ...,
        description="Type of location: trigpoint, town, postcode, gridref, latlon",
    )
    name: str = Field(..., description="Display name for the location")
    lat: float = Field(..., description="WGS84 latitude")
    lon: float = Field(..., description="WGS84 longitude")
    description: Optional[str] = Field(
        None, description="Additional descriptive information"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "type": "trigpoint",
                "name": "Kinder Low",
                "lat": 53.385,
                "lon": -1.876,
                "description": "TP0001 - Pillar",
            }
        }
