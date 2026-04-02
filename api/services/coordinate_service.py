"""
Coordinate conversion service using OSTN15/OSGM15 for accurate UK transformations
and TM65 for Irish Grid conversions.

This module provides high-accuracy coordinate conversions between WGS84 and:
- OSGB36 (British National Grid, EPSG:27700) using OSTN15/OSGM15
- TM65 (Irish Grid, EPSG:29903) for the island of Ireland

See: docs/decisions/0001-ostn15-coordinate-conversion.md
"""

import re
from typing import Optional, Tuple

from pyproj import Transformer, network

from api.core.logging import get_logger

logger = get_logger(__name__)

# EPSG codes for coordinate reference systems
# We use ETRS89 (not WGS84) as it's formally identical to WGS84 in GB but
# ensures pyproj selects OSTN15 transformation (0.03m accuracy) rather than
# generic Helmert transforms (1m+ accuracy).
EPSG_ETRS89_2D = "EPSG:4258"  # ETRS89 lat/lon (equivalent to WGS84 in GB)
EPSG_ETRS89_3D = "EPSG:4937"  # ETRS89 lat/lon + ellipsoidal height
EPSG_BNG_2D = "EPSG:27700"  # British National Grid
EPSG_BNG_3D = "EPSG:7405"  # British National Grid + ODN height

# Irish Grid CRS codes
EPSG_WGS84_2D = "EPSG:4326"  # WGS84 lat/lon
EPSG_IRISH_GRID = "EPSG:29903"  # TM65 / Irish Grid (2D projected)

# Irish vertical datum - Malin Head Ordnance Datum
# Used for all of Ireland (both ROI and Northern Ireland)
# OSGM15 geoid model covers Ireland for height conversion
EPSG_MALIN_HEIGHT = "EPSG:5731"  # Malin Head height (Irish vertical datum)
EPSG_ETRS89_MALIN = "EPSG:9449"  # ETRS89 + Malin Head height (compound CRS)

# Grid letters for OS National Grid reference conversion
# The 500km squares use a 2-column x 3-row arrangement covering GB
# First letter determined by both eastings (0-500km = col 0, 500-700km = col 1) and
# northings (0-500km = row 0, 500-1000km = row 1, 1000-1500km = row 2)
_GRID_500KM = [
    ["S", "T"],  # N 0-500000
    ["N", "O"],  # N 500000-1000000
    ["H", "J"],  # N 1000000-1500000
]

# Second letter: 100km square within the 500km square (5x5 grid, A-Z minus I)
# A-E at north (top), V-Z at south (bottom)
_GRID_100KM = [
    ["A", "B", "C", "D", "E"],  # Row 4 (north, n100km_in_500km == 4, N 400-500km)
    ["F", "G", "H", "J", "K"],  # Row 3 (note: no I)
    ["L", "M", "N", "O", "P"],  # Row 2
    ["Q", "R", "S", "T", "U"],  # Row 1
    ["V", "W", "X", "Y", "Z"],  # Row 0 (south, n100km_in_500km == 0, N 0-100km)
]

# Irish Grid letter layout (single letter, 100km squares)
# The Irish Grid uses a single letter (A-Z excluding I) for 100km squares
# Letters are arranged in a 5x5 grid covering 0-500km E × 0-500km N
# Row 0 (south) = V,W,X,Y,Z; Row 4 (north) = A,B,C,D,E
_IRISH_GRID_LETTERS = [
    ["A", "B", "C", "D", "E"],  # Row 4 (N 400-500km)
    ["F", "G", "H", "J", "K"],  # Row 3 (N 300-400km) - note: no I
    ["L", "M", "N", "O", "P"],  # Row 2 (N 200-300km)
    ["Q", "R", "S", "T", "U"],  # Row 1 (N 100-200km)
    ["V", "W", "X", "Y", "Z"],  # Row 0 (N 0-100km)
]

# Reverse lookup: letter -> (column, row) for Irish Grid
_IRISH_LETTER_TO_GRID: dict[str, tuple[int, int]] = {}
for row_idx, row in enumerate(_IRISH_GRID_LETTERS):
    for col_idx, letter in enumerate(row):
        # Store as (easting_100km, northing_100km)
        # row_idx 0 = northing 400-500km, row_idx 4 = northing 0-100km
        _IRISH_LETTER_TO_GRID[letter] = (col_idx, 4 - row_idx)


