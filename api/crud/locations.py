"""
CRUD operations for location search.
"""

import re
from typing import List, Optional, Tuple

from sqlalchemy import or_
from sqlalchemy.orm import Session

from api.models.location import Postcode, Postcode6, Town
from api.models.trig import Trig

# OSGB Grid reference mapping for 100km squares
OSGB_GRID_LETTERS = {
    "SV": (0, 0),
    "SW": (1, 0),
    "SX": (2, 0),
    "SY": (3, 0),
    "SZ": (4, 0),
    "TV": (5, 0),
    "TW": (6, 0),
    "SR": (1, 1),
    "SS": (2, 1),
    "ST": (3, 1),
    "SU": (4, 1),
    "TQ": (5, 1),
    "TR": (6, 1),
    "SM": (1, 2),
    "SN": (2, 2),
    "SO": (3, 2),
    "SP": (4, 2),
    "TL": (5, 2),
    "TM": (6, 2),
    "SH": (2, 3),
    "SJ": (3, 3),
    "SK": (4, 3),
    "TF": (5, 3),
    "TG": (6, 3),
    "SC": (2, 4),
    "SD": (3, 4),
    "SE": (4, 4),
    "TA": (5, 4),
    "NW": (1, 5),
    "NX": (2, 5),
    "NY": (3, 5),
    "NZ": (4, 5),
    "OV": (5, 5),
    "NR": (1, 6),
    "NS": (2, 6),
    "NT": (3, 6),
    "NU": (4, 6),
    "NL": (1, 7),
    "NM": (2, 7),
    "NN": (3, 7),
    "NO": (4, 7),
    "NF": (1, 8),
    "NG": (2, 8),
    "NH": (3, 8),
    "NJ": (4, 8),
    "NK": (5, 8),
    "NA": (1, 9),
    "NB": (2, 9),
    "NC": (3, 9),
    "ND": (4, 9),
    "HW": (1, 10),
    "HX": (2, 10),
    "HY": (3, 10),
    "HZ": (4, 10),
    "HT": (3, 11),
    "HU": (4, 11),
    "HP": (4, 12),
}


def search_trigpoints_by_name_or_waypoint(
    db: Session, query: str, limit: int = 10
) -> List[Trig]:
    """
    Search trigpoints by name or waypoint code.

    Args:
        db: Database session
        query: Search query
        limit: Maximum results to return

    Returns:
        List of Trig objects matching the query
    """
    query_upper = query.upper()
    return (
        db.query(Trig)
        .filter(
            or_(
                Trig.name.ilike(f"%{query}%"),
                Trig.waypoint.ilike(f"{query_upper}%"),
            )
        )
        .limit(limit)
        .all()
    )


