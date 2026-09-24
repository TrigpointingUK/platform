"""
CRUD operations for trig table.
Updated to use PostGIS spatial functions for distance calculations.
"""

from datetime import date, time
from typing import List, Optional

from geoalchemy2 import Geography
from geoalchemy2.functions import ST_Distance, ST_DWithin, ST_MakePoint, ST_SetSRID
from sqlalchemy import Float, bindparam, cast, false, func, select, text, true
from sqlalchemy.orm import Session

from api.crud.area import COUNTY_1991_AREA_TYPE_ID, TRIG_AREA
from api.models.area import Area
from api.models.trig import Trig
from api.models.user import TLog

# Import update_trigstats_distances lazily to avoid circular imports
_trigstats_crud = None


def _get_trigstats_crud():
    """Lazy import of trigstats CRUD module to avoid circular dependencies."""
    global _trigstats_crud
    if _trigstats_crud is None:
        from api.crud import trigstats as ts_crud

        _trigstats_crud = ts_crud
    return _trigstats_crud


def _is_sqlite(db: Session) -> bool:
    """Check if the database is SQLite."""
    return db.bind.dialect.name == "sqlite"  # type: ignore[union-attr]


def _trig_area_table_exists(db: Session) -> bool:
    """Check if the trig_area table exists in the database."""
    if _is_sqlite(db):
        return False
    try:
        from typing import Any, cast

        from sqlalchemy import inspect

        inspector = cast(Any, inspect(db.bind))
        return "trig_area" in inspector.get_table_names()
    except Exception:
        return False


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


def _center_geography(center_lat: float, center_lon: float):
    """A WGS84 point cast to geography, so ST_Distance/ST_DWithin work in metres."""
    return cast(ST_SetSRID(ST_MakePoint(center_lon, center_lat), 4326), Geography)


def _haversine_distance_m(center_lat: float, center_lon: float):
    """Great-circle distance in metres (SQLite fallback - no PostGIS)."""
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
    return cast(6371000 * c, Float)


def _logged_by_user(user_id: int):
    """EXISTS clause: the user has at least one published (non-draft) log of the trig."""
    return (
        select(TLog.id)
        .where(TLog.trig_id == Trig.id)
        .where(TLog.user_id == user_id)
        .where(TLog.status == "P")
        .exists()
    )


def first_log_lateral(user_id: int):
    """
    LATERAL subquery giving, for each outer trig row, the user's earliest
    published log of it (date, time, log_id) - or nothing if they haven't.

    "Earliest" is by log date, then time, then log id - the id breaks ties
    between same-day logs without a time, so the ordering is deterministic
    (important when answering "which was my 1000th pillar?").

    A per-trig index lookup (tlog has (trig_id, user_id, ...) indexes) rather
    than a window over all the user's logs: the planner can't misjudge it
    into a pathological join, and it costs the same for a user with 20 logs
    or 20,000.
    """
    return (
        select(TLog.date, TLog.time, TLog.id.label("log_id"))
        .where(
            TLog.trig_id == Trig.id,
            TLog.user_id == user_id,
            TLog.status == "P",
        )
        .order_by(
            TLog.date.asc().nulls_last(),
            TLog.time.asc().nulls_last(),
            TLog.id.asc(),
        )
        .limit(1)
        .lateral("first_log")
    )


def get_first_logs(
    db: Session, user_id: int, trig_ids: List[int]
) -> dict[int, tuple[Optional[date], Optional[time]]]:
    """Map trig_id -> (date, time) of the user's first published log of it."""
    if not trig_ids:
        return {}
    first_log = first_log_lateral(user_id)
    rows = db.execute(
        select(Trig.id, first_log.c.date, first_log.c.time)
        .select_from(Trig)
        .join(first_log, true())
        .where(Trig.id.in_(trig_ids))
    ).all()
    return {int(row.id): (row.date, row.time) for row in rows}


