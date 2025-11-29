"""
Geodesy utilities for coordinate conversions and distance calculations.
"""

import math
from typing import Tuple


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate the great-circle distance between two points on Earth using the Haversine formula.

    Args:
        lat1: Latitude of first point in decimal degrees
        lon1: Longitude of first point in decimal degrees
        lat2: Latitude of second point in decimal degrees
        lon2: Longitude of second point in decimal degrees

    Returns:
        Distance in metres
    """
    # Earth's radius in metres
    R = 6371000

    # Convert to radians
    lat1_rad = math.radians(lat1)
    lat2_rad = math.radians(lat2)
    delta_lat = math.radians(lat2 - lat1)
    delta_lon = math.radians(lon2 - lon1)

    # Haversine formula
    a = (
        math.sin(delta_lat / 2) ** 2
        + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(delta_lon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c

    return distance


def osgb_to_wgs84(eastings: int, northings: int) -> Tuple[float, float]:
    """
    Convert OSGB36 eastings/northings to WGS84 lat/lon.

    This is a simplified approximation using linear transformation.
    For production use, consider using a proper library like pyproj for more accuracy.

    Args:
        eastings: OSGB eastings
        northings: OSGB northings

    Returns:
        Tuple of (latitude, longitude) in WGS84
    """
    # Simplified conversion - this is an approximation
    # Origin point (approximately SW England)
    lat0 = 49.0
    lon0 = -2.0

    # Scale factors (approximate)
    lat_per_m = 1.0 / 111320.0  # metres per degree latitude
    lon_per_m = 1.0 / (111320.0 * 0.7)  # adjusted for UK latitude

    # Convert from false origin
    e = eastings - 400000  # OSGB false easting
    n = northings - (-100000)  # OSGB false northing

    lat = lat0 + n * lat_per_m
    lon = lon0 + e * lon_per_m

    return lat, lon
