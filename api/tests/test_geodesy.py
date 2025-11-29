"""
Tests for geodesy utilities.
"""

from api.utils.geodesy import haversine_distance, osgb_to_wgs84


def test_haversine_distance_zero():
    """Test distance between same point is zero."""
    lat, lon = 51.5074, -0.1278  # London
    distance = haversine_distance(lat, lon, lat, lon)
    assert distance == 0.0


def test_haversine_distance_known_points():
    """Test distance between known points."""
    # London to Paris (approximate)
    london_lat, london_lon = 51.5074, -0.1278
    paris_lat, paris_lon = 48.8566, 2.3522

    distance = haversine_distance(london_lat, london_lon, paris_lat, paris_lon)

    # Expected distance is approximately 344 km
    assert 340000 < distance < 350000


def test_haversine_distance_symmetry():
    """Test that distance is symmetric (A to B == B to A)."""
    lat1, lon1 = 52.0, -1.0
    lat2, lon2 = 53.0, -2.0

    distance_forward = haversine_distance(lat1, lon1, lat2, lon2)
    distance_reverse = haversine_distance(lat2, lon2, lat1, lon1)

    assert distance_forward == distance_reverse


def test_osgb_to_wgs84_conversion():
    """Test OSGB to WGS84 conversion produces reasonable values."""
    # Test point: TL 137 055 (approximate Cambridge area)
    eastings = 513700
    northings = 205500

    lat, lon = osgb_to_wgs84(eastings, northings)

    # Latitude should be in UK range (approximately 49-61)
    assert 49.0 < lat < 61.0

    # Longitude should be in UK range (approximately -8 to 2)
    assert -8.0 < lon < 2.0


def test_osgb_to_wgs84_fetlar():
    """Test conversion with real data from Fetlar trigpoint.

    Tests against Ordnance Survey ETRS89 coordinates:
    60.620248808764, -0.864837687763

    Note: WGS84 and ETRS89 are effectively identical for UK mapping purposes.
    """
    # Fetlar trigpoint location: HU 62229 93521
    eastings = 462229
    northings = 1193521

    lat, lon = osgb_to_wgs84(eastings, northings)

    # Check against OS coordinates with reasonable tolerance
    # (Helmert transformation should be accurate to ~5m / ~0.00005°)
    assert abs(lat - 60.620248808764) < 0.0001  # ~10m tolerance
    assert abs(lon - (-0.864837687763)) < 0.0001  # ~10m tolerance


def test_haversine_distance_short_distance():
    """Test distance calculation for short distances (metres scale)."""
    # Two points approximately 100m apart
    lat1, lon1 = 51.5074, -0.1278
    lat2, lon2 = 51.5083, -0.1278  # Approximately 100m north

    distance = haversine_distance(lat1, lon1, lat2, lon2)

    # Should be close to 100m (within 10% tolerance)
    assert 90 < distance < 110
