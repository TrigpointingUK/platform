"""
Experimental endpoints for data visualisation experiments.

These are temporary endpoints for testing new visualisations and may be removed
or changed without notice.
"""

from enum import Enum
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.api.deps import get_current_user, get_db
from api.api.lifecycle import openapi_lifecycle
from api.models.condition import Condition
from api.models.trig import Trig
from api.models.trigstats import TrigStats
from api.models.user import TLog, User
from api.schemas.coop import CoopResponse, CoopTrigItem, CoopUser, CoopVisit

router = APIRouter()


class CoordinateDiscrepancySortField(str, Enum):
    """Valid sort fields for coordinate discrepancy endpoint."""

    waypoint = "waypoint"
    name = "name"
    dist_wgs_osgb = "dist_wgs_osgb"
    dist_osgb_osgb = "dist_osgb_osgb"
    dist_wgs_original = "dist_wgs_original"


class MovedFilter(str, Enum):
    """Filter options for 'Moved' condition trigpoints."""

    all = "all"  # Show all trigpoints
    exclude_moved = "exclude_moved"  # Exclude condition='M' (Moved)
    only_moved = "only_moved"  # Only show condition='M' (Moved)


class CoordinateDiscrepancyItem(BaseModel):
    """Single trigpoint with coordinate discrepancy data."""

    trig_id: int
    waypoint: str
    name: str
    condition: str
    condition_name: str
    condition_icon: str
    dist_wgs_osgb: Optional[float] = None
    dist_osgb_osgb: Optional[float] = None
    dist_wgs_original: Optional[float] = (
        None  # Distance between wgs_* and original_wgs_*
    )


class CoordinateDiscrepancyResponse(BaseModel):
    """Paginated response for coordinate discrepancy endpoint."""

    items: List[CoordinateDiscrepancyItem]
    total: int
    page: int
    per_page: int
    total_pages: int


@router.get(
    "/survey-timeline",
    openapi_extra=openapi_lifecycle(
        "alpha",
        note="Temporary endpoint for visualising triangulation and levelling dates. "
        "Returns coordinates, dates, and attr_id (9=triangulation green, 11=levelling blue).",
    ),
)
def get_survey_timeline(
    db: Session = Depends(get_db),
):
    """
    Get survey timeline data showing when trigpoints were triangulated and levelled.

    Returns an array of {lat, lon, date, colour} tuples sorted by date ascending.
    - attr_id=9 (triangulation date) → green dots
    - attr_id=11 (levelling date) → red dots

    Dates are from Ordnance Survey data and are in DD/MM/YYYY format in the database,
    converted to YYYY-MM-DD for the response.
    """
    from datetime import date, datetime

    from sqlalchemy import text

    today = date.today().isoformat()

    # Query based on the user's SQL
    query = text("""
        SELECT t.wgs_lat, t.wgs_long, v.value_string as date_str, v.attr_id
        FROM trig t
        INNER JOIN attrset s ON s.trig_id = t.id
        INNER JOIN attrset_attrval sv ON s.id = sv.attrset_id
        INNER JOIN attrval v ON v.id = sv.attrval_id
        WHERE s.attrsource_id = 2
        AND v.attr_id IN (9, 11)
        AND t.wgs_lat IS NOT NULL
        AND t.wgs_long IS NOT NULL
        AND v.value_string IS NOT NULL
        AND v.value_string != ''
    """)

    results = db.execute(query).fetchall()

    # Parse and sort results
    timeline = []
    for row in results:
        lat = float(row.wgs_lat)
        lon = float(row.wgs_long)
        date_str = row.date_str
        attr_id = int(row.attr_id)

        # Parse DD/MM/YYYY to YYYY-MM-DD
        parsed_date = None
        if date_str:
            try:
                # Handle DD/MM/YYYY format
                parsed = datetime.strptime(date_str.strip(), "%d/%m/%Y")
                parsed_date = parsed.strftime("%Y-%m-%d")
            except ValueError:
                # Try other formats or skip invalid dates
                try:
                    # Try YYYY-MM-DD format
                    parsed = datetime.strptime(date_str.strip(), "%Y-%m-%d")
                    parsed_date = date_str.strip()
                except ValueError:
                    # Skip rows with unparseable dates
                    continue

        if parsed_date is None:
            continue

        # Skip future dates
        if parsed_date > today:
            continue

        # attr_id 9 = triangulation (green), attr_id 11 = levelling (blue)
        colour = "green" if attr_id == 9 else "blue"

        timeline.append(
            {
                "lat": lat,
                "lon": lon,
                "date": parsed_date,
                "colour": colour,
            }
        )

    # Sort by date ascending
    timeline.sort(key=lambda x: str(x["date"]))

    return timeline