def search_trigpoints_by_station_number(
    db: Session, query: str, skip: int = 0, limit: int = 10
) -> List[Trig]:
    """
    Search trigpoints by station numbers (fb_number and variant station numbers).

    Note: stn_number field is deprecated - searches only the specific variants
    (active, passive, osgb36) to encourage migration to specific fields.

    Args:
        db: Database session
        query: Search query
        skip: Number of results to skip
        limit: Maximum results to return

    Returns:
        List of Trig objects matching the query
    """
    query_upper = query.upper()
    return (
        db.query(Trig)
        .filter(
            or_(
                Trig.fb_number.ilike(f"%{query_upper}%"),
                Trig.stn_number_active.ilike(f"%{query_upper}%"),
                Trig.stn_number_passive.ilike(f"%{query_upper}%"),
                Trig.stn_number_osgb36.ilike(f"%{query_upper}%"),
            )
        )
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_trigpoints_by_station_number(db: Session, query: str) -> int:
    """
    Count trigpoints matching station number query.

    Note: stn_number field is deprecated - counts only the specific variants
    (active, passive, osgb36) to encourage migration to specific fields.

    Args:
        db: Database session
        query: Search query

    Returns:
        Count of matching trigpoints
    """
    query_upper = query.upper()
    return (
        db.query(Trig)
        .filter(
            or_(
                Trig.fb_number.ilike(f"%{query_upper}%"),
                Trig.stn_number_active.ilike(f"%{query_upper}%"),
                Trig.stn_number_passive.ilike(f"%{query_upper}%"),
                Trig.stn_number_osgb36.ilike(f"%{query_upper}%"),
            )
        )
        .count()
    )


def search_towns(db: Session, query: str, limit: int = 10) -> List[Town]:
    """
    Search towns by name.

    Args:
        db: Database session
        query: Search query
        limit: Maximum results to return

    Returns:
        List of Town objects matching the query
    """
    return db.query(Town).filter(Town.name.ilike(f"%{query}%")).limit(limit).all()


def search_postcodes(
    db: Session, query: str, skip: int = 0, limit: int = 10
) -> Tuple[List[Postcode6], List[Postcode]]:
    """
    Search postcodes in both postcode6 and postcodes tables.

    Args:
        db: Database session
        query: Search query (postcode)
        skip: Number of results to skip
        limit: Maximum results to return per table

    Returns:
        Tuple of (Postcode6 list, Postcode list)
    """
    # Normalize postcode: uppercase
    query_upper = query.upper().strip()

    # For postcode6 table (no spaces in codes)
    query_no_space = query_upper.replace(" ", "")

    # Search postcode6 (codes stored without spaces)
    pc6_results = (
        db.query(Postcode6)
        .filter(Postcode6.code.like(f"{query_no_space}%"))
        .offset(skip)
        .limit(limit)
        .all()
    )

    # Search postcodes table (codes stored WITH spaces like "PE27 4AB")
    # Replace multiple spaces with single space and search as-is
    query_normalized = " ".join(query_upper.split())
    postcodes_results = (
        db.query(Postcode)
        .filter(Postcode.code.like(f"{query_normalized}%"))
        .offset(skip)
        .limit(limit)
        .all()
    )

    return pc6_results, postcodes_results


def osgb_to_wgs84(eastings: int, northings: int) -> Tuple[float, float]:
    """
    Convert OSGB36 eastings/northings to WGS84 lat/lon.

    This is a simplified approximation using Helmert transformation.
    For production, consider using a proper library like pyproj.

    Args:
        eastings: OSGB eastings
        northings: OSGB northings

    Returns:
        Tuple of (latitude, longitude) in WGS84
    """
    # Simplified conversion - this is an approximation
    # For a proper implementation, you'd use pyproj or similar
    # For now, use a linear approximation good enough for UK

    # Origin point (approximately SW England)
    lat0 = 49.0
    lon0 = -2.0

    # Scale factors (approximate)
    lat_per_m = 1.0 / 111320.0  # meters per degree latitude
    lon_per_m = 1.0 / (111320.0 * 0.7)  # adjusted for UK latitude

    # Convert from false origin
    e = eastings - 400000  # OSGB false easting
    n = northings - -100000  # OSGB false northing

    lat = lat0 + n * lat_per_m
    lon = lon0 + e * lon_per_m

    return lat, lon


def parse_grid_reference(gridref: str) -> Optional[Tuple[float, float, str]]:
    """
    Parse an OSGB grid reference and return WGS84 coordinates.

    Supports formats like:
    - "SK123456" (6 digits)
    - "SK 123 456" (with spaces)
    - "SK12345678" (8 digits)
    - "SK 1234 5678" (8 digits with spaces)

    Args:
        gridref: OSGB grid reference string

    Returns:
        Tuple of (lat, lon, normalized_gridref) or None if invalid
    """
    # Normalize: uppercase, remove spaces
    gridref_norm = gridref.upper().replace(" ", "")

    # Match pattern: 2 letters + digits
    match = re.match(r"([A-Z]{2})(\d+)", gridref_norm)
    if not match:
        return None

    letters, digits = match.groups()

    # Check if letters are valid
    if letters not in OSGB_GRID_LETTERS:
        return None

    # Digits must be even length (pairs for easting/northing)
    if len(digits) % 2 != 0:
        return None

    # Split digits into easting/northing
    mid = len(digits) // 2
    easting_str = digits[:mid]
    northing_str = digits[mid:]

    # Pad to 5 digits (100m resolution)
    easting_str = easting_str.ljust(5, "0")
    northing_str = northing_str.ljust(5, "0")

    # Get 100km square offset
    square_e, square_n = OSGB_GRID_LETTERS[letters]

    # Calculate full easting/northing
    eastings = square_e * 100000 + int(easting_str)
    northings = square_n * 100000 + int(northing_str)

    # Convert to WGS84
    lat, lon = osgb_to_wgs84(eastings, northings)

    # Format normalized gridref
    normalized = f"{letters} {easting_str} {northing_str}"

    return lat, lon, normalized


def parse_latlon_string(text: str) -> Optional[Tuple[float, float]]:
    """
    Parse various lat/lon string formats.

    Supports formats like:
    - "51.5, -0.12"
    - "51.5,-0.12"
    - "51.5 -0.12"
    - "51.5N 0.12W"
    - "51.5N, 0.12W"

    Args:
        text: String to parse

    Returns:
        Tuple of (lat, lon) or None if invalid
    """
    # Remove common formatting
    text = text.strip().upper()

    # Try comma-separated
    if "," in text:
        parts = text.split(",")
        if len(parts) == 2:
            try:
                lat = float(parts[0].strip().replace("N", "").replace("S", ""))
                lon = float(parts[1].strip().replace("E", "").replace("W", ""))

                # Handle N/S/E/W indicators
                if "S" in parts[0]:
                    lat = -lat
                if "W" in parts[1]:
                    lon = -lon

                # Validate reasonable UK bounds
                if 49 <= lat <= 61 and -8 <= lon <= 2:
                    return lat, lon
            except ValueError:
                pass

    # Try space-separated
    parts = text.split()
    if len(parts) == 2:
        try:
            lat_str = parts[0].replace("N", "").replace("S", "")
            lon_str = parts[1].replace("E", "").replace("W", "")

            lat = float(lat_str)
            lon = float(lon_str)

            if "S" in parts[0]:
                lat = -lat
            if "W" in parts[1]:
                lon = -lon

            # Validate reasonable UK bounds
            if 49 <= lat <= 61 and -8 <= lon <= 2:
                return lat, lon
        except ValueError:
            pass

    return None