# Create transformers lazily (thread-safe singletons)
_transformer_etrs89_to_bng_2d: Optional[Transformer] = None
_transformer_bng_to_etrs89_2d: Optional[Transformer] = None
_transformer_etrs89_to_bng_3d: Optional[Transformer] = None
_transformer_bng_to_etrs89_3d: Optional[Transformer] = None

# Irish Grid transformers (2D horizontal only)
_transformer_wgs84_to_irish: Optional[Transformer] = None
_transformer_irish_to_wgs84: Optional[Transformer] = None

# Irish Grid 3D transformers (for Malin Head height conversion using OSGM15)
_transformer_etrs89_to_malin_3d: Optional[Transformer] = None
_transformer_malin_to_etrs89_3d: Optional[Transformer] = None


def _get_transformer_etrs89_to_bng_2d() -> Transformer:
    """Get or create the ETRS89 -> BNG 2D transformer (uses OSTN15)."""
    global _transformer_etrs89_to_bng_2d
    if _transformer_etrs89_to_bng_2d is None:
        _transformer_etrs89_to_bng_2d = Transformer.from_crs(
            EPSG_ETRS89_2D, EPSG_BNG_2D, always_xy=True
        )
    return _transformer_etrs89_to_bng_2d


def _get_transformer_bng_to_etrs89_2d() -> Transformer:
    """Get or create the BNG -> ETRS89 2D transformer (uses OSTN15)."""
    global _transformer_bng_to_etrs89_2d
    if _transformer_bng_to_etrs89_2d is None:
        _transformer_bng_to_etrs89_2d = Transformer.from_crs(
            EPSG_BNG_2D, EPSG_ETRS89_2D, always_xy=True
        )
    return _transformer_bng_to_etrs89_2d


def _get_transformer_etrs89_to_bng_3d() -> Transformer:
    """Get or create the ETRS89 -> BNG 3D transformer (uses OSTN15/OSGM15)."""
    global _transformer_etrs89_to_bng_3d
    if _transformer_etrs89_to_bng_3d is None:
        _transformer_etrs89_to_bng_3d = Transformer.from_crs(
            EPSG_ETRS89_3D, EPSG_BNG_3D, always_xy=True
        )
    return _transformer_etrs89_to_bng_3d


def _get_transformer_bng_to_etrs89_3d() -> Transformer:
    """Get or create the BNG -> ETRS89 3D transformer (uses OSTN15/OSGM15)."""
    global _transformer_bng_to_etrs89_3d
    if _transformer_bng_to_etrs89_3d is None:
        _transformer_bng_to_etrs89_3d = Transformer.from_crs(
            EPSG_BNG_3D, EPSG_ETRS89_3D, always_xy=True
        )
    return _transformer_bng_to_etrs89_3d


def _get_transformer_wgs84_to_irish() -> Transformer:
    """Get or create the WGS84 -> Irish Grid transformer."""
    global _transformer_wgs84_to_irish
    if _transformer_wgs84_to_irish is None:
        _transformer_wgs84_to_irish = Transformer.from_crs(
            EPSG_WGS84_2D, EPSG_IRISH_GRID, always_xy=True
        )
    return _transformer_wgs84_to_irish


def _get_transformer_irish_to_wgs84() -> Transformer:
    """Get or create the Irish Grid -> WGS84 transformer."""
    global _transformer_irish_to_wgs84
    if _transformer_irish_to_wgs84 is None:
        _transformer_irish_to_wgs84 = Transformer.from_crs(
            EPSG_IRISH_GRID, EPSG_WGS84_2D, always_xy=True
        )
    return _transformer_irish_to_wgs84


def _get_transformer_etrs89_to_malin_3d() -> Transformer:
    """Get or create the ETRS89 3D -> ETRS89 + Malin Height transformer.

    Uses OSGM15 geoid model for height conversion from ellipsoidal to orthometric.
    """
    global _transformer_etrs89_to_malin_3d
    if _transformer_etrs89_to_malin_3d is None:
        _transformer_etrs89_to_malin_3d = Transformer.from_crs(
            EPSG_ETRS89_3D, EPSG_ETRS89_MALIN, always_xy=True
        )
    return _transformer_etrs89_to_malin_3d