@router.get(
    "/coordinate-discrepancies",
    response_model=CoordinateDiscrepancyResponse,
    openapi_extra=openapi_lifecycle(
        "alpha",
        note="Temporary endpoint for monitoring coordinate discrepancies between "
        "WGS84/OSGB and attrval coordinates. Used for data cleansing.",
    ),
)
def get_coordinate_discrepancies(
    db: Session = Depends(get_db),
    page: int = Query(1, ge=1, description="Page number (1-based)"),
    per_page: int = Query(50, ge=1, le=200, description="Items per page"),
    sort_by: CoordinateDiscrepancySortField = Query(
        CoordinateDiscrepancySortField.dist_wgs_osgb,
        description="Field to sort by",
    ),
    sort_order: Literal["asc", "desc"] = Query(
        "desc", description="Sort order (asc or desc)"
    ),
    min_dist_wgs_osgb: Optional[float] = Query(
        None, description="Minimum dist_wgs_osgb threshold (metres)"
    ),
    min_dist_osgb_osgb: Optional[float] = Query(
        None, description="Minimum dist_osgb_osgb threshold (metres)"
    ),
    exclude_irish: bool = Query(
        False, description="Exclude Irish trigpoints (grid refs starting with I/J)"
    ),
    moved_filter: MovedFilter = Query(
        MovedFilter.all, description="Filter for 'Moved' condition trigpoints"
    ),
):
    """
    Get paginated list of trigpoints with coordinate discrepancy data.

    Returns trigpoints sorted by discrepancy distance, allowing identification
    of records that need coordinate data cleansing.

    Columns:
    - waypoint: Unique identifier (e.g., TP1234)
    - name: Trigpoint name
    - condition: Current condition code
    - condition_icon: Icon filename for condition
    - dist_wgs_osgb: Distance (m) between WGS84->OSTN15 and stored OSGB coords
    - dist_osgb_osgb: Distance (m) between trig.osgb* and attrval OSGB coords
    - dist_wgs_original: Distance (m) between current WGS84 and original WGS84 coords
    """
    from geoalchemy2.functions import ST_Distance

    # Calculate distance between current and original WGS coordinates using PostGIS
    dist_wgs_original = ST_Distance(Trig.location, Trig.original_location).label(
        "dist_wgs_original"
    )

    # Build query joining trig, trigstats, and condition
    query = (
        db.query(
            Trig.id,
            Trig.waypoint,
            Trig.name,
            Trig.condition,
            Condition.name,
            Condition.icon_file,
            TrigStats.dist_wgs_osgb,
            TrigStats.dist_osgb_osgb,
            dist_wgs_original,
        )
        .outerjoin(TrigStats, Trig.id == TrigStats.id)
        .outerjoin(Condition, Trig.condition == Condition.code)
    )

    # Filter out Irish trigpoints if requested
    # Irish Grid uses single letter prefix (e.g., "O 12345"), GB uses two letters (e.g., "TQ 12345")
    if exclude_irish:
        query = query.filter(~Trig.osgb_gridref.like("_ %"))

    # Apply moved filter
    if moved_filter == MovedFilter.exclude_moved:
        query = query.filter(Trig.condition != "M")
    elif moved_filter == MovedFilter.only_moved:
        query = query.filter(Trig.condition == "M")

    # Apply threshold filters if specified
    if min_dist_wgs_osgb is not None:
        query = query.filter(TrigStats.dist_wgs_osgb >= min_dist_wgs_osgb)
    if min_dist_osgb_osgb is not None:
        query = query.filter(TrigStats.dist_osgb_osgb >= min_dist_osgb_osgb)

    # Get total count (before pagination)
    total = query.count()

    # Apply sorting
    sort_column_map = {
        CoordinateDiscrepancySortField.waypoint: Trig.waypoint,
        CoordinateDiscrepancySortField.name: Trig.name,
        CoordinateDiscrepancySortField.dist_wgs_osgb: TrigStats.dist_wgs_osgb,
        CoordinateDiscrepancySortField.dist_osgb_osgb: TrigStats.dist_osgb_osgb,
        CoordinateDiscrepancySortField.dist_wgs_original: dist_wgs_original,
    }
    sort_column = sort_column_map[sort_by]

    if sort_order == "desc":
        # Put NULLs last when sorting descending
        query = query.order_by(sort_column.desc().nullslast())
    else:
        # Put NULLs last when sorting ascending
        query = query.order_by(sort_column.asc().nullslast())

    # Apply pagination
    offset = (page - 1) * per_page
    results = query.offset(offset).limit(per_page).all()

    # Build response items
    items = []
    for row in results:
        items.append(
            CoordinateDiscrepancyItem(
                trig_id=row[0],
                waypoint=row[1] or "",
                name=row[2] or "",
                condition=row[3] or "",
                condition_name=row[4] or "Unknown",
                condition_icon=row[5] or "c_unknown.png",
                dist_wgs_osgb=float(row[6]) if row[6] is not None else None,
                dist_osgb_osgb=float(row[7]) if row[7] is not None else None,
                dist_wgs_original=float(row[8]) if row[8] is not None else None,
            )
        )

    # Calculate total pages
    total_pages = (total + per_page - 1) // per_page if total > 0 else 1

    return CoordinateDiscrepancyResponse(
        items=items,
        total=total,
        page=page,
        per_page=per_page,
        total_pages=total_pages,
    )


