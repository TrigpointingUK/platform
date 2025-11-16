"""
Pydantic schemas for TLog (logs) endpoints.
"""

from datetime import date as DateType
from datetime import time as TimeType
from typing import Optional, Union

from pydantic import BaseModel, Field

from api.schemas.tphoto import TPhotoResponse


class TLogBase(BaseModel):
    id: int
    trig_id: Optional[int] = None  # Nullable for PostgreSQL compatibility
    user_id: Optional[int] = None  # Nullable for PostgreSQL compatibility
    date: Optional[DateType] = None  # Nullable for PostgreSQL compatibility
    time: Optional[TimeType] = None  # Nullable for PostgreSQL compatibility
    osgb_eastings: Optional[int] = None
    osgb_northings: Optional[int] = None
    osgb_gridref: Optional[str] = Field(default=None, max_length=14)
    fb_number: Optional[str] = Field(
        default=None, max_length=10
    )  # Nullable for PostgreSQL compatibility
    condition: Optional[str] = Field(
        default=None, min_length=1, max_length=1
    )  # Nullable for PostgreSQL compatibility
    comment: Optional[str] = None  # Nullable for PostgreSQL compatibility
    score: Optional[int] = None  # Nullable for PostgreSQL compatibility
    source: Optional[str] = Field(
        default=None, min_length=1, max_length=1
    )  # Nullable for PostgreSQL compatibility

    class Config:
        from_attributes = True


class TLogResponse(TLogBase):
    # Denormalized fields for convenience (populated via JOINs)
    trig_name: Optional[str] = None
    user_name: Optional[str] = None


class TLogWithIncludes(TLogResponse):
    # Optional includes for expanded responses
    photos: Optional[list[TPhotoResponse]] = None


class TLogCreate(BaseModel):
    # user_id is set from current user on POST endpoints
    # trig_id is usually provided
    trig_id: int
    date: DateType
    time: TimeType
    osgb_eastings: Optional[int] = None
    osgb_northings: Optional[int] = None
    osgb_gridref: Optional[str] = Field(default=None, max_length=14)
    fb_number: str = Field("", max_length=10)
    condition: str = Field(..., min_length=1, max_length=1)
    comment: str = ""
    score: int = 0
    source: str = Field("W", min_length=1, max_length=1)


class TLogUpdate(BaseModel):
    # Partial updates only - all fields optional
    date: Union[DateType, None] = None
    time: Union[TimeType, None] = None
    osgb_eastings: Union[int, None] = None
    osgb_northings: Union[int, None] = None
    osgb_gridref: Union[str, None] = Field(default=None, max_length=14)
    fb_number: Union[str, None] = Field(default=None, max_length=10)
    condition: Union[str, None] = Field(default=None, min_length=1, max_length=1)
    comment: Union[str, None] = None
    score: Union[int, None] = None
    source: Union[str, None] = Field(default=None, min_length=1, max_length=1)
