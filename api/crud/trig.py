"""
CRUD operations for trig table.
Updated to use PostGIS spatial functions for distance calculations.
"""

from typing import List, Optional

from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import Float, cast, false, func
from sqlalchemy.orm import Session

from api.models.trig import Trig
from api.models.user import TLog


def _is_sqlite(db: Session) -> bool:
    """Check if the database is SQLite."""
    return db.bind.dialect.name == "sqlite"  # type: ignore[union-attr]


def _get_type_ids_for_codes(db: Session, type_codes: List[str]) -> List[int]:
    """Get type IDs matching the given type codes."""
    from api.models.trig_type import TrigType

    upper_codes = [c.upper() for c in type_codes]
    type_ids = db.query(TrigType.id).filter(TrigType.code.in_(upper_codes)).all()
    return [t[0] for t in type_ids]


def _get_type_ids_for_categories(db: Session, category_codes: List[str]) -> List[int]:
    """Get type IDs for all types in the given categories."""
    from api.models.trig_type import TrigCategory, TrigType

    upper_codes = [c.upper() for c in category_codes]
    type_ids = (
        db.query(TrigType.id)
        .join(TrigCategory)
        .filter(TrigCategory.code.in_(upper_codes))
        .all()
    )
    return [t[0] for t in type_ids]


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
    type_codes: Optional[List[str]] = None,
    category_codes: Optional[List[str]] = None,
    exclude_found_by_user_id: Optional[int] = None,
    only_found_by_user_id: Optional[int] = None,
    exclude_soft_deleted: bool = True,
    area_id: Optional[int] = None,
) -> list[Trig]:
    query = db.query(Trig)

    # Global filter: exclude soft-deleted records (status >= 90) unless explicitly requested
    if exclude_soft_deleted:
        query = query.filter(Trig.status_id < 90)

    # Filter by area using trig_area_mv materialized view
    if area_id is not None and not _is_sqlite(db):
        from sqlalchemy import text

        # Subquery to get trig_ids in the specified area
        area_subquery = text(
            "SELECT trig_id FROM trig_area_mv WHERE area_id = :area_id"
        ).bindparams(area_id=area_id)
        query = query.filter(Trig.id.in_(area_subquery))

    # Filter by type codes
    if type_codes:
        type_id_list = _get_type_ids_for_codes(db, type_codes)
        if type_id_list:
            query = query.filter(Trig.type_id.in_(type_id_list))
        else:
            query = query.filter(false())  # No matching types

    # Filter by category codes (new type system)
    if category_codes:
        type_id_list = _get_type_ids_for_categories(db, category_codes)
        if type_id_list:
            query = query.filter(Trig.type_id.in_(type_id_list))
        else:
            query = query.filter(false())  # No matching categories

    # Exclude trigpoints already found by user (use NOT EXISTS for efficiency)
    if exclude_found_by_user_id is not None:
        # NOT EXISTS is more efficient than NOT IN - it can short-circuit
        exists_subquery = (
            db.query(TLog.id)
            .filter(TLog.trig_id == Trig.id)
            .filter(TLog.user_id == exclude_found_by_user_id)
            .exists()
        )
        query = query.filter(~exists_subquery)

    # Include ONLY trigpoints found by user (use EXISTS for efficiency)
    if only_found_by_user_id is not None:
        exists_subquery = (
            db.query(TLog.id)
            .filter(TLog.trig_id == Trig.id)
            .filter(TLog.user_id == only_found_by_user_id)
            .exists()
        )
        query = query.filter(exists_subquery)

    if name:
        query = query.filter(Trig.name.ilike(f"%{name}%"))
    if county:
        query = query.filter(Trig.county == county)

    if center_lat is not None and center_lon is not None:
        # Use PostGIS for distance calculation (location column is now populated)
        if not _is_sqlite(db):
            # Create a geography point from the center coordinates
            # ST_SetSRID sets the coordinate system (4326 = WGS84)
            # Cast to Geography for spherical distance in meters
            center_geog = cast(
                ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326), Geography
            )

            # ST_Distance returns meters when using geography type
            distance_m = cast(ST_Distance(Trig.location, center_geog), Float).label(
                "distance_m"
            )

            query = query.add_columns(distance_m)

            if max_km is not None:
                # ST_DWithin uses spatial index for efficient bounding
                query = query.filter(
                    ST_DWithin(Trig.location, center_geog, max_km * 1000)
                )

            if order in (None, "", "distance"):
                query = query.order_by(distance_m)
        else:
            # Fallback to haversine for SQLite (no PostGIS)
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
            distance_m = cast(6371000 * c, Float).label("distance_m")

            query = query.add_columns(distance_m)

            if max_km is not None:
                distance_expr = cast(6371000 * c, Float)
                query = query.filter(distance_expr < max_km * 1000)

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
    type_codes: Optional[List[str]] = None,
    category_codes: Optional[List[str]] = None,
    exclude_found_by_user_id: Optional[int] = None,
    only_found_by_user_id: Optional[int] = None,
    exclude_soft_deleted: bool = True,
    area_id: Optional[int] = None,
) -> int:
    query = db.query(func.count(Trig.id))

    # Global filter: exclude soft-deleted records (status >= 90) unless explicitly requested
    if exclude_soft_deleted:
        query = query.filter(Trig.status_id < 90)

    # Filter by area using trig_area_mv materialized view
    if area_id is not None and not _is_sqlite(db):
        from sqlalchemy import text

        # Subquery to get trig_ids in the specified area
        area_subquery = text(
            "SELECT trig_id FROM trig_area_mv WHERE area_id = :area_id"
        ).bindparams(area_id=area_id)
        query = query.filter(Trig.id.in_(area_subquery))

    # Filter by type codes
    if type_codes:
        type_id_list = _get_type_ids_for_codes(db, type_codes)
        if type_id_list:
            query = query.filter(Trig.type_id.in_(type_id_list))
        else:
            query = query.filter(false())  # No matching types

    # Filter by category codes (new type system)
    if category_codes:
        type_id_list = _get_type_ids_for_categories(db, category_codes)
        if type_id_list:
            query = query.filter(Trig.type_id.in_(type_id_list))
        else:
            query = query.filter(false())  # No matching categories

    # Exclude trigpoints already found by user (use NOT EXISTS for efficiency)
    if exclude_found_by_user_id is not None:
        exists_subquery = (
            db.query(TLog.id)
            .filter(TLog.trig_id == Trig.id)
            .filter(TLog.user_id == exclude_found_by_user_id)
            .exists()
        )
        query = query.filter(~exists_subquery)

    # Include ONLY trigpoints found by user (use EXISTS for efficiency)
    if only_found_by_user_id is not None:
        exists_subquery = (
            db.query(TLog.id)
            .filter(TLog.trig_id == Trig.id)
            .filter(TLog.user_id == only_found_by_user_id)
            .exists()
        )
        query = query.filter(exists_subquery)

    if name:
        query = query.filter(Trig.name.ilike(f"%{name}%"))
    if county:
        query = query.filter(Trig.county == county)

    # Apply geo-distance filtering when max_km is specified
    # Note: Unlike list_trigs_filtered which also calculates distance for ordering,
    # count only needs to filter, so we only enter this block when all three params exist
    if center_lat is not None and center_lon is not None and max_km is not None:
        if not _is_sqlite(db):
            # Use PostGIS ST_DWithin for efficient spatial filtering
            center_geog = cast(
                ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326), Geography
            )
            query = query.filter(ST_DWithin(Trig.location, center_geog, max_km * 1000))
        else:
            # Fallback to haversine for SQLite
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
            distance_m = cast(6371000 * c, Float)
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
    Update trigpoint with admin tracking fields.

    Updates the trigpoint record and populates admin tracking fields
    (admin_user_id, admin_timestamp, admin_ip_addr) on the trig table.

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

    # Update admin tracking fields (stored on trig table)
    trig.admin_user_id = admin_user_id  # type: ignore
    trig.admin_timestamp = datetime.utcnow()  # type: ignore
    trig.admin_ip_addr = admin_ip_addr  # type: ignore

    db.commit()
    db.refresh(trig)
    return trig


