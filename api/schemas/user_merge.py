"""
Schemas for user merge operations.
"""

from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class UserActivitySummary(BaseModel):
    """Summary of a user's activity."""

    user_id: int
    username: str
    email: str
    last_activity: Optional[datetime] = None
    activity_counts: Dict[str, int] = Field(
        default_factory=dict,
        description="Counts by activity type: logs, photos, photo_votes, queries, quiz_scores",
    )


class EmailDuplicateInfo(BaseModel):
    """Information about users sharing an email address."""

    email: str
    user_count: int
    users: List[UserActivitySummary]


class EmailDuplicatesResponse(BaseModel):
    """Response for email duplicates analysis."""

    total_duplicate_emails: int
    duplicates: List[EmailDuplicateInfo]


class UserMergeRequest(BaseModel):
    """Request to merge users with duplicate email."""

    email: str = Field(..., min_length=1, max_length=255, description="Email address")
    activity_threshold_days: int = Field(
        default=180,
        ge=1,
        le=3650,
        description="Days threshold for activity conflict detection (default 180 = 6 months)",
    )
    dry_run: bool = Field(
        default=True,
        description="If true, only preview the merge without executing it",
    )

    @field_validator("email")
    @classmethod
    def validate_email(cls, v: str) -> str:
        """Validate email format."""
        if not v or not v.strip():
            raise ValueError("Email is required")
        return v.strip()


class ConflictingUser(BaseModel):
    """Information about a user that conflicts with merge."""

    user_id: int
    username: str
    last_activity: Optional[datetime]
    days_since_primary: Optional[float] = Field(
        None, description="Days between this user's and primary user's last activity"
    )


class UserMergeConflict(BaseModel):
    """Conflict information when merge cannot proceed."""

    error: str = "merge_conflict"
    message: str
    email: str
    primary_user: ConflictingUser
    conflicting_users: List[ConflictingUser]
    threshold_days: int


class RecordCounts(BaseModel):
    """Counts of records updated during merge."""

    tlog: int = 0
    tphoto: int = 0
    tphotovote: int = 0
    tquery: int = 0
    tquizscores: int = 0


class UserMergePreview(BaseModel):
    """Preview of merge operation."""

    dry_run: bool = True
    email: str
    primary_user_id: int
    primary_username: str
    users_to_merge: List[int]
    usernames_to_merge: List[str]
    estimated_records: RecordCounts
    profile_updates: Dict[str, Optional[str]] = Field(
        description="Profile fields that will be updated on primary user"
    )


class UserMergeResult(BaseModel):
    """Result of successful merge operation."""

    success: bool = True
    email: str
    primary_user_id: int
    primary_username: str
    merged_user_ids: List[int]
    merged_usernames: List[str]
    updated_records: RecordCounts
    profile_updated: bool = False