def _apply_trig_filters(
    query,
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
    area_ids: Optional[List[int]] = None,
    historic_use: Optional[List[str]] = None,
    current_use: Optional[List[str]] = None,
    conditions: Optional[List[str]] = None,
    logged_conditions: Optional[List[str]] = None,
):
    """Apply the shared trig filter set (used by list, count and points queries)."""
    # Global filter: exclude soft-deleted records (status >= 90) unless explicitly requested
    if exclude_soft_deleted:
        query = query.filter(Trig.status_id < 90)

    # Filter by area using trig_area table (single area_id - legacy support)
    if area_id is not None and not _is_sqlite(db):
        area_subquery = text(
            "SELECT trig_id FROM trig_area WHERE area_id = :area_id"
        ).bindparams(area_id=area_id)
        query = query.filter(Trig.id.in_(area_subquery))

    # Filter by multiple areas (area_ids - multi-select support)
    if area_ids and not _is_sqlite(db):
        area_ids_subquery = text(
            "SELECT trig_id FROM trig_area WHERE area_id = ANY(:area_ids)"
        ).bindparams(bindparam("area_ids", value=area_ids))
        query = query.filter(Trig.id.in_(area_ids_subquery))

    if historic_use:
        query = query.filter(Trig.historic_use.in_(historic_use))

    if current_use:
        query = query.filter(Trig.current_use.in_(current_use))

    if conditions:
        query = query.filter(Trig.condition.in_(conditions))

    if type_codes:
        type_id_list = _get_type_ids_for_codes(db, type_codes)
        if type_id_list:
            query = query.filter(Trig.type_id.in_(type_id_list))
        else:
            query = query.filter(false())  # No matching types

    if category_codes:
        type_id_list = _get_type_ids_for_categories(db, category_codes)
        if type_id_list:
            query = query.filter(Trig.type_id.in_(type_id_list))
        else:
            query = query.filter(false())  # No matching categories

    # Logged / not-logged filters. Draft logs don't count as a find.
    if exclude_found_by_user_id is not None:
        query = query.filter(~_logged_by_user(exclude_found_by_user_id))

    if only_found_by_user_id is not None:
        query = query.filter(_logged_by_user(only_found_by_user_id))

    # Show trigs where the user logged with specific conditions
    if logged_conditions and only_found_by_user_id is not None:
        logged_cond_subquery = (
            select(TLog.trig_id)
            .where(TLog.user_id == only_found_by_user_id)
            .where(TLog.status == "P")
            .where(TLog.condition.in_(logged_conditions))
            .distinct()
        )
        query = query.filter(Trig.id.in_(logged_cond_subquery))

    if name:
        query = query.filter(Trig.name.ilike(f"%{name}%"))
    if county and _trig_area_table_exists(db):
        # Filter by county using trig_area join (area_type_id=7 = county_1991)
        county_subquery = (
            select(TRIG_AREA.c.trig_id)
            .join(Area, Area.id == TRIG_AREA.c.area_id)
            .where(
                TRIG_AREA.c.area_type_id == COUNTY_1991_AREA_TYPE_ID,
                Area.name == county,
            )
        )
        query = query.filter(Trig.id.in_(county_subquery))

    if center_lat is not None and center_lon is not None and max_km is not None:
        if not _is_sqlite(db):
            # ST_DWithin uses the spatial index for efficient bounding
            query = query.filter(
                ST_DWithin(
                    Trig.location,
                    _center_geography(center_lat, center_lon),
                    max_km * 1000,
                )
            )
        else:
            query = query.filter(
                _haversine_distance_m(center_lat, center_lon) < max_km * 1000
            )

    return query


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
    area_ids: Optional[List[int]] = None,
    historic_use: Optional[List[str]] = None,
    current_use: Optional[List[str]] = None,
    conditions: Optional[List[str]] = None,
    logged_conditions: Optional[List[str]] = None,
    log_user_id: Optional[int] = None,
) -> list[Trig]:
    """
    List trigs with filters. Returns just Trig objects.

    For distance information, use list_trigs_filtered_with_distance() instead.
    """
    results = list_trigs_filtered_with_distance(
        db,
        name=name,
        county=county,
        skip=skip,
        limit=limit,
        center_lat=center_lat,
        center_lon=center_lon,
        max_km=max_km,
        order=order,
        type_codes=type_codes,
        category_codes=category_codes,
        exclude_found_by_user_id=exclude_found_by_user_id,
        only_found_by_user_id=only_found_by_user_id,
        exclude_soft_deleted=exclude_soft_deleted,
        area_id=area_id,
        area_ids=area_ids,
        historic_use=historic_use,
        current_use=current_use,
        conditions=conditions,
        logged_conditions=logged_conditions,
        log_user_id=log_user_id,
    )
    return [trig for trig, _ in results]


