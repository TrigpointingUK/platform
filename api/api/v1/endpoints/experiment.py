"""
Experimental endpoints for data visualisation experiments.

These are temporary endpoints for testing new visualisations and may be removed
or changed without notice.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.api.deps import get_db
from api.api.lifecycle import openapi_lifecycle

router = APIRouter()


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
