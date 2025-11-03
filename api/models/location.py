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
    wgs_lat: Any = Column(DECIMAL(6, 5), nullable=False)
    wgs_long: Any = Column(DECIMAL(6, 5), nullable=False)
    osgb_eastings = Column(Integer, nullable=False)
    osgb_northings = Column(Integer, nullable=False)
    osgb_gridref = Column(CHAR(14), nullable=False)

    def __repr__(self):
        return f"<Town(name='{self.name}')>"


class Postcode6(Base):
    """Postcode model for 6-character postcodes."""

    __tablename__ = "postcode6"

    code = Column(CHAR(6), primary_key=True, nullable=False)
    code4 = Column(CHAR(4), nullable=False)
    wgs_lat: Any = Column(DECIMAL(6, 5), nullable=False)
    wgs_long: Any = Column(DECIMAL(6, 5), nullable=False)
    osgb_eastings = Column(Integer, nullable=False)
    osgb_northings = Column(Integer, nullable=False)
    osgb_gridref = Column(CHAR(14), nullable=False)
    county = Column(CHAR(20), nullable=False)
    town = Column(CHAR(50), nullable=False)
    postal_town = Column(CHAR(50), nullable=False)

    def __repr__(self):
        return f"<Postcode6(code='{self.code}', town='{self.town}')>"


class Postcode8(Base):
    """Postcode model for 8-character postcodes."""

    __tablename__ = "postcode8"

    code = Column(CHAR(8), primary_key=True, nullable=False)
    osgb_eastings = Column(Integer, nullable=False)
    osgb_northings = Column(Integer, nullable=False)
    source = Column(CHAR(20), nullable=False)

    def __repr__(self):
        return f"<Postcode8(code='{self.code}')>"
