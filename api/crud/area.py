"""
CRUD operations for area and area_type tables.
Uses PostGIS spatial functions for containment queries.
"""

from typing import Any, Optional

import sqlalchemy as sa
from geoalchemy2 import Geometry
from geoalchemy2.functions import ST_AsGeoJSON, ST_Covers, ST_MakePoint, ST_SetSRID
from sqlalchemy import cast, func
from sqlalchemy.orm import Session

from api.models.area import Area, AreaType
from api.models.user import TLog

# Reference to the trig_area table for efficient trig-to-area lookups
# (Previously a materialized view, now a table with triggers for incremental updates)
TRIG_AREA = sa.table(
    "trig_area",
    sa.column("trig_id", sa.Integer),
    sa.column("area_id", sa.Integer),
    sa.column("area_type_id", sa.Integer),
    sa.column("area_type_code", sa.String),
)


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
    # Cast Geography to Geometry for efficient spatial index usage.
    # Geography type uses expensive spheroidal calculations; Geometry
    # uses planar calculations which are much faster and the GIST index
    # works more efficiently. This matches the materialized view approach.
    query = (
        db.query(Area)
        .join(AreaType, Area.area_type_id == AreaType.id)
        .filter(
            ST_Covers(
                cast(Area.boundary, Geometry),
                cast(point, Geometry),
            )
        )
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


def get_area_boundary_geojson(db: Session, area_id: int) -> Optional[dict[str, Any]]:
    """
    Get an area's boundary as GeoJSON.

    Uses PostGIS ST_AsGeoJSON to convert the boundary geometry to GeoJSON format.

    Args:
        db: Database session
        area_id: Area ID

    Returns:
        Dictionary with area info and GeoJSON boundary, or None if not found.
        Format: {
            "id": int,
            "name": str,
            "code": str | None,
            "area_type": {"id": int, "code": str, "name": str},
            "boundary": GeoJSON object (parsed from ST_AsGeoJSON)
        }
    """
    import json

    if _is_sqlite(db):
        # SQLite doesn't support PostGIS - return None for tests
        return None

    # Query area with boundary as GeoJSON
    result = (
        db.query(
            Area.id,
            Area.name,
            Area.code,
            Area.area_type_id,
            ST_AsGeoJSON(Area.boundary).label("boundary_geojson"),
        )
        .filter(Area.id == area_id)
        .first()
    )

    if result is None:
        return None

    # Get area type info
    area_type = get_area_type_by_id(db, result.area_type_id)
    if area_type is None:
        return None

    # Parse GeoJSON string to dict
    boundary_dict = json.loads(result.boundary_geojson)

    return {
        "id": result.id,
        "name": result.name,
        "code": result.code,
        "area_type": {
            "id": int(area_type.id),
            "code": str(area_type.code),
            "name": str(area_type.name),
            "description": (
                str(area_type.description) if area_type.description else None
            ),
        },
        "boundary": boundary_dict,
    }


def get_user_log_counts_by_area(
    db: Session,
    user_id: int,
    area_type_code: str,
) -> list[dict[str, Any]]:
    """
    Get user's log counts grouped by area for a specific area type.

    Uses the trig_area table for efficient trig-to-area lookups
    (precomputed spatial containment). Counts distinct trigpoints (not individual
    logs) for each area.

    Args:
        db: Database session
        user_id: User ID to get log counts for
        area_type_code: Area type code (e.g., "county_1991")

    Returns:
        List of dicts with area_name and count, ordered by count descending.
        Format: [{"area_name": str, "count": int}, ...]
    """
    if _is_sqlite(db):
        # SQLite doesn't support the trig_area table - return empty list for tests
        return []

    # Query: join user's logged trigs with areas via the trig_area table
    # trig_area has area_type_code so we can filter directly
    query = (
        db.query(
            Area.name.label("area_name"),
            func.count(func.distinct(TLog.trig_id)).label("trig_count"),
        )
        .select_from(TLog)
        .join(TRIG_AREA, TRIG_AREA.c.trig_id == TLog.trig_id)
        .join(Area, Area.id == TRIG_AREA.c.area_id)
        .filter(
            TLog.user_id == user_id,
            TRIG_AREA.c.area_type_code == area_type_code,
        )
        .group_by(Area.name)
        .order_by(func.count(func.distinct(TLog.trig_id)).desc())
    )

    results = query.all()

    return [
        {"area_name": str(row.area_name), "count": int(row.trig_count)}
        for row in results
    ]


# Area type ID for county_1991 (UK Counties 1991)
COUNTY_1991_AREA_TYPE_ID = 7


def get_county_name_for_trig(db: Session, trig_id: int) -> Optional[str]:
    """
    Get the county name for a trigpoint from the trig_area table.

    Uses area_type_id = 7 (county_1991) to find the county.

    Args:
        db: Database session
        trig_id: Trig ID to look up

    Returns:
        County name string, or None if not found
    """
    if _is_sqlite(db):
        # SQLite doesn't have the trig_area table - return None for tests
        return None

    # Check if trig_area table exists before querying
    try:
        from typing import Any, cast

        from sqlalchemy import inspect

        inspector = cast(Any, inspect(db.bind))
        if "trig_area" not in inspector.get_table_names():
            return None
    except Exception:
        return None

    result = (
        db.query(Area.name)
        .join(TRIG_AREA, TRIG_AREA.c.area_id == Area.id)
        .filter(
            TRIG_AREA.c.trig_id == trig_id,
            TRIG_AREA.c.area_type_id == COUNTY_1991_AREA_TYPE_ID,
        )
        .first()
    )

    return str(result[0]) if result else None
