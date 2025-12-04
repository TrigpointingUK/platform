"""
CRUD operations for area and area_type tables.
Uses PostGIS spatial functions for containment queries.
"""

from typing import Optional

from geoalchemy2.functions import ST_Covers, ST_MakePoint, ST_SetSRID
from sqlalchemy.orm import Session

from api.models.area import Area, AreaType


def _is_sqlite(db: Session) -> bool:
    """Check if the database is SQLite."""
    return db.bind.dialect.name == "sqlite"  # type: ignore[union-attr]


def get_areas_containing_point(
    db: Session,
    lat: float,
    lon: float,
) -> list[Area]:
    """
    Get all areas that contain the given point.

    Uses PostGIS ST_Covers to check if the area boundary covers the point.
    Returns areas with their area_type relationship loaded, ordered by
    area_type.name then area.name.

    Args:
        db: Database session
        lat: Latitude (WGS84)
        lon: Longitude (WGS84)

    Returns:
        List of Area objects with area_type loaded
    """
    if _is_sqlite(db):
        # SQLite doesn't support PostGIS - return empty list for tests
        return []

    # Create a point geometry from lat/lon
    # Note: ST_MakePoint takes (x, y) = (lon, lat)
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Query areas where the boundary covers the point
    # Cast boundary to geometry for ST_Covers comparison
    query = (
        db.query(Area)
        .join(AreaType, Area.area_type_id == AreaType.id)
        .filter(ST_Covers(Area.boundary, point))
        .order_by(AreaType.name, Area.name)
    )

    return query.all()


def get_area_by_id(db: Session, area_id: int) -> Optional[Area]:
    """
    Get an area by ID.

    Args:
        db: Database session
        area_id: Area ID

    Returns:
        Area object or None if not found
    """
    return db.query(Area).filter(Area.id == area_id).first()


def get_area_type_by_id(db: Session, area_type_id: int) -> Optional[AreaType]:
    """
    Get an area type by ID.

    Args:
        db: Database session
        area_type_id: Area type ID

    Returns:
        AreaType object or None if not found
    """
    return db.query(AreaType).filter(AreaType.id == area_type_id).first()


def get_area_type_by_code(db: Session, code: str) -> Optional[AreaType]:
    """
    Get an area type by code.

    Args:
        db: Database session
        code: Area type code (e.g., "historic_county")

    Returns:
        AreaType object or None if not found
    """
    return db.query(AreaType).filter(AreaType.code == code).first()


def list_area_types(db: Session) -> list[AreaType]:
    """
    List all area types.

    Args:
        db: Database session

    Returns:
        List of AreaType objects ordered by name
    """
    return db.query(AreaType).order_by(AreaType.name).all()


def list_areas_by_type(
    db: Session,
    area_type_id: int,
    skip: int = 0,
    limit: int = 100,
) -> list[Area]:
    """
    List areas of a specific type.

    Args:
        db: Database session
        area_type_id: Area type ID to filter by
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of Area objects ordered by name
    """
    return (
        db.query(Area)
        .filter(Area.area_type_id == area_type_id)
        .order_by(Area.name)
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_areas_by_type(db: Session, area_type_id: int) -> int:
    """
    Count areas of a specific type.

    Args:
        db: Database session
        area_type_id: Area type ID to filter by

    Returns:
        Count of areas
    """
    return db.query(Area).filter(Area.area_type_id == area_type_id).count()