def _get_transformer_malin_to_etrs89_3d() -> Transformer:
    """Get or create the ETRS89 + Malin Height -> ETRS89 3D transformer.

    Uses OSGM15 geoid model for height conversion from orthometric to ellipsoidal.
    """
    global _transformer_malin_to_etrs89_3d
    if _transformer_malin_to_etrs89_3d is None:
        _transformer_malin_to_etrs89_3d = Transformer.from_crs(
            EPSG_ETRS89_MALIN, EPSG_ETRS89_3D, always_xy=True
        )
    return _transformer_malin_to_etrs89_3d


def convert_wgs84_to_osgb(
    lon: float, lat: float, height: Optional[float] = None
) -> Tuple[float, float, Optional[float]]:
    """
    Convert WGS84/ETRS89 coordinates to OSGB36 British National Grid.

    Uses OSTN15 for horizontal transformation and OSGM15 for height conversion
    when height is provided. Internally uses ETRS89 CRS codes to ensure pyproj
    selects the OSTN15 transformation (ETRS89 and WGS84 are equivalent in GB).

    Args:
        lon: Longitude in decimal degrees (WGS84/ETRS89)
        lat: Latitude in decimal degrees (WGS84/ETRS89)
        height: Optional ellipsoidal height in metres (above WGS84/GRS80 ellipsoid)

    Returns:
        Tuple of (eastings, northings, orthometric_height or None)
        - eastings: OSGB36 eastings in metres
        - northings: OSGB36 northings in metres
        - orthometric_height: Height above ODN (Newlyn) in metres, or None if
          input height was not provided
    """
    if height is not None:
        transformer = _get_transformer_etrs89_to_bng_3d()
        e, n, h = transformer.transform(lon, lat, height)
        return e, n, h
    else:
        transformer = _get_transformer_etrs89_to_bng_2d()
        e, n = transformer.transform(lon, lat)
        return e, n, None


def convert_osgb_to_wgs84(
    eastings: float, northings: float, height: Optional[float] = None
) -> Tuple[float, float, Optional[float]]:
    """
    Convert OSGB36 British National Grid coordinates to WGS84/ETRS89.

    Uses OSTN15 for horizontal transformation and OSGM15 for height conversion
    when height is provided. Internally uses ETRS89 CRS codes to ensure pyproj
    selects the OSTN15 transformation (ETRS89 and WGS84 are equivalent in GB).

    Args:
        eastings: OSGB36 eastings in metres
        northings: OSGB36 northings in metres
        height: Optional orthometric height in metres (above ODN/Newlyn)

    Returns:
        Tuple of (longitude, latitude, ellipsoidal_height or None)
        - longitude: WGS84/ETRS89 longitude in decimal degrees
        - latitude: WGS84/ETRS89 latitude in decimal degrees
        - ellipsoidal_height: Height above WGS84/GRS80 ellipsoid in metres, or None if
          input height was not provided
    """
    if height is not None:
        transformer = _get_transformer_bng_to_etrs89_3d()
        lon, lat, h = transformer.transform(eastings, northings, height)
        return lon, lat, h
    else:
        transformer = _get_transformer_bng_to_etrs89_2d()
        lon, lat = transformer.transform(eastings, northings)
        return lon, lat, None


