"""
Schemas for contact form endpoints.
"""

from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator


class ContactRequest(BaseModel):
    """Request schema for contact form submission."""

    name: str = Field(..., min_length=1, max_length=100, description="Sender's name")
    email: EmailStr = Field(..., description="Sender's email address")
    subject: str = Field(..., min_length=1, max_length=200, description="Email subject")
    message: str = Field(
        ..., min_length=1, max_length=5000, description="Message content"
    )
    user_id: Optional[int] = Field(
        None, description="Database user ID (for logged-in users)"
    )
    auth0_user_id: Optional[str] = Field(
        None, description="Auth0 user ID (for logged-in users)"
    )
    username: Optional[str] = Field(
        None, description="Username/nickname (for logged-in users)"
    )

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Name cannot be empty")
        return v.strip()

    @field_validator("subject")
    @classmethod
    def validate_subject(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Subject cannot be empty")
        return v.strip()

    @field_validator("message")
    @classmethod
    def validate_message(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Message cannot be empty")
        return v.strip()


class ContactResponse(BaseModel):
    """Response schema for contact form submission."""

    success: bool = Field(..., description="Whether the email was sent successfully")
    message: str = Field(..., description="Response message")