def get_next_waypoint(db: Session) -> str:
    """
    Generate the next available waypoint code.

    Queries for the maximum numeric portion of existing "TP" prefixed waypoints
    and returns the next sequential value (e.g., "TP12345" -> "TP12346").

    Args:
        db: Database session

    Returns:
        Next available waypoint code (e.g., "TP12346")
    """
    import re

    # Get the maximum waypoint that starts with "TP" followed by digits
    # We need to extract the numeric part and find the max
    max_waypoint = (
        db.query(func.max(Trig.waypoint)).filter(Trig.waypoint.like("TP%")).scalar()
    )

    if max_waypoint:
        # Extract numeric portion after "TP"
        match = re.match(r"TP(\d+)", max_waypoint)
        if match:
            next_num = int(match.group(1)) + 1
            return f"TP{next_num}"

    # Fallback: start from TP100000 if no existing waypoints found
    # This avoids collision with legacy numbering
    return "TP100000"


def create_trig_admin(
    db: Session,
    waypoint: str,
    admin_user_id: int,
    admin_ip_addr: str,
    trig_data: dict,
) -> Trig:
    """
    Create a new trigpoint with admin tracking fields.

    Creates a new trigpoint record and populates creation audit fields
    (crt_user_id, crt_date, crt_time, crt_ip_addr) and admin tracking fields.

    Args:
        db: Database session
        waypoint: Auto-generated waypoint code
        admin_user_id: Admin user ID performing the creation
        admin_ip_addr: Admin IP address
        trig_data: Dictionary of trig field values

    Returns:
        Newly created Trig object
    """
    from datetime import date, datetime, time

    now = datetime.utcnow()

    trig = Trig(
        waypoint=waypoint,
        # Basic fields from trig_data
        name=trig_data["name"],
        fb_number=trig_data.get("fb_number", ""),
        stn_number=trig_data.get("stn_number", ""),
        stn_number_active=trig_data.get("stn_number_active", ""),
        stn_number_passive=trig_data.get("stn_number_passive", ""),
        stn_number_osgb36=trig_data.get("stn_number_osgb36", ""),
        # Classification
        status_id=trig_data["status_id"],
        type_id=trig_data.get("type_id"),
        current_use=trig_data.get("current_use", "none"),
        historic_use=trig_data.get("historic_use", "none"),
        condition=trig_data.get("condition", "G"),
        user_added=0,  # Admin-created trigs are trusted, not user-added
        # Coordinates
        wgs_lat=trig_data["wgs_lat"],
        wgs_long=trig_data["wgs_long"],
        wgs_height=trig_data.get("wgs_height"),
        osgb_eastings=trig_data["osgb_eastings"],
        osgb_northings=trig_data["osgb_northings"],
        osgb_gridref=trig_data.get("osgb_gridref", ""),
        osgb_height=trig_data.get("osgb_height"),
        # Location (deprecated, use defaults)
        county="",
        town="",
        postcode=trig_data.get("postcode"),  # Auto-computed by endpoint
        # PostGIS location (set by endpoint if PostgreSQL)
        location=trig_data.get("location"),
        # Admin/attention fields
        permission_ind="Y",
        needs_attention=0,
        attention_comment=trig_data.get("attention_comment", ""),
        legal_message=trig_data.get("legal_message"),
        # Creation audit fields
        crt_date=date.today(),
        crt_time=time(now.hour, now.minute, now.second),
        crt_user_id=admin_user_id,
        crt_ip_addr=admin_ip_addr,
        # Admin tracking fields
        admin_user_id=admin_user_id,
        admin_timestamp=now,
        admin_ip_addr=admin_ip_addr,
    )

    db.add(trig)
    db.commit()
    db.refresh(trig)
    return trig
