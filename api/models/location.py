"""
SQLAlchemy models for location-related tables (towns, postcodes).
Updated to use PostGIS GEOGRAPHY type for postcodes.
"""

import sys
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import CHAR, Column, Integer, String
from sqlalchemy.types import DECIMAL

from api.db.database import Base

# Detect if running under pytest (SQLite) to handle PostGIS types
_IS_SQLITE = "pytest" in sys.modules


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
    """Postcode model for all UK postcodes from NSPL dataset.

    Uses PostGIS GEOGRAPHY(POINT, 4326) for efficient spatial queries.
    The lat/long columns are retained for backward compatibility.
    """

    __tablename__ = "postcodes"

    code = Column(String(10), primary_key=True, nullable=False)
    lat: Any = Column(DECIMAL(10, 7), nullable=False)
    long: Any = Column(DECIMAL(11, 7), nullable=False)

    # PostGIS Geography column for WGS84 coordinates
    # Enables efficient KNN (k-nearest-neighbour) spatial queries
    location = Column(
        Geography(geometry_type="POINT", srid=4326) if not _IS_SQLITE else String(100),
        nullable=True if _IS_SQLITE else False,  # Nullable in SQLite tests
        index=(True if not _IS_SQLITE else False),  # Spatial index in PostgreSQL
    )

    def __repr__(self):
        return f"<Postcode(code='{self.code}')>"
