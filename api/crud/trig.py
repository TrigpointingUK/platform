"""
CRUD operations for trig table.
"""

from typing import List, Optional

from sqlalchemy import Float, cast, func, literal
from sqlalchemy.orm import Session

from api.models.trig import Trig
from api.models.user import TLog


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
        deg_km = 111.32
        lat = literal(center_lat)
        lon = literal(center_lon)
        cos_lat = func.cos(func.radians(lat))
        # cast DECIMAL to float for math ops
        dlat_km = (cast(Trig.wgs_lat, Float) - lat) * deg_km
        dlon_km = (cast(Trig.wgs_long, Float) - lon) * deg_km * cos_lat
        dist2 = (dlat_km * dlat_km + dlon_km * dlon_km).label("dist2")

        if max_km is not None:
            query = query.filter(dist2 <= (max_km * max_km))

        # order by distance if requested or default when lat/lon supplied
        if order in (None, "", "distance"):
            query = query.order_by(dist2)
    else:
        # deterministic default
        if order in (None, "", "id"):
            query = query.order_by(Trig.id.asc())
        elif order == "name":
            query = query.order_by(Trig.name.asc())

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

    # Apply the same geo-distance filtering as in list_trigs_filtered
    if center_lat is not None and center_lon is not None:
        deg_km = 111.32
        lat = literal(center_lat)
        lon = literal(center_lon)
        cos_lat = func.cos(func.radians(lat))
        dlat_km = (cast(Trig.wgs_lat, Float) - lat) * deg_km
        dlon_km = (cast(Trig.wgs_long, Float) - lon) * deg_km * cos_lat
        dist2 = dlat_km * dlat_km + dlon_km * dlon_km
        if max_km is not None:
            query = query.filter(dist2 <= (max_km * max_km))

    return int(query.scalar() or 0)
