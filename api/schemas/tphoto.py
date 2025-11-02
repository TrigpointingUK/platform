"""
Pydantic schemas for tphoto endpoints.
"""

# from datetime import datetime  # Not currently used
from typing import List, Optional

from pydantic import AliasChoices, BaseModel, Field, field_validator


class TPhotoBase(BaseModel):
    id: int
    log_id: int
    user_id: int
    type: str = Field(..., min_length=1, max_length=1)
    filesize: int
    height: int
    width: int
    icon_filesize: int
    icon_height: int
    icon_width: int
    name: str = Field(
        serialization_alias="caption",
        validation_alias=AliasChoices("caption", "name"),
    )
    text_desc: str
    public_ind: str = Field(
        ...,
        min_length=1,
        max_length=1,
        serialization_alias="license",
        validation_alias=AliasChoices("license", "public_ind"),
    )
    # Derived fields
    photo_url: str
    icon_url: str

    class Config:
        from_attributes = True


class TPhotoResponse(TPhotoBase):
    # Denormalized fields for convenience (populated via JOINs)
    user_name: Optional[str] = None
    trig_id: Optional[int] = None
    trig_name: Optional[str] = None
    log_date: Optional[date] = None


class TPhotoUpdate(BaseModel):
    # Allow updating metadata fields only (no IDs or sizes)
    type: Optional[str] = Field(
        None,
        pattern="^[TFLPO]$",
        description="Photo type: T=trigpoint, F=flush bracket, L=landscape, P=people, O=other",
    )
    name: Optional[str] = Field(
        None,
        serialization_alias="caption",
        validation_alias=AliasChoices("caption", "name"),
    )
    text_desc: Optional[str] = None
    public_ind: Optional[str] = Field(
        None,
        min_length=1,
        max_length=1,
        serialization_alias="license",
        validation_alias=AliasChoices("license", "public_ind"),
    )


class TPhotoCreate(BaseModel):
    # Creation fields (server and filenames are required for now; upload is out of scope)
    server_id: int
    type: str = Field(..., min_length=1, max_length=1)
    filename: str
    filesize: int
    height: int
    width: int
    icon_filename: str
    icon_filesize: int
    icon_height: int
    icon_width: int
    name: str = Field(
        serialization_alias="caption",
        validation_alias=AliasChoices("caption", "name"),
    )
    text_desc: str = ""
    public_ind: str = Field(
        "Y",
        min_length=1,
        max_length=1,
        serialization_alias="license",
        validation_alias=AliasChoices("license", "public_ind"),
    )


class TPhotoUpload(BaseModel):
    """Schema for photo upload requests."""

    name: str = Field(
        min_length=1,
        max_length=80,
        description="Photo caption",
        serialization_alias="caption",
        validation_alias=AliasChoices("caption", "name"),
    )
    text_desc: str = Field(default="", max_length=1000, description="Photo description")
    type: str = Field(
        pattern="^[TFLPO]$",
        description="Photo type: T=trigpoint, F=flush bracket, L=landscape, P=people, O=other",
    )
    licence: str = Field(
        pattern="^[YCN]$",
        description="Licence: Y=public domain, C=creative commons, N=private",
        serialization_alias="license",
        validation_alias=AliasChoices("license", "licence"),
    )

    class Config:
        from_attributes = True


class TPhotoRotateRequest(BaseModel):
    """Schema for photo rotation requests."""

    angle: int = Field(
        default=90,
        description="Rotation angle in degrees (90, 180, 270)",
    )

    @field_validator("angle")
    @classmethod
    def validate_angle(cls, v: int) -> int:
        if v not in [90, 180, 270]:
            raise ValueError("angle must be 90, 180, or 270 degrees")
        return v


class TPhotoEvaluationResponse(BaseModel):
    photo_id: int
    photo_accessible: bool
    icon_accessible: bool
    photo_dimension_match: bool
    icon_dimension_match: bool
    photo_width_actual: Optional[int] = None
    photo_height_actual: Optional[int] = None
    icon_width_actual: Optional[int] = None
    icon_height_actual: Optional[int] = None
    orientation_analysis: Optional[dict] = None
    content_moderation: Optional[dict] = None
    errors: List[str] = []
