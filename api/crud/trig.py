"""
CRUD operations for trig table.
Updated to use PostGIS spatial functions for distance calculations.
"""

from typing import List, Optional

from sqlalchemy import Float, cast, func
from sqlalchemy.orm import Session

from api.models.trig import Trig
from api.models.user import TLog

# PostGIS imports commented out until location column is populated
# from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint


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
    status_ids: Optional[List[int]] = None,
    max_status: Optional[int] = None,
    exclude_found_by_user_id: Optional[int] = None,
    exclude_soft_deleted: bool = True,
) -> list[Trig]:
    query = db.query(Trig)

    # Global filter: exclude soft-deleted records (status >= 90) unless explicitly requested
    if exclude_soft_deleted:
        query = query.filter(Trig.status_id < 90)

    # Filter by status IDs (specific statuses)
    if status_ids:
        query = query.filter(Trig.status_id.in_(status_ids))

    # Filter by max status (status <= max_status)
    if max_status is not None:
        query = query.filter(Trig.status_id <= max_status)

    # Filter by physical types (kept for backward compatibility)
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
        # TEMPORARILY: Use haversine formula for all databases until PostGIS location column is populated
        # TODO: Switch back to PostGIS ST_Distance when location column has data
        # For now, use a simple haversine distance calculation
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
    status_ids: Optional[List[int]] = None,
    max_status: Optional[int] = None,
    exclude_found_by_user_id: Optional[int] = None,
    exclude_soft_deleted: bool = True,
) -> int:
    query = db.query(func.count(Trig.id))

    # Global filter: exclude soft-deleted records (status >= 90) unless explicitly requested
    if exclude_soft_deleted:
        query = query.filter(Trig.status_id < 90)

    # Filter by status IDs (specific statuses)
    if status_ids:
        query = query.filter(Trig.status_id.in_(status_ids))

    # Filter by max status (status <= max_status)
    if max_status is not None:
        query = query.filter(Trig.status_id <= max_status)

    # Filter by physical types (kept for backward compatibility)
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
        # TEMPORARILY: Use haversine formula for all databases until PostGIS location column is populated
        # TODO: Switch back to PostGIS ST_DWithin when location column has data
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

    return int(query.scalar() or 0)


def get_trigs_needing_attention(
    db: Session, skip: int = 0, limit: int = 100
) -> list[Trig]:
    """
    Get trigpoints flagged as needing attention.

    Args:
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return

    Returns:
        List of Trig objects with needs_attention != 0
    """
    return (
        db.query(Trig)
        .filter(Trig.needs_attention != 0)
        .order_by(Trig.upd_timestamp.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_trigs_needing_attention(db: Session) -> int:
    """
    Count trigpoints flagged as needing attention.

    Args:
        db: Database session

    Returns:
        Count of trigs with needs_attention != 0
    """
    return db.query(Trig).filter(Trig.needs_attention != 0).count()


def get_needs_attention_summary(db: Session) -> dict:
    """
    Get summary statistics for trigpoints needing attention.

    Args:
        db: Database session

    Returns:
        Dictionary with count and latest upd_timestamp
    """
    count = count_trigs_needing_attention(db)
    latest = (
        db.query(func.max(Trig.upd_timestamp))
        .filter(Trig.needs_attention != 0)
        .scalar()
    )

    return {"count": count, "latest_update": latest}


def update_trig_admin(
    db: Session,
    trig_id: int,
    admin_user_id: int,
    admin_ip_addr: str,
    updates: dict,
) -> Optional[Trig]:
    """
    Update trigpoint with admin audit trail.

    Args:
        db: Database session
        trig_id: Trigpoint ID
        admin_user_id: Admin user ID
        admin_ip_addr: Admin IP address
        updates: Dictionary of field updates

    Returns:
        Updated Trig object or None if not found
    """
    from datetime import datetime

    trig = get_trig_by_id(db, trig_id)
    if not trig:
        return None

    # Apply field updates
    for field, value in updates.items():
        if hasattr(trig, field):
            setattr(trig, field, value)

    # Update admin audit fields
    trig.admin_user_id = admin_user_id  # type: ignore
    trig.admin_timestamp = datetime.utcnow()  # type: ignore
    trig.admin_ip_addr = admin_ip_addr  # type: ignore
    trig.upd_timestamp = datetime.utcnow()  # type: ignore

    db.commit()
    db.refresh(trig)
    return trig
