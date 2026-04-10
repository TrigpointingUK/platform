"""
SQLAlchemy models for the trig_category and trig_type tables.

These tables provide a two-level hierarchy for trigpoint classification:
- trig_category: High-level categories (Pillar, FBM, Minor mark, etc.)
- trig_type: Specific types within each category (Hotine, Vanessa, Bolt, etc.)
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


class TrigCategory(Base):
    """High-level category of trigpoint types."""

    __tablename__ = "trig_category"

    id = Column(Integer, primary_key=True)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(30), nullable=False)
    description = Column(String(100), nullable=True)
    wiki_url = Column(String(255), nullable=True)
    sort_order = Column(SmallInteger, nullable=False, unique=True)

    # Relationship to types in this category
    types = relationship("TrigType", back_populates="category", lazy="selectin")

    def __repr__(self):
        return f"<TrigCategory(id={self.id}, code='{self.code}', name='{self.name}')>"


class TrigType(Base):
    """Specific trigpoint type within a category."""

    __tablename__ = "trig_type"
    __table_args__ = (
        UniqueConstraint(
            "category_id", "sort_order", name="uq_trig_type_category_sort"
        ),
        # Explicit index name to avoid collision
        Index("ix_trig_type_category_id", "category_id"),
    )

    id = Column(Integer, primary_key=True)
    category_id = Column(
        Integer,
        ForeignKey("trig_category.id"),
        nullable=False,
    )
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(30), nullable=False)
    description = Column(String(100), nullable=True)
    wiki_url = Column(String(255), nullable=True)
    sort_order = Column(SmallInteger, nullable=False)
    legacy_physical_type = Column(String(25), nullable=True)

    # Relationship to parent category (joined to avoid N+1 when accessing trig.trig_type.category)
    category = relationship("TrigCategory", back_populates="types", lazy="joined")

    # Relationship to trigs of this type
    trigs = relationship("Trig", back_populates="trig_type", lazy="dynamic")

    def __repr__(self):
        return f"<TrigType(id={self.id}, code='{self.code}', name='{self.name}')>"