def eastings_northings_to_gridref(eastings: float, northings: float) -> str:
    """
    Convert OSGB36 eastings/northings to an OS National Grid reference string.

    Args:
        eastings: OSGB36 eastings in metres
        northings: OSGB36 northings in metres

    Returns:
        Grid reference string in format "XX NNNNN NNNNN" (e.g., "TQ 30005 80433")

    Raises:
        ValueError: If coordinates are outside the GB National Grid bounds
    """
    # Truncate to integers for grid reference (grid refs use truncation, not rounding)
    e = int(eastings)
    n = int(northings)

    # Check bounds (GB National Grid extends from 0,0 to 700000,1300000 approximately)
    if e < 0 or e > 700000 or n < 0 or n > 1300000:
        raise ValueError(
            f"Coordinates ({eastings}, {northings}) are outside the GB National Grid"
        )

    # Calculate 500km square indices for first letter
    e500km = e // 500000  # 0 = S/N/H column, 1 = T/O/J column
    n500km = n // 500000  # 0 = S/T row, 1 = N/O row, 2 = H/J row

    if n500km >= len(_GRID_500KM) or e500km >= len(_GRID_500KM[0]):
        raise ValueError(
            f"Coordinates ({eastings}, {northings}) are outside the GB National Grid"
        )

    first_letter = _GRID_500KM[n500km][e500km]

    # Calculate 100km square indices within the 500km square for second letter
    # Position within 500km square
    e_in_500km = e % 500000
    n_in_500km = n % 500000

    # 100km column and row within 500km square
    e100km_in_500km = e_in_500km // 100000  # 0-4
    n100km_in_500km = n_in_500km // 100000  # 0-4

    # Row in _GRID_100KM (inverted because letters go north to south)
    row = 4 - n100km_in_500km
    col = e100km_in_500km
    second_letter = _GRID_100KM[row][col]

    # Get numeric part (within 100km square)
    e_within = e % 100000
    n_within = n % 100000

    # Format as 5-digit strings with leading zeros
    e_str = str(e_within).zfill(5)
    n_str = str(n_within).zfill(5)

    return f"{first_letter}{second_letter} {e_str} {n_str}"


# =============================================================================
# Irish Grid (EPSG:29903) conversion functions
# =============================================================================


def convert_wgs84_to_irish(
    lon: float, lat: float, height: Optional[float] = None
) -> Tuple[float, float, Optional[float]]:
    """
    Convert WGS84/ETRS89 coordinates to Irish Grid (TM65/EPSG:29903).

    Uses OSGM15 geoid model for height conversion when height is provided,
    converting ellipsoidal height to orthometric height above Malin Head datum.

    Args:
        lon: Longitude in decimal degrees (WGS84/ETRS89)
        lat: Latitude in decimal degrees (WGS84/ETRS89)
        height: Optional ellipsoidal height in metres (above WGS84/GRS80 ellipsoid)

    Returns:
        Tuple of (eastings, northings, orthometric_height or None)
        - eastings: Irish Grid eastings in metres
        - northings: Irish Grid northings in metres
        - orthometric_height: Height above Malin Head datum in metres, or None if
          input height was not provided
    """
    # Get horizontal coordinates
    transformer_2d = _get_transformer_wgs84_to_irish()
    e, n = transformer_2d.transform(lon, lat)

    # Convert height if provided
    if height is not None:
        transformer_3d = _get_transformer_etrs89_to_malin_3d()
        # The 3D transformer returns (lon, lat, orthometric_height)
        _, _, ortho_h = transformer_3d.transform(lon, lat, height)
        return e, n, ortho_h
    else:
        return e, n, None


def convert_irish_to_wgs84(
    eastings: float, northings: float, height: Optional[float] = None
) -> Tuple[float, float, Optional[float]]:
    """
    Convert Irish Grid (TM65/EPSG:29903) coordinates to WGS84/ETRS89.

    Uses OSGM15 geoid model for height conversion when height is provided,
    converting orthometric height (Malin Head datum) to ellipsoidal height.

    Args:
        eastings: Irish Grid eastings in metres
        northings: Irish Grid northings in metres
        height: Optional orthometric height in metres (above Malin Head datum)

    Returns:
        Tuple of (longitude, latitude, ellipsoidal_height or None)
        - longitude: WGS84/ETRS89 longitude in decimal degrees
        - latitude: WGS84/ETRS89 latitude in decimal degrees
        - ellipsoidal_height: Height above WGS84/GRS80 ellipsoid in metres, or None if
          input height was not provided
    """
    # Get horizontal coordinates
    transformer_2d = _get_transformer_irish_to_wgs84()
    lon, lat = transformer_2d.transform(eastings, northings)

    # Convert height if provided
    if height is not None:
        transformer_3d = _get_transformer_malin_to_etrs89_3d()
        # The 3D transformer expects (lon, lat, orthometric_height) and returns
        # (lon, lat, ellipsoidal_height)
        _, _, ellip_h = transformer_3d.transform(lon, lat, height)
        return lon, lat, ellip_h
    else:
        return lon, lat, None


