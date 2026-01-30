"""
Experimental endpoints for data visualisation experiments.

These are temporary endpoints for testing new visualisations and may be removed
or changed without notice.
"""

from enum import Enum
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import openapi_lifecycle
from api.models.condition import Condition
from api.models.trig import Trig
from api.models.trigstats import TrigStats

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
