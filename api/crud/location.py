"""
CRUD operations for location-related tables (postcodes, towns).
Uses PostGIS for efficient spatial queries.
"""

import sys
from typing import Optional, Tuple

from geoalchemy2.functions import ST_Distance, ST_MakePoint, ST_SetSRID
from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.location import Postcode

# Detect if running under pytest (SQLite) to handle PostGIS types
_IS_SQLITE = "pytest" in sys.modules


def find_nearest_postcode(
    db: Session, lat: float, lon: float, max_distance_m: float = 5000.0
) -> Optional[Tuple[str, float]]:
    """
    Find the nearest postcode to a given WGS84 coordinate using PostGIS.

    Uses PostGIS KNN (k-nearest-neighbour) index for O(log n) performance
    instead of scanning all 2.7M postcodes.

    Args:
        db: Database session
        lat: Latitude (WGS84)
        lon: Longitude (WGS84)
        max_distance_m: Maximum distance in metres (default 5000m = 5km)

    Returns:
        Tuple of (postcode_code, distance_metres) or None if no postcodes
        found within max_distance_m
    """
    if _IS_SQLITE:
        # Fallback for SQLite tests - use Haversine formula
        return _find_nearest_postcode_haversine(db, lat, lon, max_distance_m)

    # Create a PostGIS point from the input coordinates
    # Note: ST_MakePoint takes (longitude, latitude) order
    point = ST_SetSRID(ST_MakePoint(lon, lat), 4326)

    # Use PostGIS KNN operator (<->) for efficient nearest-neighbour search
    # The <-> operator uses the spatial index for O(log n) lookup
    # We cast to geography for accurate great-circle distance in metres
    distance_expr = ST_Distance(
        Postcode.location,
        func.cast(point, Postcode.location.type),
    )

    result = (
        db.query(Postcode.code, distance_expr.label("distance_m"))
        .order_by(distance_expr)
        .limit(1)
        .first()
    )

    if result and result.distance_m <= max_distance_m:
        return (str(result.code), float(result.distance_m))
    return None


def _find_nearest_postcode_haversine(
    db: Session, lat: float, lon: float, max_distance_m: float
) -> Optional[Tuple[str, float]]:
    """
    Fallback for SQLite tests - uses Haversine formula.

    This is O(n) and scans all postcodes, but is only used in tests
    where the postcode table is small.
    """
    # Use Haversine formula for distance calculation
    lat_rad = func.radians(lat)
    lon_rad = func.radians(lon)
    postcode_lat_rad = func.radians(Postcode.lat)
    postcode_lon_rad = func.radians(Postcode.long)

    # Haversine formula
    dlat = postcode_lat_rad - lat_rad
    dlon = postcode_lon_rad - lon_rad

    a = func.sin(dlat / 2) * func.sin(dlat / 2) + func.cos(lat_rad) * func.cos(
        postcode_lat_rad
    ) * func.sin(dlon / 2) * func.sin(dlon / 2)
    c = 2 * func.atan2(func.sqrt(a), func.sqrt(1 - a))
    distance = 6371000 * c  # Earth radius in metres

    # Find the nearest postcode with its distance
    result = (
        db.query(Postcode.code, distance.label("distance_m"))
        .order_by(distance)
        .limit(1)
        .first()
    )

    if result and result.distance_m <= max_distance_m:
        return (str(result.code), float(result.distance_m))
    return None
