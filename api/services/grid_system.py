"""
Grid system classification service.

Determines whether a point falls within the GB (OSGB36/EPSG:27700) or
Irish (TM65/EPSG:29903) grid system based on country polygon boundaries.

Country classification uses direct PostGIS ST_Covers queries against the
area table (area_type_id=3 for countries), not materialized views.

Mapping:
- GB grid (EPSG:27700): England (E92000001), Scotland (S92000003), Wales (W92000004)
- Irish grid (EPSG:29903): Northern Ireland (N92000002), Ireland (IE)
"""

from typing import Literal, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.core.logging import get_logger

logger = get_logger(__name__)

# Grid system type
GridSystem = Literal["gb", "ie"]

# Country codes that map to each grid system
# These are the 'code' values from area table where area_type_id=3
GB_COUNTRY_CODES = frozenset(
    {"E92000001", "S92000003", "W92000004"}
)  # England, Scotland, Wales
IE_COUNTRY_CODES = frozenset({"N92000002", "IE"})  # Northern Ireland, Ireland (ROI)

# Country area_type_id (from your database)
COUNTRY_AREA_TYPE_ID = 3


def classify_country_for_point(db: Session, lat: float, lon: float) -> Optional[str]:
    """
    Classify which country a WGS84 point falls within.

    Uses direct PostGIS ST_Covers query against country polygons in the area table.

    Args:
        db: Database session
        lat: WGS84 latitude in decimal degrees
        lon: WGS84 longitude in decimal degrees

    Returns:
        Country code (e.g., 'E92000001', 'IE', 'N92000002') or None if not found
    """
    result = db.execute(
        text(
            """
            SELECT code
            FROM area
            WHERE area_type_id = :area_type_id
              AND ST_Covers(boundary, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            LIMIT 1
        """
        ),
        {"area_type_id": COUNTRY_AREA_TYPE_ID, "lat": lat, "lon": lon},
    ).fetchone()

    if result:
        return result[0]
    return None


def classify_country_name_for_point(
    db: Session, lat: float, lon: float
) -> Optional[str]:
    """
    Get the country name for a WGS84 point.

    Args:
        db: Database session
        lat: WGS84 latitude in decimal degrees
        lon: WGS84 longitude in decimal degrees

    Returns:
        Country name (e.g., 'England', 'Ireland', 'Northern Ireland') or None
    """
    result = db.execute(
        text(
            """
            SELECT name
            FROM area
            WHERE area_type_id = :area_type_id
              AND ST_Covers(boundary, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            LIMIT 1
        """
        ),
        {"area_type_id": COUNTRY_AREA_TYPE_ID, "lat": lat, "lon": lon},
    ).fetchone()

    if result:
        return result[0]
    return None


def grid_system_for_point(db: Session, lat: float, lon: float) -> Optional[GridSystem]:
    """
    Determine the appropriate grid system for a WGS84 point.

    Uses country polygon classification to determine whether the point
    falls within GB (England/Scotland/Wales) or Irish (Northern Ireland/ROI)
    grid coverage.

    Args:
        db: Database session
        lat: WGS84 latitude in decimal degrees
        lon: WGS84 longitude in decimal degrees

    Returns:
        'gb' for British National Grid (EPSG:27700)
        'ie' for Irish Grid (EPSG:29903)
        None if point is not within a known country
    """
    country_code = classify_country_for_point(db, lat, lon)

    if country_code is None:
        return None

    if country_code in GB_COUNTRY_CODES:
        return "gb"
    elif country_code in IE_COUNTRY_CODES:
        return "ie"
    else:
        # Unknown country code - log and return None
        logger.warning(
            f"Unknown country code '{country_code}' for point ({lat}, {lon})"
        )
        return None


def grid_system_for_country_code(country_code: Optional[str]) -> Optional[GridSystem]:
    """
    Determine grid system from a country code.

    Args:
        country_code: Country code from area table (e.g., 'E92000001', 'IE')

    Returns:
        'gb' or 'ie' or None if unknown
    """
    if country_code is None:
        return None

    if country_code in GB_COUNTRY_CODES:
        return "gb"
    elif country_code in IE_COUNTRY_CODES:
        return "ie"
    else:
        return None


def get_country_info_for_point(
    db: Session, lat: float, lon: float
) -> tuple[Optional[GridSystem], Optional[str], Optional[str]]:
    """
    Get complete country/grid information for a WGS84 point.

    Combines grid system classification with country name lookup in a single query.

    Args:
        db: Database session
        lat: WGS84 latitude in decimal degrees
        lon: WGS84 longitude in decimal degrees

    Returns:
        Tuple of (grid_system, country_code, country_name)
        All values may be None if point is not within a known country
    """
    result = db.execute(
        text(
            """
            SELECT code, name
            FROM area
            WHERE area_type_id = :area_type_id
              AND ST_Covers(boundary, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326))
            LIMIT 1
        """
        ),
        {"area_type_id": COUNTRY_AREA_TYPE_ID, "lat": lat, "lon": lon},
    ).fetchone()

    if result is None:
        return None, None, None

    country_code, country_name = result
    grid_system = grid_system_for_country_code(country_code)

    return grid_system, country_code, country_name