def list_trigs_filtered_with_distance(
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
    area_ids: Optional[List[int]] = None,
    historic_use: Optional[List[str]] = None,
    current_use: Optional[List[str]] = None,
    conditions: Optional[List[str]] = None,
    logged_conditions: Optional[List[str]] = None,
    log_user_id: Optional[int] = None,
) -> list[tuple[Trig, Optional[float]]]:
    """
    List trigs with filters, returning (Trig, distance_m) tuples.

    Orders: distance | name | height | score | logged | id, prefixed with "-"
    to reverse. "logged" sorts by log_user_id's first published log of each
    trig (trigs they haven't logged go last) and is ignored without a
    log_user_id. Every order ends with trig id so pagination is stable.
    """
    query = _apply_trig_filters(
        db.query(Trig),
        db,
        name=name,
        county=county,
        center_lat=center_lat,
        center_lon=center_lon,
        max_km=max_km,
        type_codes=type_codes,
        category_codes=category_codes,
        exclude_found_by_user_id=exclude_found_by_user_id,
        only_found_by_user_id=only_found_by_user_id,
        exclude_soft_deleted=exclude_soft_deleted,
        area_id=area_id,
        area_ids=area_ids,
        historic_use=historic_use,
        current_use=current_use,
        conditions=conditions,
        logged_conditions=logged_conditions,
    )

    has_centre = center_lat is not None and center_lon is not None
    distance_m = None
    if center_lat is not None and center_lon is not None:
        if not _is_sqlite(db):
            # ST_Distance returns metres when using the geography type
            distance_expr = cast(
                ST_Distance(Trig.location, _center_geography(center_lat, center_lon)),
                Float,
            )
        else:
            distance_expr = _haversine_distance_m(center_lat, center_lon)
        distance_m = distance_expr.label("distance_m")
        query = query.add_columns(distance_m)

    key = order or ("distance" if has_centre else "id")
    descending = key.startswith("-")
    key = key.lstrip("-")

    if key == "distance" and distance_m is not None:
        query = query.order_by(distance_m.desc() if descending else distance_m)
    elif key == "name":
        query = query.order_by(Trig.name.desc() if descending else Trig.name.asc())
    elif key == "height":
        # "height" means highest first; "-height" lowest first
        query = query.order_by(
            Trig.wgs_height.asc().nulls_last()
            if descending
            else Trig.wgs_height.desc().nulls_last()
        )
    elif key == "score":
        # "score" means best first; "-score" worst first
        from api.models.trigstats import TrigStats

        query = query.outerjoin(TrigStats, TrigStats.id == Trig.id)
        query = query.order_by(
            TrigStats.score_baysian.asc().nulls_last()
            if descending
            else TrigStats.score_baysian.desc().nulls_last()
        )
    elif key == "logged" and log_user_id is not None:
        first_log = first_log_lateral(log_user_id)
        query = query.outerjoin(first_log, true())
        if descending:
            query = query.order_by(
                first_log.c.date.desc().nulls_last(),
                first_log.c.time.desc().nulls_last(),
                first_log.c.log_id.desc().nulls_last(),
            )
        else:
            query = query.order_by(
                first_log.c.date.asc().nulls_last(),
                first_log.c.time.asc().nulls_last(),
                first_log.c.log_id.asc().nulls_last(),
            )

    # Final tie-break keeps OFFSET pagination stable (no duplicates or gaps
    # between pages when many rows share a name, height or null score)
    query = query.order_by(
        Trig.id.desc() if key == "id" and descending else Trig.id.asc()
    )

    results = query.offset(skip).limit(limit).all()
    if has_centre:
        return [(row[0], row[1]) for row in results]
    return [(trig, None) for trig in results]


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
    area_ids: Optional[List[int]] = None,
    historic_use: Optional[List[str]] = None,
    current_use: Optional[List[str]] = None,
    conditions: Optional[List[str]] = None,
    logged_conditions: Optional[List[str]] = None,
) -> int:
    query = _apply_trig_filters(
        db.query(func.count(Trig.id)),
        db,
        name=name,
        county=county,
        center_lat=center_lat,
        center_lon=center_lon,
        max_km=max_km,
        type_codes=type_codes,
        category_codes=category_codes,
        exclude_found_by_user_id=exclude_found_by_user_id,
        only_found_by_user_id=only_found_by_user_id,
        exclude_soft_deleted=exclude_soft_deleted,
        area_id=area_id,
        area_ids=area_ids,
        historic_use=historic_use,
        current_use=current_use,
        conditions=conditions,
        logged_conditions=logged_conditions,
    )
    return int(query.scalar() or 0)


