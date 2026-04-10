"""
Database models for trig lists (user-curated collections of trigpoints).
"""

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB

from api.db.database import Base


class TrigList(Base):
    """A user-owned, ordered list of trigpoints."""

    __tablename__ = "trig_list"
    __table_args__ = (
        CheckConstraint(
            "visibility IN ('private', 'public', 'admins')",
            name="ck_trig_list_visibility",
        ),
        CheckConstraint(
            "editability IN ('private', 'public', 'admins')",
            name="ck_trig_list_editability",
        ),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    owner_id = Column(
        Integer, ForeignKey("user.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    visibility = Column(String(10), nullable=False, default="private")
    editability = Column(String(10), nullable=False, default="private")
    position = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)


class TrigListItem(Base):
    """An entry linking a trig to a list, with ordering and metadata."""

    __tablename__ = "trig_list_item"
    __table_args__ = (
        UniqueConstraint("list_id", "trig_id", name="uq_trig_list_item_list_trig"),
        Index("ix_trig_list_item_list_position", "list_id", "position"),
    )

    id = Column(Integer, primary_key=True, autoincrement=True)
    list_id = Column(
        Integer, ForeignKey("trig_list.id", ondelete="CASCADE"), nullable=False
    )
    trig_id = Column(
        Integer, ForeignKey("trig.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_by = Column(
        Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    updated_by = Column(
        Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )
    name = Column(String(200), nullable=True)
    description = Column(Text, nullable=True)
    metadata_ = Column("metadata", JSONB, nullable=True, default=dict)
    position = Column(Integer, nullable=False)
    created_at = Column(DateTime, nullable=False, server_default=func.now())
    updated_at = Column(DateTime, nullable=True)
