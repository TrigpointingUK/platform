"""
CRUD operations for trig table.
Updated to use PostGIS spatial functions for distance calculations.
"""

from typing import List, Optional

from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint
from sqlalchemy import Float, cast, func
from sqlalchemy.orm import Session

from api.models.trig import Trig
from api.models.user import TLog


def _is_sqlite(db: Session) -> bool:
    """Check if the database is SQLite."""
    return db.bind.dialect.name == "sqlite"  # type: ignore[union-attr]


def get_trig_by_id(db: Session, trig_id: int) -> Optional[Trig]:
    """
    Get a trigpoint by ID.

    Args:
        db: Database session
        trig_id: Trigpoint ID

    Returns:
        Trig object or None if not found
    """
    return db.query(Trig).filter(Trig.id == trig_id).first()


def get_trig_by_waypoint(db: Session, waypoint: str) -> Optional[Trig]:
    """
    Get a trigpoint by waypoint code.

    Args:
        db: Database session
        waypoint: Waypoint code (e.g., "TP0001")

    Returns:
        Trig object or None if not found
    """
    return db.query(Trig).filter(Trig.waypoint == waypoint).first()


def get_trigs_by_county(
    db: Session, county: str, skip: int = 0, limit: int = 100
) -> list[Trig]:
    """
    Get trigpoints by county.

    Args:
        db: Database session
        county: County name
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of Trig objects
    """
    return db.query(Trig).filter(Trig.county == county).offset(skip).limit(limit).all()


def search_trigs_by_name(
    db: Session, name_pattern: str, skip: int = 0, limit: int = 100
) -> list[Trig]:
    """
    Search trigpoints by name pattern.

    Args:
        db: Database session
        name_pattern: Name pattern to search for (case-insensitive)
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of Trig objects
    """
    return (
        db.query(Trig)
        .filter(Trig.name.ilike(f"%{name_pattern}%"))
        .offset(skip)
        .limit(limit)
        .all()
    )


def get_trigs_count(db: Session) -> int:
    """
    Get total number of trigpoints.

    Args:
        db: Database session

    Returns:
        Total count of trigpoints
    """
    return db.query(Trig).count()


def list_trigs_filtered(
    db: Session,
    *,
    name: Optional[str] = None,
    county: Optional[str] = None,
    skip: int = 0,
    limit: int = 100,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    max_km: Optional[float] = None,
    order: Optional[str] = None,
    physical_types: Optional[List[str]] = None,
    exclude_found_by_user_id: Optional[int] = None,
) -> list[Trig]:
    query = db.query(Trig)

    # Filter by physical types
    if physical_types:
        query = query.filter(Trig.physical_type.in_(physical_types))

    # Exclude trigpoints already found by user
    if exclude_found_by_user_id is not None:
        # LEFT JOIN to find trigs NOT logged by this user
        subquery = (
            db.query(TLog.trig_id)
            .filter(TLog.user_id == exclude_found_by_user_id)
            .distinct()
            .subquery()
        )
        query = query.filter(~Trig.id.in_(subquery))  # type: ignore[arg-type]

    if name:
        query = query.filter(Trig.name.ilike(f"%{name}%"))
    if county:
        query = query.filter(Trig.county == county)

    if center_lat is not None and center_lon is not None:
        if _is_sqlite(db):
            # For SQLite tests, use a simple haversine distance calculation
            # This is less accurate but sufficient for testing
            lat1_rad = func.radians(center_lat)
            lat2_rad = func.radians(Trig.wgs_lat)
            lon1_rad = func.radians(center_lon)
            lon2_rad = func.radians(Trig.wgs_long)

            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad

            a = func.sin(dlat / 2) * func.sin(dlat / 2) + func.cos(lat1_rad) * func.cos(
                lat2_rad
            ) * func.sin(dlon / 2) * func.sin(dlon / 2)
            c = 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))
            distance_m = cast(6371000 * c, Float).label(
                "distance_m"
            )  # Earth radius in meters

            query = query.add_columns(distance_m)

            if max_km is not None:
                query = query.having(distance_m < max_km * 1000)

            if order in (None, "", "distance"):
                query = query.order_by(distance_m)
        else:
            # Use PostGIS for native spatial calculations
            # Create a geography point from the center coordinates (WGS84, SRID 4326)
            center_point = ST_MakePoint(center_lon, center_lat, type_="geography")

            # Calculate distance in meters using PostGIS ST_Distance
            # ST_Distance on geography types returns meters (spherical earth calculation)
            distance_m = ST_Distance(Trig.location, center_point).label("distance_m")

            # Add distance to the query for ordering
            query = query.add_columns(distance_m)

            if max_km is not None:
                # Use ST_DWithin for efficient distance filtering with spatial index
                # ST_DWithin is much faster than calculating distance for all records
                query = query.filter(
                    ST_DWithin(Trig.location, center_point, max_km * 1000)  # meters
                )

            # Order by distance if requested or default when lat/lon supplied
            if order in (None, "", "distance"):
                query = query.order_by(distance_m)
    else:
        # deterministic default
        if order in (None, "", "id"):
            query = query.order_by(Trig.id.asc())
        elif order == "name":
            query = query.order_by(Trig.name.asc())

    # Extract only the Trig objects if we added distance column
    if center_lat is not None and center_lon is not None:
        results = query.offset(skip).limit(limit).all()
        return [row[0] for row in results]  # Extract Trig from (Trig, distance) tuples

    return query.offset(skip).limit(limit).all()


def count_trigs_filtered(
    db: Session,
    *,
    name: Optional[str] = None,
    county: Optional[str] = None,
    center_lat: Optional[float] = None,
    center_lon: Optional[float] = None,
    max_km: Optional[float] = None,
    physical_types: Optional[List[str]] = None,
    exclude_found_by_user_id: Optional[int] = None,
) -> int:
    query = db.query(func.count(Trig.id))

    # Filter by physical types
    if physical_types:
        query = query.filter(Trig.physical_type.in_(physical_types))

    # Exclude trigpoints already found by user
    if exclude_found_by_user_id is not None:
        subquery = (
            db.query(TLog.trig_id)
            .filter(TLog.user_id == exclude_found_by_user_id)
            .distinct()
            .subquery()
        )
        query = query.filter(~Trig.id.in_(subquery))  # type: ignore[arg-type]

    if name:
        query = query.filter(Trig.name.ilike(f"%{name}%"))
    if county:
        query = query.filter(Trig.county == county)

    # Apply the same geo-distance filtering as in list_trigs_filtered (PostGIS or SQLite)
    if center_lat is not None and center_lon is not None:
        if _is_sqlite(db):
            # For SQLite, use haversine formula
            lat1_rad = func.radians(center_lat)
            lat2_rad = func.radians(Trig.wgs_lat)
            lon1_rad = func.radians(center_lon)
            lon2_rad = func.radians(Trig.wgs_long)

            dlat = lat2_rad - lat1_rad
            dlon = lon2_rad - lon1_rad

            a = func.sin(dlat / 2) * func.sin(dlat / 2) + func.cos(lat1_rad) * func.cos(
                lat2_rad
            ) * func.sin(dlon / 2) * func.sin(dlon / 2)
            c = 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))
            distance_m = cast(6371000 * c, Float)  # Earth radius in meters

            if max_km is not None:
                query = query.filter(distance_m < max_km * 1000)
        else:
            # Use PostGIS
            center_point = ST_MakePoint(center_lon, center_lat, type_="geography")
            if max_km is not None:
                query = query.filter(
                    ST_DWithin(Trig.location, center_point, max_km * 1000)  # meters
                )

    return int(query.scalar() or 0)
