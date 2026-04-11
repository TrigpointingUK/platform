"""
SQLAlchemy model for the trig table - UK trigonometric stations.
Updated to use PostGIS GEOGRAPHY types for spatial data.
"""

from typing import Any

from geoalchemy2 import Geography
from sqlalchemy import (
    CHAR,
    DECIMAL,
    TIMESTAMP,
    Column,
    Date,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    Text,
    Time,
)
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship

from api.db.database import Base

# Note: MEDIUMINT and TINYINT are MySQL-specific, using Integer/SmallInteger for PostgreSQL

# Always use Geography type (PostgreSQL with PostGIS)
_IS_SQLITE = False


class Trig(Base):
    """Trig model for UK trigonometric stations."""

    __tablename__ = "trig"
    __table_args__ = (
        # Explicit index name to avoid collision with ix_trig_type_id (from trig_type.id)
        Index("ix_trig_typeid", "type_id"),
    )

    # Primary key
    id = Column(Integer, primary_key=True)

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
    status_id = Column(
        Integer, ForeignKey("status.id", ondelete="SET NULL"), nullable=True, index=True
    )
    # New type system - FK to trig_type table
    # Note: explicit index name to avoid collision with ix_trig_type_id (from trig_type.id)
    type_id = Column(
        Integer,
        ForeignKey("trig_type.id", ondelete="SET NULL"),
        nullable=True,
    )
    user_added = Column(SmallInteger, nullable=False, default=0)
    current_use = Column(String(25), nullable=False)  # e.g., "Passive station"
    historic_use = Column(String(30), nullable=False)  # e.g., "Primary"
    condition = Column(CHAR(1), nullable=False)  # G=Good, etc.

    # Relationship to trig_type
    trig_type = relationship("TrigType", back_populates="trigs", lazy="joined")

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

    # WGS84 coordinate columns
    # High precision (8dp) to support source data with 6dp seconds accuracy (~1mm precision)
    wgs_lat: Any = Column(DECIMAL(11, 8), nullable=False)  # Latitude
    wgs_long: Any = Column(DECIMAL(12, 8), nullable=False)  # Longitude
    wgs_height: Any = Column(
        DECIMAL(8, 4), nullable=True
    )  # Height in metres (0.1mm precision)

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

    # Type system properties - expose relationship data for Pydantic serialization
    @property
    def type_code(self) -> str | None:
        """Type code from the trig_type relationship."""
        return self.trig_type.code if self.trig_type else None

    @property
    def type_name(self) -> str | None:
        """Type display name from the trig_type relationship."""
        return self.trig_type.name if self.trig_type else None

    @property
    def type_wiki_url(self) -> str | None:
        """Wiki URL from the trig_type relationship."""
        return self.trig_type.wiki_url if self.trig_type else None

    @property
    def category_code(self) -> str | None:
        """Category code from the trig_type.category relationship."""
        if self.trig_type and self.trig_type.category:
            return self.trig_type.category.code
        return None

    @property
    def category_name(self) -> str | None:
        """Category display name from the trig_type.category relationship."""
        if self.trig_type and self.trig_type.category:
            return self.trig_type.category.name
        return None

    @property
    def physical_type(self) -> str | None:
        """Legacy physical type from the trig_type relationship."""
        return self.trig_type.legacy_physical_type if self.trig_type else None

    # OSGB coordinates (4dp for 0.1mm precision)
    osgb_eastings: Any = Column(DECIMAL(10, 4), nullable=False)  # Eastings
    osgb_northings: Any = Column(
        DECIMAL(11, 4), nullable=False
    )  # Northings (11,4 for values >1M)
    osgb_gridref = Column(String(14), nullable=False)  # Grid reference
    osgb_height: Any = Column(
        DECIMAL(8, 4), nullable=True
    )  # Height in metres (0.1mm precision)

    # Location information
    postcode = Column(
        String(10),
        ForeignKey("postcodes.code", ondelete="SET NULL"),
        nullable=True,
    )  # Nearest postcode (FK to postcodes table, NULL if >5km away)
    # Note: county is now derived from trig_area join (area_type_id=7 = county_1991)
    town = Column(String(50), nullable=False)  # Town/area

    # Administrative fields
    permission_ind = Column(CHAR(1), nullable=False)  # Permission indicator
    needs_attention = Column(SmallInteger, nullable=False, default=0)
    attention_comment = Column(Text, nullable=False)

    # Audit fields - creation
    crt_date = Column(Date, nullable=False)  # Creation date
    crt_time = Column(Time, nullable=False)  # Creation time
    crt_user_id = Column(
        Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )  # Creating user ID
    crt_ip_addr = Column(String(15), nullable=False)  # Creating IP address

    # Audit fields - admin updates
    admin_user_id = Column(
        Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True
    )  # Admin user ID
    admin_timestamp = Column(TIMESTAMP, nullable=True)  # Admin update time
    admin_ip_addr = Column(String(15), nullable=True)  # Admin IP address

    # Audit fields - last update
    upd_timestamp = Column(TIMESTAMP, nullable=True)  # Last update time

    # Legal/access information
    legal_message = Column(
        Text, nullable=True
    )  # Optional legal/access message displayed on detail page (HTML)

    # Original location columns - official OS-published location
    # Base columns (wgs_*, osgb_*) store current/actual location
    # These columns store the original OS coordinates (may differ if trig has moved)
    original_wgs_lat: Any = Column(
        DECIMAL(11, 8), nullable=True
    )  # Official OS WGS84 latitude
    original_wgs_long: Any = Column(
        DECIMAL(12, 8), nullable=True
    )  # Official OS WGS84 longitude
    original_osgb_eastings: Any = Column(
        DECIMAL(10, 4), nullable=True
    )  # Official OS grid eastings
    original_osgb_northings: Any = Column(
        DECIMAL(11, 4), nullable=True
    )  # Official OS grid northings
    original_osgb_gridref = Column(
        String(14), nullable=True
    )  # Official OS grid reference
    original_grid_system = Column(CHAR(2), nullable=True)  # Grid system: 'gb' or 'ie'
    original_location = Column(
        Geography(geometry_type="POINT", srid=4326) if not _IS_SQLITE else String(100),
        nullable=True,
        index=(True if not _IS_SQLITE else False),
    )  # PostGIS point for original location spatial queries
    original_provenance = Column(
        Text, nullable=True
    )  # Notes for data cleansing tracking
    original_wgs_height: Any = Column(
        DECIMAL(8, 4), nullable=True
    )  # Official OS WGS84 height in metres
    original_osgb_height: Any = Column(
        DECIMAL(8, 4), nullable=True
    )  # Official OS OSGB height in metres

    def __repr__(self):
        return f"<Trig(id={self.id}, waypoint='{self.waypoint}', name='{self.name}')>"
