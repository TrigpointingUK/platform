"""
CRUD operations for location-related tables (postcodes, towns).
"""

from typing import Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from api.models.location import Postcode


def find_nearest_postcode(
    db: Session, lat: float, lon: float
) -> Optional[Tuple[str, float]]:
    """
    Find the nearest postcode to a given WGS84 coordinate using distance calculation.

    Args:
        db: Database session
        lat: Latitude (WGS84)
        lon: Longitude (WGS84)

    Returns:
        Tuple of (postcode_code, distance_metres) or None if no postcodes found
    """
    # Use Haversine formula for distance calculation
    # More accurate would be PostGIS ST_Distance, but this works for all DB backends
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

    if result:
        return (str(result.code), float(result.distance_m))
    return None
