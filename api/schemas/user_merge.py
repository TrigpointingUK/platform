"""
Minimal schemas for email duplicate analysis in legacy endpoints.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel


class UserActivitySummary(BaseModel):
    """Summary of a user's activity."""

    user_id: int
    username: str
    email: str
    last_activity: Optional[datetime] = None
    activity_counts: Dict[str, int] = {}


class EmailDuplicateInfo(BaseModel):
    """Information about users sharing an email address."""

    email: str
    user_count: int
    users: List[UserActivitySummary]


class EmailDuplicatesResponse(BaseModel):
    """Response for email duplicates analysis."""

    total_duplicate_emails: int
    duplicates: List[EmailDuplicateInfo]
