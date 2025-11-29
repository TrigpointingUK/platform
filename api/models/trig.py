"""
SQLAlchemy model for the trig table - UK trigonometric stations.
Updated to use PostGIS GEOGRAPHY types for spatial data.
"""

import sys
from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import (
    CHAR,
    DECIMAL,
    TIMESTAMP,
    Column,
    Date,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.ext.hybrid import hybrid_property

from api.db.database import Base

# Note: MEDIUMINT and TINYINT are MySQL-specific, using Integer/SmallInteger for PostgreSQL

# Detect if we're running tests (pytest imports this module when running tests)
_IS_SQLITE = "pytest" in sys.modules


class Trig(Base):
    """Trig model for UK trigonometric stations."""

    __tablename__ = "trig"

    # Primary key
    id = Column(Integer, primary_key=True, index=True)

    # Identifiers
    waypoint = Column(String(8), nullable=False, index=True)  # e.g., "TP0001"
    name = Column(String(50), nullable=False, index=True)  # Trigpoint name
    fb_number = Column(String(10), nullable=False)  # Flush bracket number

    # Station numbers (various systems)
    stn_number = Column(String(20), nullable=False)
    stn_number_active = Column(String(20), nullable=True)
    stn_number_passive = Column(String(20), nullable=True)
    stn_number_osgb36 = Column(String(20), nullable=True)

    # Status and classification
    status_id = Column(Integer, nullable=False, index=True)
    user_added = Column(SmallInteger, nullable=False, default=0)
    current_use = Column(String(25), nullable=False)  # e.g., "Passive station"
    historic_use = Column(String(30), nullable=False)  # e.g., "Primary"
    physical_type = Column(String(25), nullable=False)  # e.g., "Pillar"
    condition = Column(CHAR(1), nullable=False)  # G=Good, etc.

    # PostGIS Geography column for WGS84 coordinates
    # This stores coordinates as a GEOGRAPHY(POINT, 4326) type
    # Enables native PostGIS spatial queries and proper spherical earth calculations
    location = Column(
        Geography(geometry_type="POINT", srid=4326) if not _IS_SQLITE else String(100),
        nullable=True,  # Nullable during migration
        index=(
            True if not _IS_SQLITE else False
        ),  # Spatial index will be created in PostgreSQL
    )

    # Legacy WGS84 coordinate columns (maintained for backward compatibility)
    # These will be deprecated once all code is updated to use PostGIS
    wgs_lat: Any = Column(DECIMAL(7, 5), nullable=False)  # Latitude
    wgs_long: Any = Column(DECIMAL(7, 5), nullable=False)  # Longitude
    wgs_height = Column(Integer, nullable=False)  # Height in meters

    @hybrid_property
    def latitude(self) -> float:
        """Extract latitude from PostGIS location column."""
        if not _IS_SQLITE and self.location is not None:
            from geoalchemy2.functions import ST_Y

            return float(ST_Y(self.location))
        return float(self.wgs_lat)

    @hybrid_property
    def longitude(self) -> float:
        """Extract longitude from PostGIS location column."""
        if not _IS_SQLITE and self.location is not None:
            from geoalchemy2.functions import ST_X

            return float(ST_X(self.location))
        return float(self.wgs_long)

    # OSGB coordinates
    osgb_eastings = Column(Integer, nullable=False)  # Eastings
    osgb_northings = Column(Integer, nullable=False)  # Northings
    osgb_gridref = Column(String(14), nullable=False)  # Grid reference
    osgb_height = Column(Integer, nullable=False)  # Height in meters

    # Location information
    postcode = Column(String(10), nullable=False)  # Postcode
    county = Column(String(20), nullable=False)  # County
    town = Column(String(50), nullable=False)  # Town/area

    # Administrative fields
    permission_ind = Column(CHAR(1), nullable=False)  # Permission indicator
    needs_attention = Column(SmallInteger, nullable=False, default=0)
    attention_comment = Column(Text, nullable=False)

    # External system integration
    os_net_web_id = Column(Integer, nullable=True)  # OS Net Web ID

    # Audit fields - creation
    crt_date = Column(Date, nullable=False)  # Creation date
    crt_time = Column(Time, nullable=False)  # Creation time
    crt_user_id = Column(Integer, nullable=False)  # Creating user ID
    crt_ip_addr = Column(String(15), nullable=False)  # Creating IP address

    # Audit fields - admin updates
    admin_user_id = Column(Integer, nullable=True)  # Admin user ID
    admin_timestamp = Column(TIMESTAMP, nullable=True)  # Admin update time
    admin_ip_addr = Column(String(15), nullable=True)  # Admin IP address

    # Audit fields - last update
    upd_timestamp = Column(TIMESTAMP, nullable=True)  # Last update time

    def __repr__(self):
        return f"<Trig(id={self.id}, waypoint='{self.waypoint}', name='{self.name}')>"
