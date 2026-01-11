"""
Coordinate conversion service using OSTN15/OSGM15 for accurate UK transformations.

This module provides high-accuracy coordinate conversions between WGS84 and OSGB36
using the Ordnance Survey OSTN15 (horizontal) and OSGM15 (vertical) transformation
models via the pyproj library.

See: docs/decisions/0001-ostn15-coordinate-conversion.md
"""

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


# Create transformers lazily (thread-safe singletons)
_transformer_etrs89_to_bng_2d: Optional[Transformer] = None
_transformer_bng_to_etrs89_2d: Optional[Transformer] = None
_transformer_etrs89_to_bng_3d: Optional[Transformer] = None
_transformer_bng_to_etrs89_3d: Optional[Transformer] = None


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
    # Convert to integers for grid reference
    e = int(round(eastings))
    n = int(round(northings))

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

    # Test 2D transformation
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

    # Test 3D transformation (includes OSGM15 height)
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
