"""fix_town_wgs84_coordinates

Revision ID: a8b2c4d6e8f0
Revises: e9f5a7b34d02
Create Date: 2025-12-04

This migration fixes corrupted WGS84 coordinates in the town table.
All wgs_lat values were incorrectly set to 9.99999 (the max value for DECIMAL(6,5)).

The fix:
1. Increase column precision to DECIMAL(9,6) to accommodate UK coordinates properly
   (latitudes 49-61 need 2 digits before decimal; longitudes -8 to +2 need 1-2 digits)
2. Recalculate wgs_lat and wgs_long from osgb_eastings and osgb_northings
   using the Helmert transformation (OSGB36 to WGS84)
"""

import math
from typing import Sequence, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a8b2c4d6e8f0"
down_revision: Union[str, Sequence[str], None] = "e9f5a7b34d02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


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


def upgrade() -> None:
    """Fix corrupted WGS84 coordinates in town table.

    1. Increase column precision from DECIMAL(6,5) to DECIMAL(9,6)
       - DECIMAL(6,5) only allows 1 digit before decimal (max 9.99999)
       - UK latitudes need 2 digits (49-61), longitudes need 1-2 digits (-8 to +2)
    2. Recalculate all WGS84 coordinates from OSGB eastings/northings
    """
    # Step 1: Alter column types to accommodate full UK coordinate range
    op.alter_column(
        "town",
        "wgs_lat",
        existing_type=sa.DECIMAL(6, 5),
        type_=sa.DECIMAL(9, 6),
        existing_nullable=False,
    )
    op.alter_column(
        "town",
        "wgs_long",
        existing_type=sa.DECIMAL(6, 5),
        type_=sa.DECIMAL(9, 6),
        existing_nullable=False,
    )

    # Step 2: Recalculate WGS84 coordinates from OSGB using Helmert transformation
    connection = op.get_bind()

    # Fetch all towns
    result = connection.execute(
        sa.text("SELECT name, osgb_eastings, osgb_northings FROM town")
    )
    towns = result.fetchall()

    # Update each town with recalculated WGS84 coordinates
    update_stmt = sa.text(
        "UPDATE town SET wgs_lat = :lat, wgs_long = :lon WHERE name = :name"
    )

    for town in towns:
        name, eastings, northings = town
        if eastings is not None and northings is not None:
            lat, lon = osgb_to_wgs84(int(eastings), int(northings))
            connection.execute(
                update_stmt,
                {"lat": round(lat, 6), "lon": round(lon, 6), "name": name},
            )


def downgrade() -> None:
    """Revert column types (data will be truncated/corrupted again).

    WARNING: This downgrade will corrupt the data again due to precision loss.
    The DECIMAL(6,5) type cannot store UK latitudes correctly.
    """
    # Revert column types (will truncate/corrupt data)
    op.alter_column(
        "town",
        "wgs_lat",
        existing_type=sa.DECIMAL(9, 6),
        type_=sa.DECIMAL(6, 5),
        existing_nullable=False,
    )
    op.alter_column(
        "town",
        "wgs_long",
        existing_type=sa.DECIMAL(9, 6),
        type_=sa.DECIMAL(6, 5),
        existing_nullable=False,
    )
