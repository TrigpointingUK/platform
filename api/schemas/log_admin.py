"""
Pydantic schemas for admin log management endpoints.
"""

from datetime import date as DateType
from datetime import time as TimeType
from typing import Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class LogNeedsAttentionSummary(BaseModel):
    """Summary statistics for logs needing attention."""

    orphaned_count: int = Field(
        ..., description="Number of logs for deleted trigpoints"
    )
    duplicate_count: int = Field(..., description="Number of duplicate log entries")


class OrphanedLogItem(BaseModel):
    """List item for orphaned logs (logs referencing deleted trigpoints)."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Log ID")
    trig_id: Optional[int] = Field(None, description="Trigpoint ID (deleted)")
    user_id: Optional[int] = Field(None, description="User ID")
    user_name: Optional[str] = Field(None, description="Username")
    date: Optional[DateType] = Field(None, description="Log date")
    time: Optional[TimeType] = Field(None, description="Log time")
    condition: Optional[str] = Field(None, description="Condition code")
    comment: Optional[str] = Field(None, description="Log comment")
    score: Optional[int] = Field(None, description="Score")
    issue_type: Literal["orphaned"] = Field(
        default="orphaned", description="Issue type identifier"
    )


class DuplicateLogItem(BaseModel):
    """List item for duplicate logs."""

    model_config = ConfigDict(from_attributes=True)

    id: int = Field(..., description="Log ID")
    trig_id: Optional[int] = Field(None, description="Trigpoint ID")
    trig_name: Optional[str] = Field(None, description="Trigpoint name")
    trig_waypoint: Optional[str] = Field(None, description="Trigpoint waypoint")
    user_id: Optional[int] = Field(None, description="User ID")
    user_name: Optional[str] = Field(None, description="Username")
    date: Optional[DateType] = Field(None, description="Log date")
    time: Optional[TimeType] = Field(None, description="Log time")
    condition: Optional[str] = Field(None, description="Condition code")
    comment: Optional[str] = Field(None, description="Log comment")
    score: Optional[int] = Field(None, description="Score")
    duplicate_count: int = Field(..., description="Number of duplicates in this group")
    issue_type: Literal["duplicate"] = Field(
        default="duplicate", description="Issue type identifier"
    )


class LogNeedsAttentionListResponse(BaseModel):
    """Response for logs needing attention list endpoint."""

    items: list[OrphanedLogItem | DuplicateLogItem] = Field(
        ..., description="List of logs needing attention"
    )
    pagination: dict = Field(..., description="Pagination information")
