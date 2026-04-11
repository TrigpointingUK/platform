"""
SQLAlchemy models for geographic areas with polygon boundaries.

These tables store various types of area boundaries (historic counties,
administrative areas, OS map sheets, etc.) and enable spatial queries
to determine which areas contain a given trigpoint.
"""

import sys

from geoalchemy2 import Geography
from sqlalchemy import DECIMAL, Column, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from api.db.database import Base

# Detect if we're running tests (pytest imports this module when running tests)
_IS_SQLITE = "pytest" in sys.modules


class AreaType(Base):
    """
    Categories of area boundaries.

    Examples: historic_county, ceremonial_county, os_landranger, parish, etc.
    """

    __tablename__ = "area_type"

    id = Column(Integer, primary_key=True)
    code = Column(String(50), unique=True, nullable=False)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=True)
    source_url = Column(String(500), nullable=True)  # Attribution/data source

    # Self-referential for hierarchies (e.g., parish -> district -> county)
    parent_type_id = Column(Integer, ForeignKey("area_type.id"), nullable=True)

    # Relationships
    areas = relationship("Area", back_populates="area_type")
    parent_type = relationship("AreaType", remote_side=[id], backref="child_types")

    def __repr__(self):
        return f"<AreaType(id={self.id}, code='{self.code}', name='{self.name}')>"


class Area(Base):
    """
    Geographic areas with polygon boundaries.

    Stores boundary polygons for various types of areas (counties, map sheets,
    administrative regions, etc.) enabling spatial queries against trigpoints.
    """

    __tablename__ = "area"

    id = Column(Integer, primary_key=True)
    area_type_id = Column(
        Integer, ForeignKey("area_type.id"), nullable=False, index=True
    )

    # Identifiers
    code = Column(
        String(50), nullable=True, index=True
    )  # External code (ONS, OS, etc.)
    name = Column(String(255), nullable=False, index=True)

    # PostGIS Geography column for polygon/multipolygon boundaries
    # Using SRID 4326 (WGS84) for consistency with trig.location
    # MULTIPOLYGON handles both simple polygons and complex multi-part areas
    boundary = Column(
        (
            Geography(geometry_type="MULTIPOLYGON", srid=4326)
            if not _IS_SQLITE
            else String
        ),
        nullable=False,
    )

    # Optional hierarchy (e.g., parish -> district -> county -> region)
    parent_id = Column(Integer, ForeignKey("area.id"), nullable=True, index=True)

    # Store additional shapefile attributes as JSON
    properties = Column(Text, nullable=True)

    # Centroid coordinates for distance-based sorting
    center_lat: Column[DECIMAL] = Column(DECIMAL(11, 8), nullable=True)  # Latitude
    center_lon: Column[DECIMAL] = Column(DECIMAL(12, 8), nullable=True)  # Longitude

    # Relationships
    area_type = relationship("AreaType", back_populates="areas")
    parent = relationship("Area", remote_side=[id], backref="children")

    def __repr__(self):
        return f"<Area(id={self.id}, name='{self.name}', type_id={self.area_type_id})>"
