"""
SQLAlchemy models for the trig_type_group and trig_type tables.

These tables provide a two-level hierarchy for trigpoint classification:
- trig_type_group: High-level groupings (Pillar, FBM, Minor mark, etc.)
- trig_type: Specific types within each group (Hotine, Vanessa, Bolt, etc.)
"""

from sqlalchemy import (
    Column,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from api.db.database import Base


class TrigTypeGroup(Base):
    """High-level grouping of trigpoint types."""

    __tablename__ = "trig_type_group"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(30), nullable=False)
    description = Column(String(100), nullable=True)
    wiki_url = Column(String(255), nullable=True)
    sort_order = Column(SmallInteger, nullable=False, unique=True)

    # Relationship to types in this group
    types = relationship("TrigType", back_populates="group", lazy="selectin")

    def __repr__(self):
        return f"<TrigTypeGroup(id={self.id}, code='{self.code}', name='{self.name}')>"


class TrigType(Base):
    """Specific trigpoint type within a group."""

    __tablename__ = "trig_type"
    __table_args__ = (
        UniqueConstraint("group_id", "sort_order", name="uq_trig_type_group_sort"),
        # Explicit index name to avoid collision with ix_trig_type_group_id (from trig_type_group.id)
        Index("ix_trig_type_grp_id", "group_id"),
    )

    id = Column(Integer, primary_key=True, index=True)
    # Note: index name explicitly set to avoid collision with ix_trig_type_group_id
    group_id = Column(
        Integer,
        ForeignKey("trig_type_group.id"),
        nullable=False,
    )
    code = Column(String(20), nullable=False, unique=True, index=True)
    name = Column(String(30), nullable=False)
    description = Column(String(100), nullable=True)
    wiki_url = Column(String(255), nullable=True)
    sort_order = Column(SmallInteger, nullable=False)
    legacy_physical_type = Column(String(25), nullable=True)

    # Relationship to parent group (joined to avoid N+1 when accessing trig.trig_type.group)
    group = relationship("TrigTypeGroup", back_populates="types", lazy="joined")

    # Relationship to trigs of this type
    trigs = relationship("Trig", back_populates="trig_type", lazy="dynamic")

    def __repr__(self):
        return f"<TrigType(id={self.id}, code='{self.code}', name='{self.name}')>"