def list_trig_points(
    db: Session,
    *,
    limit: int = 50000,
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
    area_ids: Optional[List[int]] = None,
    historic_use: Optional[List[str]] = None,
    current_use: Optional[List[str]] = None,
    conditions: Optional[List[str]] = None,
    logged_conditions: Optional[List[str]] = None,
) -> list:
    """
    Lightweight rows (no full ORM objects) for every trig matching the filters.

    Intended for plotting a whole filtered set on a map in one request.
    """
    from api.models.trig_type import TrigCategory, TrigType

    query = (
        db.query(
            Trig.id,
            Trig.waypoint,
            Trig.name,
            Trig.wgs_lat,
            Trig.wgs_long,
            Trig.condition,
            Trig.osgb_gridref,
            TrigType.name.label("type_name"),
            TrigCategory.code.label("category_code"),
        )
        .select_from(Trig)
        .outerjoin(TrigType, TrigType.id == Trig.type_id)
        .outerjoin(TrigCategory, TrigCategory.id == TrigType.category_id)
    )
    query = _apply_trig_filters(
        query,
        db,
        name=name,
        county=county,
        center_lat=center_lat,
        center_lon=center_lon,
        max_km=max_km,
        type_codes=type_codes,
        category_codes=category_codes,
        exclude_found_by_user_id=exclude_found_by_user_id,
        only_found_by_user_id=only_found_by_user_id,
        exclude_soft_deleted=exclude_soft_deleted,
        area_id=area_id,
        area_ids=area_ids,
        historic_use=historic_use,
        current_use=current_use,
        conditions=conditions,
        logged_conditions=logged_conditions,
    )
    return query.order_by(Trig.id.asc()).limit(limit).all()


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
    from datetime import UTC, datetime

    trig = get_trig_by_id(db, trig_id)
    if not trig:
        return None

    # Apply field updates
    for field, value in updates.items():
        if hasattr(trig, field):
            setattr(trig, field, value)

    # Update admin tracking fields (stored on trig table)
    trig.admin_user_id = admin_user_id  # type: ignore
    trig.admin_timestamp = datetime.now(UTC)  # type: ignore
    trig.admin_ip_addr = admin_ip_addr  # type: ignore

    db.commit()
    db.refresh(trig)

    # Update trigstats distance columns (coordinates may have changed)
    _get_trigstats_crud().update_trigstats_distances(db, trig_id)

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
    from datetime import UTC, date, datetime, time

    now = datetime.now(UTC)

    trig = Trig(
        waypoint="TEMP",  # Will be set from ID after flush
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
        # county is now derived from trig_area table
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
    db.flush()  # Get the assigned ID

    # Waypoint is always TP + ID (padded to minimum 4 digits)
    trig.waypoint = f"TP{trig.id:04d}"  # type: ignore[assignment]

    db.commit()
    db.refresh(trig)

    # Create trigstats row with coordinate distances
    _get_trigstats_crud().update_trigstats_distances(db, int(trig.id))

    return trig
