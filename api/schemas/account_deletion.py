"""
Schemas for account deletion (self-service and admin).
"""

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AccountDeletionMode(str, Enum):
    """How to treat logs, photos, and the user row when deleting an account."""

    anonymise_keep_photos = "anonymise_keep_photos"
    anonymise_delete_photos = "anonymise_delete_photos"
    purge_all = "purge_all"


class AccountDeletionSummaryResponse(BaseModel):
    """Overview for the account deletion confirmation page."""

    user_id: int
    username: str
    full_name: str = ""
    email: str
    log_count: int
    photo_count: int


class AccountDeletionExecuteRequest(BaseModel):
    """Execute account deletion with the chosen data policy."""

    mode: AccountDeletionMode
    feedback: Optional[str] = Field(
        default=None,
        max_length=8000,
        description="Optional reason for leaving (sent to operations only).",
    )


class AccountDeletionExecuteResponse(BaseModel):
    """Outcome of a completed account deletion."""

    success: bool = True
    mode: AccountDeletionMode
    user_id: int
    previous_username: str
    new_username: Optional[str] = Field(
        default=None,
        description="Set when the account was anonymised in place.",
    )
    logs_anonymised: int = 0
    photos_deleted: int = 0
    logs_deleted: int = 0
    s3_photo_delete_failures: int = 0
    user_row_deleted: bool = False


class AccountDeletionEmailBackupResponse(BaseModel):
    """Acknowledgement after queuing a pre-deletion log archive email."""

    success: bool = True
    message: str = (
        "If your account has a valid email, you will receive a zip archive shortly."
    )
