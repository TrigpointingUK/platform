"""
SQLAlchemy models for location-related tables (towns, postcodes).
"""

from typing import Any

from sqlalchemy import CHAR, Column, Integer, String
from sqlalchemy.types import DECIMAL

from api.db.database import Base


class Town(Base):
    """Town model for the town table."""

    __tablename__ = "town"

    name = Column(String(25), primary_key=True, nullable=False)
    wgs_lat: Any = Column(DECIMAL(9, 6), nullable=False)
    wgs_long: Any = Column(DECIMAL(9, 6), nullable=False)
    osgb_eastings = Column(Integer, nullable=False)
    osgb_northings = Column(Integer, nullable=False)
    osgb_gridref = Column(CHAR(14), nullable=False)

    def __repr__(self):
        return f"<Town(name='{self.name}')>"


class Postcode(Base):
    """Postcode model for all UK postcodes from NSPL dataset."""

    __tablename__ = "postcodes"

    code = Column(String(10), primary_key=True, nullable=False)
    lat: Any = Column(DECIMAL(10, 7), nullable=False)
    long: Any = Column(DECIMAL(11, 7), nullable=False)

    def __repr__(self):
        return f"<Postcode(code='{self.code}')>"
