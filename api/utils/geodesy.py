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
    Convert OSGB36 eastings/northings to WGS84 lat/lon using Helmert transformation.

    This implements the full transformation including:
    - Inverse Transverse Mercator projection (OSGB36 grid to OSGB36 lat/lon)
    - Helmert transformation (OSGB36 to WGS84)

    Based on Ordnance Survey's conversion equations.

    Args:
        eastings: OSGB eastings
        northings: OSGB northings

    Returns:
        Tuple of (latitude, longitude) in WGS84 decimal degrees
    """
    # OSGB36 ellipsoid parameters (Airy 1830)
    a_osgb = 6377563.396  # semi-major axis
    b_osgb = 6356256.909  # semi-minor axis
    e2_osgb = 1 - (b_osgb * b_osgb) / (a_osgb * a_osgb)

    # National Grid parameters
    lat0 = math.radians(49.0)  # True origin latitude
    lon0 = math.radians(-2.0)  # True origin longitude
    N0 = -100000  # Northing of true origin
    E0 = 400000  # Easting of true origin
    F0 = 0.9996012717  # Scale factor on central meridian

    n = (a_osgb - b_osgb) / (a_osgb + b_osgb)
    n2 = n * n
    n3 = n * n * n

    # Initial estimate of latitude
    lat = lat0 + (northings - N0) / (a_osgb * F0)

    # Iteratively refine latitude estimate
    for _ in range(10):
        M = (
            b_osgb
            * F0
            * (
                (1 + n + (5 / 4) * n2 + (5 / 4) * n3) * (lat - lat0)
                - (3 * n + 3 * n2 + (21 / 8) * n3)
                * math.sin(lat - lat0)
                * math.cos(lat + lat0)
                + ((15 / 8) * n2 + (15 / 8) * n3)
                * math.sin(2 * (lat - lat0))
                * math.cos(2 * (lat + lat0))
                - ((35 / 24) * n3)
                * math.sin(3 * (lat - lat0))
                * math.cos(3 * (lat + lat0))
            )
        )
        lat = lat + (northings - N0 - M) / (a_osgb * F0)

    sin_lat = math.sin(lat)
    cos_lat = math.cos(lat)
    nu = a_osgb * F0 / math.sqrt(1 - e2_osgb * sin_lat * sin_lat)
    rho = a_osgb * F0 * (1 - e2_osgb) / math.pow(1 - e2_osgb * sin_lat * sin_lat, 1.5)
    eta2 = nu / rho - 1

    tan_lat = math.tan(lat)
    tan2_lat = tan_lat * tan_lat
    tan4_lat = tan2_lat * tan2_lat
    tan6_lat = tan4_lat * tan2_lat

    VII = tan_lat / (2 * rho * nu)
    VIII = (tan_lat / (24 * rho * nu * nu * nu)) * (
        5 + 3 * tan2_lat + eta2 - 9 * tan2_lat * eta2
    )
    IX = (tan_lat / (720 * rho * math.pow(nu, 5))) * (
        61 + 90 * tan2_lat + 45 * tan4_lat
    )

    X = 1 / (cos_lat * nu)
    XI = 1 / (cos_lat * 6 * nu * nu * nu) * (nu / rho + 2 * tan2_lat)
    XII = 1 / (cos_lat * 120 * math.pow(nu, 5)) * (5 + 28 * tan2_lat + 24 * tan4_lat)
    XIIA = (
        1
        / (cos_lat * 5040 * math.pow(nu, 7))
        * (61 + 662 * tan2_lat + 1320 * tan4_lat + 720 * tan6_lat)
    )

    dE = eastings - E0
    dE2 = dE * dE
    dE3 = dE2 * dE
    dE4 = dE3 * dE
    dE5 = dE4 * dE
    dE6 = dE5 * dE
    dE7 = dE6 * dE

    lat_osgb = lat - VII * dE2 + VIII * dE4 - IX * dE6
    lon_osgb = lon0 + X * dE - XI * dE3 + XII * dE5 - XIIA * dE7

    # Convert OSGB36 to WGS84 using Helmert transformation
    # WGS84 ellipsoid parameters
    a_wgs = 6378137.0
    b_wgs = 6356752.314
    e2_wgs = 1 - (b_wgs * b_wgs) / (a_wgs * a_wgs)

    # Helmert transformation parameters (OSGB36 to WGS84)
    tx = 446.448  # metres
    ty = -125.157
    tz = 542.060
    rx = 0.1502  # seconds
    ry = 0.2470
    rz = 0.8421
    s = -20.4894  # ppm

    # Convert OSGB36 lat/lon to Cartesian coordinates
    nu2 = a_osgb / math.sqrt(1 - e2_osgb * math.sin(lat_osgb) * math.sin(lat_osgb))
    x1 = nu2 * math.cos(lat_osgb) * math.cos(lon_osgb)
    y1 = nu2 * math.cos(lat_osgb) * math.sin(lon_osgb)
    z1 = (1 - e2_osgb) * nu2 * math.sin(lat_osgb)

    # Apply Helmert transformation
    rx_rad = math.radians(rx / 3600)
    ry_rad = math.radians(ry / 3600)
    rz_rad = math.radians(rz / 3600)
    s1 = s / 1e6 + 1

    x2 = tx + x1 * s1 - y1 * rz_rad + z1 * ry_rad
    y2 = ty + x1 * rz_rad + y1 * s1 - z1 * rx_rad
    z2 = tz - x1 * ry_rad + y1 * rx_rad + z1 * s1

    # Convert Cartesian to WGS84 lat/lon
    p = math.sqrt(x2 * x2 + y2 * y2)
    lat_wgs = math.atan2(z2, p * (1 - e2_wgs))

    # Iterate to improve accuracy
    for _ in range(10):
        nu3 = a_wgs / math.sqrt(1 - e2_wgs * math.sin(lat_wgs) * math.sin(lat_wgs))
        lat_wgs = math.atan2(z2 + e2_wgs * nu3 * math.sin(lat_wgs), p)

    lon_wgs = math.atan2(y2, x2)

    return math.degrees(lat_wgs), math.degrees(lon_wgs)
