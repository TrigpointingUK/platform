"""
Pydantic schemas for location search endpoints.
"""

from datetime import date as DateType
from datetime import time as TimeType
from typing import Generic, List, Optional, TypeVar

from pydantic import BaseModel, ConfigDict, Field


class LocationSearchResult(BaseModel):
    """Result from location search endpoint."""

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "type": "trigpoint",
                "name": "Kinder Low",
                "lat": 53.385,
                "lon": -1.876,
                "description": "TP0001 - Pillar",
                "location": "Edale, Derbyshire",
                "category_code": "PILLAR",
            }
        }
    )

    type: str = Field(
        ...,
        description="Type of location: trigpoint, town, postcode, gridref, latlon, user",
    )
    name: str = Field(..., description="Display name for the location")
    lat: float = Field(..., description="WGS84 latitude")
    lon: float = Field(..., description="WGS84 longitude")
    description: Optional[str] = Field(
        None, description="Additional descriptive information"
    )
    id: Optional[str] = Field(
        None, description="ID for routing (trig ID, user ID, etc.)"
    )
    location: Optional[str] = Field(
        default=None, description="Human-readable location (town, county)"
    )
    category_code: Optional[str] = Field(
        default=None,
        description="Trig category code for icon selection (e.g. PILLAR, FBM)",
    )


class LogSearchResult(BaseModel):
    """Result from log text search."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Log ID")
    trig_id: int = Field(..., description="Trigpoint ID")
    trig_name: Optional[str] = Field(None, description="Trigpoint name")
    user_id: int = Field(..., description="User ID")
    user_name: Optional[str] = Field(None, description="Username")
    date: DateType = Field(..., description="Log date")
    time: TimeType = Field(..., description="Log time")
    condition: str = Field(..., description="Log condition (G/D/M/P/U)")
    comment: str = Field(..., description="Log comment text")
    score: int = Field(..., description="Log score (0-10)")
    comment_excerpt: Optional[str] = Field(
        None, description="Truncated comment for display"
    )


T = TypeVar("T")


class SearchCategoryResults(BaseModel, Generic[T]):
    """Wrapper for search results in a specific category."""

    total: int = Field(..., description="Total count of matching results")
    items: List[T] = Field(..., description="List of result items")
    has_more: bool = Field(..., description="Whether more results are available")
    query: str = Field(..., description="The search query used")


class UnifiedSearchResults(BaseModel):
    """Top-level response containing all search categories."""

    query: str = Field(..., description="The search query")
    trigpoints: SearchCategoryResults[LocationSearchResult] = Field(
        ..., description="Trigpoint search results"
    )
    station_numbers: SearchCategoryResults[LocationSearchResult] = Field(
        ..., description="Station number search results"
    )
    places: SearchCategoryResults[LocationSearchResult] = Field(
        ..., description="Place (town) search results"
    )
    users: SearchCategoryResults[LocationSearchResult] = Field(
        ..., description="User search results"
    )
    postcodes: SearchCategoryResults[LocationSearchResult] = Field(
        ..., description="Postcode search results"
    )
    coordinates: SearchCategoryResults[LocationSearchResult] = Field(
        ..., description="Coordinate (latlon/gridref) search results"
    )
    log_substring: SearchCategoryResults[LogSearchResult] = Field(
        ..., description="Log text substring search results"
    )
    log_regex: SearchCategoryResults[LogSearchResult] = Field(
        ..., description="Log text regex search results"
    )