class CoopFilterMode(str, Enum):
    """Filter modes for the co-op endpoint."""

    all = "all"
    unvisited_by_all = "unvisited_by_all"
    visited_by_any = "visited_by_any"
    unvisited_by_me = "unvisited_by_me"
    visited_by_me = "visited_by_me"
    only_visited_by_me = "only_visited_by_me"
    visited_by_all = "visited_by_all"
    visited_by_all_except_me = "visited_by_all_except_me"
    visited_by_most = "visited_by_most"
    not_visited_by_most = "not_visited_by_most"


@router.get(
    "/coop",
    response_model=CoopResponse,
    openapi_extra=openapi_lifecycle(
        "alpha",
        note="Co-op trigpointing: compare visits across selected members. "
        "Returns trigs sorted by distance with per-user visit matrix.",
    ),
)
def get_coop_data(
    user_ids: str = Query(..., description="Comma-separated user IDs to compare"),
    lat: Optional[float] = Query(None, description="Centre latitude"),
    lon: Optional[float] = Query(None, description="Centre longitude"),
    max_km: Optional[float] = Query(None, description="Maximum radius in km"),
    categories: Optional[str] = Query(
        None, description="Comma-separated category codes"
    ),
    types: Optional[str] = Query(None, description="Comma-separated type codes"),
    filter_mode: CoopFilterMode = Query(
        CoopFilterMode.all, description="Filter mode for visit status"
    ),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Co-op trigpointing comparison grid.

    Returns trigpoints sorted by distance from a centre point, with a per-user
    visit matrix showing which of the selected users has logged each trig and
    with what condition.

    filter_mode controls which trigs are included:
    - all: all trigs matching the location/type filters
    - unvisited_by_all: only trigs not visited by any of the selected users
    - unvisited_by_me: only trigs not visited by the authenticated user
    - visited_by_all: only trigs visited by every selected user
    """
    from api.crud import trig as trig_crud

    # Parse user IDs
    parsed_user_ids = []
    for uid in user_ids.split(","):
        uid = uid.strip()
        if uid:
            try:
                parsed_user_ids.append(int(uid))
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid user ID: {uid}")

    if not parsed_user_ids:
        raise HTTPException(status_code=400, detail="At least one user ID required")

    if len(parsed_user_ids) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 users allowed")

    # Ensure current user is included
    current_user_id = int(current_user.id)
    if current_user_id not in parsed_user_ids:
        parsed_user_ids.insert(0, current_user_id)

    # Validate that all user IDs exist and fetch names
    users_db = db.query(User.id, User.name).filter(User.id.in_(parsed_user_ids)).all()
    users_map = {int(u.id): u.name for u in users_db}

    missing_ids = [uid for uid in parsed_user_ids if uid not in users_map]
    if missing_ids:
        raise HTTPException(
            status_code=404,
            detail=f"User(s) not found: {', '.join(str(i) for i in missing_ids)}",
        )

    # Parse filter params
    type_codes_list = None
    if types:
        type_codes_list = [t.strip() for t in types.split(",") if t.strip()]

    category_codes_list = None
    if categories:
        category_codes_list = [c.strip() for c in categories.split(",") if c.strip()]

    # Determine exclude/include found based on filter_mode
    exclude_found_by_user_id = None
    only_found_by_user_id = None
    if filter_mode == CoopFilterMode.unvisited_by_me:
        exclude_found_by_user_id = current_user_id
    elif filter_mode == CoopFilterMode.visited_by_me:
        only_found_by_user_id = current_user_id

    # Build the trig query - reuse the existing filtered query infrastructure
    items_with_distance = trig_crud.list_trigs_filtered_with_distance(
        db,
        skip=skip,
        limit=limit,
        center_lat=lat,
        center_lon=lon,
        max_km=max_km,
        order="distance" if lat and lon else "name",
        type_codes=type_codes_list,
        category_codes=category_codes_list,
        exclude_found_by_user_id=exclude_found_by_user_id,
        only_found_by_user_id=only_found_by_user_id,
        exclude_soft_deleted=True,
    )

    items = [trig for trig, _ in items_with_distance]
    distances_m = {trig.id: dist_m for trig, dist_m in items_with_distance}

    # For unvisited_by_all, we need to exclude trigs visited by ANY of the
    # selected users. For visited_by_all, we keep only trigs visited by EVERY
    # selected user. Both require post-filtering.
    post_filter_user_ids = None
    if filter_mode == CoopFilterMode.unvisited_by_all:
        post_filter_user_ids = parsed_user_ids
    elif filter_mode == CoopFilterMode.visited_by_any:
        post_filter_user_ids = parsed_user_ids
    elif filter_mode == CoopFilterMode.visited_by_all:
        post_filter_user_ids = parsed_user_ids
    elif filter_mode in (
        CoopFilterMode.visited_by_most,
        CoopFilterMode.not_visited_by_most,
        CoopFilterMode.only_visited_by_me,
        CoopFilterMode.visited_by_all_except_me,
    ):
        post_filter_user_ids = parsed_user_ids

    if post_filter_user_ids:
        # Get visit counts per trig for the selected users
        from sqlalchemy import func as sa_func

        visit_data = (
            db.query(TLog.trig_id, sa_func.count(sa_func.distinct(TLog.user_id)))
            .filter(
                TLog.user_id.in_(post_filter_user_ids),
                TLog.status == "P",
            )
            .group_by(TLog.trig_id)
            .all()
        )

        if filter_mode == CoopFilterMode.unvisited_by_all:
            visited_trig_ids = {int(row[0]) for row in visit_data}

            def keep_fn(trig_id: int) -> bool:
                return trig_id not in visited_trig_ids

        elif filter_mode == CoopFilterMode.visited_by_any:
            visited_trig_ids = {int(row[0]) for row in visit_data}

            def keep_fn(trig_id: int) -> bool:
                return trig_id in visited_trig_ids

        elif filter_mode == CoopFilterMode.visited_by_all:
            num_users = len(post_filter_user_ids)
            all_visited_trig_ids = {
                int(row[0]) for row in visit_data if row[1] >= num_users
            }

            def keep_fn(trig_id: int) -> bool:
                return trig_id in all_visited_trig_ids

        elif filter_mode == CoopFilterMode.visited_by_most:
            num_users = len(post_filter_user_ids)
            visit_counts = {int(row[0]): int(row[1]) for row in visit_data}

            def keep_fn(trig_id: int) -> bool:
                return visit_counts.get(trig_id, 0) * 2 >= num_users

        elif filter_mode == CoopFilterMode.not_visited_by_most:
            num_users = len(post_filter_user_ids)
            visit_counts = {int(row[0]): int(row[1]) for row in visit_data}

            def keep_fn(trig_id: int) -> bool:
                return visit_counts.get(trig_id, 0) * 2 < num_users

        elif filter_mode == CoopFilterMode.only_visited_by_me:
            visit_counts = {int(row[0]): int(row[1]) for row in visit_data}
            my_visit_trig_ids = {
                int(row[0])
                for row in db.query(TLog.trig_id)
                .filter(
                    TLog.user_id == current_user_id,
                    TLog.status == "P",
                )
                .distinct()
                .all()
            }

            def keep_fn(trig_id: int) -> bool:
                return (
                    trig_id in my_visit_trig_ids and visit_counts.get(trig_id, 0) == 1
                )

        else:
            # visited_by_all_except_me: every other user visited but I haven't
            num_users = len(post_filter_user_ids)
            visit_counts = {int(row[0]): int(row[1]) for row in visit_data}
            my_visit_trig_ids = {
                int(row[0])
                for row in db.query(TLog.trig_id)
                .filter(
                    TLog.user_id == current_user_id,
                    TLog.status == "P",
                )
                .distinct()
                .all()
            }

            def keep_fn(trig_id: int) -> bool:
                return (
                    trig_id not in my_visit_trig_ids
                    and visit_counts.get(trig_id, 0) >= num_users - 1
                )

        # Re-query without user-specific filters and apply our own
        items_with_distance = trig_crud.list_trigs_filtered_with_distance(
            db,
            skip=0,
            limit=limit + skip + 500,  # over-fetch to compensate for filtering
            center_lat=lat,
            center_lon=lon,
            max_km=max_km,
            order="distance" if lat and lon else "name",
            type_codes=type_codes_list,
            category_codes=category_codes_list,
            exclude_soft_deleted=True,
        )

        filtered = [
            (trig, dist) for trig, dist in items_with_distance if keep_fn(int(trig.id))
        ]

        total = len(filtered)
        page_items = filtered[skip : skip + limit]
        items = [trig for trig, _ in page_items]
        distances_m = {trig.id: dist_m for trig, dist_m in page_items}
    else:
        total = trig_crud.count_trigs_filtered(
            db,
            center_lat=lat,
            center_lon=lon,
            max_km=max_km,
            type_codes=type_codes_list,
            category_codes=category_codes_list,
            exclude_found_by_user_id=exclude_found_by_user_id,
            only_found_by_user_id=only_found_by_user_id,
            exclude_soft_deleted=True,
        )

    if not items:
        return CoopResponse(
            users=[CoopUser(id=uid, name=users_map[uid]) for uid in parsed_user_ids],
            items=[],
            total=total,
            skip=skip,
            limit=limit,
            has_more=False,
        )

    # Batch-fetch visit data for all selected users x returned trigs
    trig_ids = [int(t.id) for t in items]
    visit_rows = (
        db.query(TLog.id, TLog.trig_id, TLog.user_id, TLog.condition, TLog.date)
        .filter(
            TLog.user_id.in_(parsed_user_ids),
            TLog.trig_id.in_(trig_ids),
            TLog.status == "P",
        )
        .all()
    )

    # Build visits lookup: trig_id -> user_id -> CoopVisit
    # When a user has multiple logs for the same trig, keep the most recent
    visits_lookup: dict[int, dict[int, CoopVisit]] = {}
    for row in visit_rows:
        tid = int(row.trig_id)
        visit_uid = int(row.user_id)
        visit = CoopVisit(
            log_id=int(row.id),
            condition=str(row.condition or "U"),
            date=row.date,
        )
        if tid not in visits_lookup:
            visits_lookup[tid] = {}
        existing = visits_lookup[tid].get(visit_uid)
        if existing is None or (
            visit.date and (not existing.date or visit.date > existing.date)
        ):
            visits_lookup[tid][visit_uid] = visit

    # Build response items
    response_items = []
    for trig in items:
        trig_visits = visits_lookup.get(int(trig.id), {})
        visits_dict: dict[str, Optional[CoopVisit]] = {}
        for member_id in parsed_user_ids:
            visits_dict[str(member_id)] = trig_visits.get(member_id)

        dist_m = distances_m.get(trig.id)
        distance_km = round(dist_m / 1000, 1) if dist_m is not None else None

        item = CoopTrigItem(
            id=int(trig.id),
            waypoint=str(trig.waypoint or ""),
            name=str(trig.name or ""),
            condition=str(trig.condition or "U"),
            type_code=str(trig.trig_type.code) if trig.trig_type else None,
            type_name=str(trig.trig_type.name) if trig.trig_type else None,
            category_code=(
                str(trig.trig_type.category.code)
                if trig.trig_type and trig.trig_type.category
                else None
            ),
            category_name=(
                str(trig.trig_type.category.name)
                if trig.trig_type and trig.trig_type.category
                else None
            ),
            wgs_lat=trig.wgs_lat,
            wgs_long=trig.wgs_long,
            osgb_gridref=str(trig.osgb_gridref or ""),
            distance_km=distance_km,
            visits=visits_dict,
        )
        response_items.append(item)

    has_more = (skip + len(items)) < total

    return CoopResponse(
        users=[CoopUser(id=uid, name=users_map[uid]) for uid in parsed_user_ids],
        items=response_items,
        total=total,
        skip=skip,
        limit=limit,
        has_more=has_more,
    )