def eastings_northings_to_irish_gridref(eastings: float, northings: float) -> str:
    """
    Convert Irish Grid eastings/northings to an Irish Grid reference string.

    The Irish Grid uses a single letter (A-Z excluding I) for 100km squares,
    arranged in a 5x5 grid covering the island of Ireland.

    Args:
        eastings: Irish Grid eastings in metres
        northings: Irish Grid northings in metres

    Returns:
        Grid reference string in format "X NNNNN NNNNN" (e.g., "O 31500 23400")

    Raises:
        ValueError: If coordinates are outside the Irish Grid bounds
    """
    # Truncate to integers for grid reference (grid refs use truncation, not rounding)
    e = int(eastings)
    n = int(northings)

    # Check bounds (Irish Grid extends from 0,0 to 500000,500000 approximately)
    if e < 0 or e > 500000 or n < 0 or n > 500000:
        raise ValueError(
            f"Coordinates ({eastings}, {northings}) are outside the Irish Grid"
        )

    # Calculate 100km square indices
    e100km = e // 100000  # 0-4
    n100km = n // 100000  # 0-4

    if e100km > 4 or n100km > 4:
        raise ValueError(
            f"Coordinates ({eastings}, {northings}) are outside the Irish Grid"
        )

    # Get letter from grid (row index is inverted: 0=north, 4=south)
    row = 4 - n100km
    col = e100km
    letter = _IRISH_GRID_LETTERS[row][col]

    # Get numeric part (within 100km square)
    e_within = e % 100000
    n_within = n % 100000

    # Format as 5-digit strings with leading zeros
    e_str = str(e_within).zfill(5)
    n_str = str(n_within).zfill(5)

    return f"{letter} {e_str} {n_str}"


def irish_gridref_to_eastings_northings(gridref: str) -> Tuple[int, int]:
    """
    Parse an Irish Grid reference and return eastings/northings.

    Supports formats like:
    - "O123456" (6 digits)
    - "O 123 456" (with spaces)
    - "O12345678" (8 digits)
    - "O 1234 5678" (8 digits with spaces)
    - "O 12345 67890" (10 digits with spaces)

    Args:
        gridref: Irish Grid reference string (single letter + digits)

    Returns:
        Tuple of (eastings, northings) in metres

    Raises:
        ValueError: If grid reference is invalid
    """
    # Normalize: uppercase, remove spaces
    gridref_norm = gridref.upper().replace(" ", "")

    # Match pattern: 1 letter + digits
    match = re.match(r"^([A-HJ-Z])(\d+)$", gridref_norm)
    if not match:
        raise ValueError(f"Invalid Irish grid reference format: {gridref}")

    letter, digits = match.groups()

    # Check if letter is valid (must be in our lookup)
    if letter not in _IRISH_LETTER_TO_GRID:
        raise ValueError(f"Invalid Irish grid letter: {letter}")

    # Digits must be even length (pairs for easting/northing)
    if len(digits) % 2 != 0:
        raise ValueError(
            f"Invalid Irish grid reference: odd number of digits in {gridref}"
        )

    # Split digits into easting/northing
    mid = len(digits) // 2
    easting_str = digits[:mid]
    northing_str = digits[mid:]

    # Pad to 5 digits (1m resolution)
    easting_str = easting_str.ljust(5, "0")
    northing_str = northing_str.ljust(5, "0")

    # Get 100km square offset
    e100km, n100km = _IRISH_LETTER_TO_GRID[letter]

    # Calculate full easting/northing
    eastings = e100km * 100000 + int(easting_str)
    northings = n100km * 100000 + int(northing_str)

    return eastings, northings


def parse_irish_gridref(gridref: str) -> Optional[Tuple[float, float, str]]:
    """
    Parse an Irish Grid reference and return WGS84 coordinates.

    Args:
        gridref: Irish Grid reference string

    Returns:
        Tuple of (lat, lon, normalized_gridref) or None if invalid
    """
    try:
        eastings, northings = irish_gridref_to_eastings_northings(gridref)
        lon, lat, _ = convert_irish_to_wgs84(eastings, northings)

        # Format normalized gridref
        e_str = str(eastings % 100000).zfill(5)
        n_str = str(northings % 100000).zfill(5)
        e100km = eastings // 100000
        n100km = northings // 100000
        row = 4 - n100km
        letter = _IRISH_GRID_LETTERS[row][e100km]
        normalized = f"{letter} {e_str} {n_str}"

        return lat, lon, normalized
    except (ValueError, IndexError):
        return None


