"""
SQLAlchemy model for the trig_variant lookup table.

A variant qualifies a trig's type without adding a type of its own, e.g. the
detector material of a Buried Block ("Buried Block (concrete ring)"). Variants
are grouped (group_code), and trig_type.variant_group says which group, if
any, trigs of that type may choose from. New kinds of differentiation are new
rows here, not schema changes.
"""

from sqlalchemy import Column, Integer, SmallInteger, String

from api.db.database import Base

# Pseudo variant code for filtering: trigs with no variant recorded
NOT_RECORDED_CODE = "NOT_RECORDED"


class TrigVariant(Base):
    """One variant value within a variant group."""

    __tablename__ = "trig_variant"

    id = Column(Integer, primary_key=True)
    # Group this value belongs to, e.g. "DETECTOR" / "Detector material"
    group_code = Column(String(20), nullable=False, index=True)
    group_name = Column(String(30), nullable=False)
    code = Column(String(20), nullable=False, unique=True)
    name = Column(String(30), nullable=False)
    sort_order = Column(SmallInteger, nullable=False)

    def __repr__(self):
        return f"<TrigVariant(id={self.id}, group='{self.group_code}', code='{self.code}')>"