def is_irish_gridref(gridref: str) -> bool:
    """
    Check if a string looks like an Irish Grid reference.

    Irish Grid references have a single letter (A-Z excluding I) followed by digits.
    OSGB references have two letters.

    Args:
        gridref: Grid reference string to check

    Returns:
        True if it looks like an Irish Grid reference
    """
    gridref_norm = gridref.upper().replace(" ", "")
    # Irish: single letter (not I) + even number of digits
    match = re.match(r"^([A-HJ-Z])(\d+)$", gridref_norm)
    if match:
        letter, digits = match.groups()
        return letter in _IRISH_LETTER_TO_GRID and len(digits) % 2 == 0
    return False


def is_osgb_gridref(gridref: str) -> bool:
    """
    Check if a string looks like an OSGB Grid reference.

    OSGB Grid references have two letters followed by digits.

    Args:
        gridref: Grid reference string to check

    Returns:
        True if it looks like an OSGB Grid reference
    """
    gridref_norm = gridref.upper().replace(" ", "")
    # OSGB: two letters + even number of digits
    match = re.match(r"^([A-Z]{2})(\d+)$", gridref_norm)
    return match is not None and len(match.group(2)) % 2 == 0


def verify_ostn15_available() -> bool:
    """
    Verify that OSTN15 transformation is available and working correctly.

    This function should be called at application startup to ensure the
    transformation grid files are properly loaded. It performs a test
    transformation using official Ordnance Survey reference data and
    verifies the result is within expected accuracy.

    Returns:
        True if OSTN15 is available and working

    Raises:
        RuntimeError: If OSTN15 is not available or producing incorrect results
    """
    # Check that network access is disabled (we should use local grid files)
    if network.is_network_enabled():
        logger.warning(
            "PROJ network access is enabled - transformation may use remote grids"
        )

    # Official Ordnance Survey test data (from OS online coordinate converter):
    # ETRS89: 51.507879, -0.128094, 10m (ellipsoidal height)
    # OSGB36: 530005.2410, 180432.6360, -35.549m (ODN)
    test_lon = -0.128094
    test_lat = 51.507879
    test_height = 10.0

    expected_e = 530005.2410
    expected_n = 180432.6360
    expected_osgb_h = -35.549

    # Verify 2D transformation
    try:
        e, n, _ = convert_wgs84_to_osgb(test_lon, test_lat)
    except Exception as exc:
        raise RuntimeError(f"OSTN15 transformation failed: {exc}") from exc

    # Check horizontal result - OSTN15 should give sub-metre accuracy
    # Helmert fallback would be off by hundreds of metres
    tolerance_2d = 0.01  # 1cm - OSTN15 should easily achieve this

    e_diff = abs(e - expected_e)
    n_diff = abs(n - expected_n)

    if e_diff > tolerance_2d or n_diff > tolerance_2d:
        raise RuntimeError(
            f"OSTN15 transformation appears inaccurate. "
            f"Expected ({expected_e:.4f}, {expected_n:.4f}), got ({e:.4f}, {n:.4f}). "
            f"Difference: ({e_diff:.4f}m, {n_diff:.4f}m). "
            f"This may indicate OSTN15 grid files are not loaded."
        )

    # Verify 3D transformation (includes OSGM15 height)
    try:
        e3, n3, osgb_h = convert_wgs84_to_osgb(test_lon, test_lat, test_height)
    except Exception as exc:
        raise RuntimeError(f"OSGM15 height transformation failed: {exc}") from exc

    if osgb_h is None:
        raise RuntimeError("OSGM15 height transformation returned None")

    # Check height - OSGM15 should give sub-metre accuracy
    tolerance_3d = 0.01  # 1cm
    h_diff = abs(osgb_h - expected_osgb_h)

    if h_diff > tolerance_3d:
        raise RuntimeError(
            f"OSGM15 height transformation appears inaccurate. "
            f"Expected height {expected_osgb_h:.3f}m, got {osgb_h:.3f}m. "
            f"Difference: {h_diff:.4f}m. "
            f"This may indicate OSGM15 grid file is not loaded."
        )

    logger.info(
        "OSTN15/OSGM15 verification passed: "
        f"2D accuracy {max(e_diff, n_diff):.4f}m, "
        f"3D height accuracy {h_diff:.4f}m"
    )

    return True
