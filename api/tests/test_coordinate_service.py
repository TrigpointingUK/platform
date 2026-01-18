"""
Unit tests for the coordinate conversion service.

Tests OSTN15 (horizontal) and OSGM15 (vertical) transformations for GB,
and Irish Grid (EPSG:29903) transformations for Ireland.
"""

import pytest

from api.services.coordinate_service import (
    convert_irish_to_wgs84,
    convert_osgb_to_wgs84,
    convert_wgs84_to_irish,
    convert_wgs84_to_osgb,
    eastings_northings_to_gridref,
    eastings_northings_to_irish_gridref,
    irish_gridref_to_eastings_northings,
    is_irish_gridref,
    is_osgb_gridref,
    parse_irish_gridref,
    verify_ostn15_available,
)


class TestWGS84ToOSGB:
    """Tests for WGS84/ETRS89 to OSGB36 conversion."""

    def test_london_official_os_data_2d(self):
        """Test conversion using official Ordnance Survey reference data (2D).

        Official OS test data:
        - ETRS89: 51.507879, -0.128094
        - OSGB36: 530005.2410, 180432.6360
        """
        lon, lat = -0.128094, 51.507879

        e, n, h = convert_wgs84_to_osgb(lon, lat)

        # OSTN15 should achieve sub-centimetre accuracy
        assert (
            abs(e - 530005.2410) < 0.01
        ), f"Eastings {e} differs from expected 530005.2410"
        assert (
            abs(n - 180432.6360) < 0.01
        ), f"Northings {n} differs from expected 180432.6360"
        assert h is None  # No height input, no height output

    def test_london_official_os_data_3d(self):
        """Test conversion using official Ordnance Survey reference data (3D).

        Official OS test data:
        - ETRS89: 51.507879, -0.128094, 10m (ellipsoidal)
        - OSGB36: 530005.2410, 180432.6360, -35.549m (ODN)
        """
        lon, lat = -0.128094, 51.507879
        wgs_height = 10.0  # 10m ellipsoidal height

        e, n, osgb_h = convert_wgs84_to_osgb(lon, lat, wgs_height)

        # OSTN15/OSGM15 should achieve sub-centimetre accuracy
        assert abs(e - 530005.2410) < 0.01, f"Eastings {e} differs from expected"
        assert abs(n - 180432.6360) < 0.01, f"Northings {n} differs from expected"
        assert osgb_h is not None
        assert (
            abs(osgb_h - (-35.549)) < 0.01
        ), f"Height {osgb_h} differs from expected -35.549"

    def test_london_geoid_separation(self):
        """Test geoid separation calculation for London area."""
        # At this test point, ellipsoidal 10m -> orthometric -35.549m
        # So geoid separation = 10 - (-35.549) = 45.549m
        lon, lat = -0.128094, 51.507879
        wgs_height = 100.0  # 100m ellipsoidal height

        e, n, osgb_h = convert_wgs84_to_osgb(lon, lat, wgs_height)

        # Height should be approximately 100 - 45.549 = 54.451m
        assert osgb_h is not None
        geoid_separation = wgs_height - osgb_h
        assert (
            45.0 < geoid_separation < 46.0
        ), f"Geoid separation {geoid_separation} outside expected range for London"

    def test_barra_differential_conversion(self):
        """Test conversion for Barra Differential (Western Isles).

        This is a known reference point from the database schema documentation.
        Note: Barra (lon=-7.43) is outside the OSGM15 geoid model coverage
        (which only extends to lon=-7.06), so height conversion is not available.
        """
        # Barra Differential: WGS84 coordinates from schema docs
        lon, lat = -7.43001, 56.96243
        wgs_height = 83.0  # From schema: wgs_height = 83

        e, n, osgb_h = convert_wgs84_to_osgb(lon, lat, wgs_height)

        # Expected BNG coordinates from schema: osgb_eastings=70095, osgb_northings=798813
        # Using 10m tolerance as schema values may be from different transformation
        assert abs(e - 70095) < 10, f"Eastings {e} should be close to 70095"
        assert abs(n - 798813) < 10, f"Northings {n} should be close to 798813"

        # Height: Barra is outside OSGM15 coverage, so height passes through unchanged
        # (or may have ballpark correction applied)
        assert osgb_h is not None

    def test_mainland_scotland_height_conversion(self):
        """Test 3D conversion for mainland Scotland (within OSGM15 coverage)."""
        # Point on mainland Scotland, well within OSGM15 bounds
        lon, lat = -4.0, 57.0
        wgs_height = 100.0

        e, n, osgb_h = convert_wgs84_to_osgb(lon, lat, wgs_height)

        # Should be in NH grid square (Highland)
        assert 200000 < e < 400000
        assert 700000 < n < 900000

        # Height should be transformed - mainland Scotland geoid separation is ~53m
        assert osgb_h is not None
        geoid_separation = wgs_height - osgb_h
        assert (
            50 < geoid_separation < 60
        ), f"Geoid separation {geoid_separation} outside expected range for Scotland"

    def test_edinburgh_conversion(self):
        """Test conversion for Edinburgh coordinates."""
        # Edinburgh Castle: approximate WGS84 coordinates
        lon, lat = -3.2, 55.95

        e, n, h = convert_wgs84_to_osgb(lon, lat)

        # Should be somewhere in the NT (Edinburgh area) grid square
        # Eastings around 325000, Northings around 673000
        assert 320000 < e < 330000, f"Eastings {e} outside expected range"
        assert 668000 < n < 678000, f"Northings {n} outside expected range"
        assert h is None


class TestOSGBToWGS84:
    """Tests for OSGB36 to WGS84/ETRS89 conversion."""

    def test_london_official_os_data_2d(self):
        """Test reverse conversion using official OS reference data (2D).

        Official OS test data:
        - OSGB36: 530005.2410, 180432.6360
        - ETRS89: 51.507879, -0.128094
        """
        e, n = 530005.2410, 180432.6360

        lon, lat, h = convert_osgb_to_wgs84(e, n)

        # OSTN15 should achieve high accuracy
        assert (
            abs(lon - (-0.128094)) < 0.000001
        ), f"Longitude {lon} differs from expected"
        assert abs(lat - 51.507879) < 0.000001, f"Latitude {lat} differs from expected"
        assert h is None

    def test_london_official_os_data_3d(self):
        """Test reverse conversion using official OS reference data (3D).

        Official OS test data:
        - OSGB36: 530005.2410, 180432.6360, -35.549m (ODN)
        - ETRS89: 51.507879, -0.128094, 10m (ellipsoidal)
        """
        e, n = 530005.2410, 180432.6360
        osgb_height = -35.549  # -35.549m orthometric (ODN)

        lon, lat, wgs_h = convert_osgb_to_wgs84(e, n, osgb_height)

        # OSTN15/OSGM15 should achieve high accuracy
        assert (
            abs(lon - (-0.128094)) < 0.000001
        ), f"Longitude {lon} differs from expected"
        assert abs(lat - 51.507879) < 0.000001, f"Latitude {lat} differs from expected"
        assert wgs_h is not None
        assert (
            abs(wgs_h - 10.0) < 0.01
        ), f"Ellipsoidal height {wgs_h} differs from expected 10.0"

    def test_barra_differential_reverse(self):
        """Test reverse conversion for Barra Differential.

        Note: Barra is outside OSGM15 geoid coverage, so height conversion
        is not available. We only test the horizontal conversion.
        """
        # Barra Differential: OSGB coordinates from schema
        e, n = 70095.0, 798813.0

        lon, lat, wgs_h = convert_osgb_to_wgs84(e, n)

        # Should get back approximately the original WGS84 coordinates
        assert (
            abs(lon - (-7.43001)) < 0.001
        ), f"Longitude {lon} should be close to -7.43001"
        assert (
            abs(lat - 56.96243) < 0.001
        ), f"Latitude {lat} should be close to 56.96243"
        assert wgs_h is None  # No height input


class TestRoundTrip:
    """Tests for round-trip conversions."""

    def test_wgs84_round_trip_2d(self):
        """Test that WGS84 -> OSGB -> WGS84 gives back original coordinates."""
        original_lon, original_lat = -1.5, 52.5

        # Forward conversion
        e, n, _ = convert_wgs84_to_osgb(original_lon, original_lat)

        # Reverse conversion
        result_lon, result_lat, _ = convert_osgb_to_wgs84(e, n)

        # Should get back (very close to) original coordinates
        assert (
            abs(result_lon - original_lon) < 0.00001
        ), f"Longitude round-trip error: {result_lon} vs {original_lon}"
        assert (
            abs(result_lat - original_lat) < 0.00001
        ), f"Latitude round-trip error: {result_lat} vs {original_lat}"

    def test_wgs84_round_trip_3d(self):
        """Test that WGS84 -> OSGB -> WGS84 gives back original coordinates including height."""
        original_lon, original_lat = -1.5, 52.5
        original_height = 150.0

        # Forward conversion
        e, n, osgb_h = convert_wgs84_to_osgb(
            original_lon, original_lat, original_height
        )

        # Reverse conversion
        result_lon, result_lat, result_h = convert_osgb_to_wgs84(e, n, osgb_h)

        # Should get back (very close to) original coordinates
        assert abs(result_lon - original_lon) < 0.00001
        assert abs(result_lat - original_lat) < 0.00001
        assert result_h is not None
        assert (
            abs(result_h - original_height) < 0.5
        ), f"Height round-trip error: {result_h} vs {original_height}"

    def test_osgb_round_trip_2d(self):
        """Test that OSGB -> WGS84 -> OSGB gives back original coordinates."""
        original_e, original_n = 400000.0, 300000.0

        # Forward conversion
        lon, lat, _ = convert_osgb_to_wgs84(original_e, original_n)

        # Reverse conversion
        result_e, result_n, _ = convert_wgs84_to_osgb(lon, lat)

        # Should get back (very close to) original coordinates
        # Within 1 metre
        assert (
            abs(result_e - original_e) < 1.0
        ), f"Eastings round-trip error: {result_e} vs {original_e}"
        assert (
            abs(result_n - original_n) < 1.0
        ), f"Northings round-trip error: {result_n} vs {original_n}"


class TestGridReference:
    """Tests for grid reference generation."""

    def test_london_gridref_official_os_data(self):
        """Test grid reference for official OS test point."""
        # Using official OS coordinates: 530005.2410, 180432.6360
        e, n = 530005, 180433  # Rounded to nearest metre

        gridref = eastings_northings_to_gridref(e, n)

        assert gridref == "TQ 30005 80433", f"Unexpected gridref: {gridref}"

    def test_edinburgh_gridref(self):
        """Test grid reference for Edinburgh area."""
        e, n = 325200, 673400

        gridref = eastings_northings_to_gridref(e, n)

        # Should be in NT grid square
        assert gridref.startswith("NT"), f"Expected NT grid square, got: {gridref}"
        assert gridref == "NT 25200 73400", f"Unexpected gridref: {gridref}"

    def test_barra_gridref(self):
        """Test grid reference for Barra (Western Isles)."""
        e, n = 70095, 798813

        gridref = eastings_northings_to_gridref(e, n)

        # From schema: "NL 70095 98813"
        assert gridref == "NL 70095 98813", f"Unexpected gridref: {gridref}"

    def test_cornwall_gridref(self):
        """Test grid reference for Cornwall (SW grid square)."""
        e, n = 150000, 50000

        gridref = eastings_northings_to_gridref(e, n)

        # Should be in SW grid square
        assert gridref.startswith("SW"), f"Expected SW grid square, got: {gridref}"

    def test_invalid_coordinates_raises(self):
        """Test that coordinates outside GB grid raise ValueError."""
        # Way outside GB grid
        with pytest.raises(ValueError, match="outside the GB National Grid"):
            eastings_northings_to_gridref(1000000, 100000)

        with pytest.raises(ValueError, match="outside the GB National Grid"):
            eastings_northings_to_gridref(-100, 100000)


class TestVerifyOSTN15:
    """Tests for the OSTN15 verification function."""

    def test_verify_passes(self):
        """Test that verification passes when OSTN15 is available."""
        # This test may fail in environments without OSTN15 grid files
        # In that case, the test itself serves as documentation that
        # the environment is not properly configured
        try:
            result = verify_ostn15_available()
            assert result is True
        except RuntimeError as e:
            # If we're in an environment without grid files (e.g., CI without Docker),
            # we expect this error. Skip the test in that case.
            if "OSTN15" in str(e) or "OSGM15" in str(e):
                pytest.skip(f"OSTN15/OSGM15 grid files not available: {e}")
            raise


# =============================================================================
# Irish Grid Tests (EPSG:29903)
# =============================================================================


class TestWGS84ToIrish:
    """Tests for WGS84/ETRS89 to Irish Grid (TM65/TM75) conversion.

    Note: Irish Grid conversion is 2D only (no height transformation).
    """

    def test_dublin_conversion(self):
        """Test conversion for Dublin.

        Dublin city centre: approximately lat=53.3498, lon=-6.2603
        Expected Irish Grid: approximately E=316200, N=234000
        """
        lon, lat = -6.2603, 53.3498

        e, n = convert_wgs84_to_irish(lon, lat)

        # Dublin should be in the O grid square (Eastings 300-400km, Northings 200-300km)
        assert 310000 < e < 320000, f"Eastings {e} outside expected Dublin range"
        assert 230000 < n < 240000, f"Northings {n} outside expected Dublin range"

    def test_belfast_conversion(self):
        """Test conversion for Belfast (Northern Ireland).

        Belfast city centre: approximately lat=54.5973, lon=-5.9301
        Expected Irish Grid: approximately E=334000, N=373000
        """
        lon, lat = -5.9301, 54.5973

        e, n = convert_wgs84_to_irish(lon, lat)

        # Belfast should be in the J grid square
        assert 330000 < e < 340000, f"Eastings {e} outside expected Belfast range"
        assert 370000 < n < 380000, f"Northings {n} outside expected Belfast range"

    def test_galway_conversion(self):
        """Test conversion for Galway (west coast).

        Galway city centre: approximately lat=53.2707, lon=-9.0568
        Expected Irish Grid: approximately E=131000, N=225000
        """
        lon, lat = -9.0568, 53.2707

        e, n = convert_wgs84_to_irish(lon, lat)

        # Galway should be in the M grid square (west)
        assert 125000 < e < 140000, f"Eastings {e} outside expected Galway range"
        assert 220000 < n < 230000, f"Northings {n} outside expected Galway range"

    def test_cork_conversion(self):
        """Test conversion for Cork (south coast).

        Cork city centre: approximately lat=51.8985, lon=-8.4756
        Expected Irish Grid: approximately E=167000, N=72000
        """
        lon, lat = -8.4756, 51.8985

        e, n = convert_wgs84_to_irish(lon, lat)

        # Cork should be in the W grid square (south)
        assert 160000 < e < 175000, f"Eastings {e} outside expected Cork range"
        assert 68000 < n < 78000, f"Northings {n} outside expected Cork range"


class TestIrishToWGS84:
    """Tests for Irish Grid to WGS84/ETRS89 conversion.

    Note: Irish Grid conversion is 2D only (no height transformation).
    """

    def test_dublin_reverse(self):
        """Test reverse conversion for Dublin."""
        e, n = 316200.0, 234000.0

        lon, lat = convert_irish_to_wgs84(e, n)

        # Dublin is approximately lat=53.35, lon=-6.26
        assert -6.3 < lon < -6.2, f"Longitude {lon} outside expected Dublin range"
        assert 53.3 < lat < 53.4, f"Latitude {lat} outside expected Dublin range"

    def test_belfast_reverse(self):
        """Test reverse conversion for Belfast."""
        e, n = 334000.0, 373000.0

        lon, lat = convert_irish_to_wgs84(e, n)

        # Belfast is approximately lat=54.6, lon=-5.9
        assert -6.0 < lon < -5.8, f"Longitude {lon} outside expected Belfast range"
        assert 54.5 < lat < 54.7, f"Latitude {lat} outside expected Belfast range"


class TestIrishRoundTrip:
    """Tests for round-trip Irish Grid conversions.

    Note: Irish Grid conversion is 2D only (no height transformation).
    """

    def test_wgs84_round_trip_ireland(self):
        """Test WGS84 -> Irish -> WGS84 round trip."""
        original_lon, original_lat = -7.5, 53.0  # Somewhere in central Ireland

        # Forward conversion
        e, n = convert_wgs84_to_irish(original_lon, original_lat)

        # Reverse conversion
        result_lon, result_lat = convert_irish_to_wgs84(e, n)

        # Should get back (very close to) original coordinates
        assert (
            abs(result_lon - original_lon) < 0.0001
        ), f"Longitude round-trip error: {result_lon} vs {original_lon}"
        assert (
            abs(result_lat - original_lat) < 0.0001
        ), f"Latitude round-trip error: {result_lat} vs {original_lat}"

    def test_irish_grid_round_trip(self):
        """Test Irish Grid -> WGS84 -> Irish Grid round trip."""
        original_e, original_n = 200000.0, 250000.0  # Somewhere in Ireland

        # Forward conversion
        lon, lat = convert_irish_to_wgs84(original_e, original_n)

        # Reverse conversion
        result_e, result_n = convert_wgs84_to_irish(lon, lat)

        # Should get back (very close to) original coordinates
        # Within 1 metre
        assert (
            abs(result_e - original_e) < 1.0
        ), f"Eastings round-trip error: {result_e} vs {original_e}"
        assert (
            abs(result_n - original_n) < 1.0
        ), f"Northings round-trip error: {result_n} vs {original_n}"


class TestIrishGridReference:
    """Tests for Irish Grid reference generation and parsing."""

    def test_dublin_gridref(self):
        """Test grid reference for Dublin area."""
        e, n = 316200, 234000

        gridref = eastings_northings_to_irish_gridref(e, n)

        # Dublin is in the O grid square
        assert gridref.startswith("O"), f"Expected O grid square, got: {gridref}"
        assert gridref == "O 16200 34000", f"Unexpected gridref: {gridref}"

    def test_belfast_gridref(self):
        """Test grid reference for Belfast area."""
        e, n = 334000, 373000

        gridref = eastings_northings_to_irish_gridref(e, n)

        # Belfast is in the J grid square
        assert gridref.startswith("J"), f"Expected J grid square, got: {gridref}"
        assert gridref == "J 34000 73000", f"Unexpected gridref: {gridref}"

    def test_galway_gridref(self):
        """Test grid reference for Galway (west coast)."""
        e, n = 131000, 225000

        gridref = eastings_northings_to_irish_gridref(e, n)

        # Galway is in the M grid square
        assert gridref.startswith("M"), f"Expected M grid square, got: {gridref}"
        assert gridref == "M 31000 25000", f"Unexpected gridref: {gridref}"

    def test_cork_gridref(self):
        """Test grid reference for Cork area (south)."""
        e, n = 167000, 72000

        gridref = eastings_northings_to_irish_gridref(e, n)

        # Cork is in the W grid square
        assert gridref.startswith("W"), f"Expected W grid square, got: {gridref}"
        assert gridref == "W 67000 72000", f"Unexpected gridref: {gridref}"

    def test_invalid_irish_coordinates_raises(self):
        """Test that coordinates outside Irish Grid raise ValueError."""
        # Way outside Irish Grid (> 500km)
        with pytest.raises(ValueError, match="outside the Irish Grid"):
            eastings_northings_to_irish_gridref(600000, 300000)

        # Negative coordinates
        with pytest.raises(ValueError, match="outside the Irish Grid"):
            eastings_northings_to_irish_gridref(-100, 100000)

    def test_parse_irish_gridref_dublin(self):
        """Test parsing Irish grid reference for Dublin."""
        gridref = "O 16200 34000"

        e, n = irish_gridref_to_eastings_northings(gridref)

        assert e == 316200, f"Eastings {e} should be 316200"
        assert n == 234000, f"Northings {n} should be 234000"

    def test_parse_irish_gridref_belfast(self):
        """Test parsing Irish grid reference for Belfast."""
        gridref = "J 34000 73000"

        e, n = irish_gridref_to_eastings_northings(gridref)

        assert e == 334000, f"Eastings {e} should be 334000"
        assert n == 373000, f"Northings {n} should be 373000"

    def test_parse_irish_gridref_no_spaces(self):
        """Test parsing Irish grid reference without spaces."""
        gridref = "O1620034000"

        e, n = irish_gridref_to_eastings_northings(gridref)

        assert e == 316200, f"Eastings {e} should be 316200"
        assert n == 234000, f"Northings {n} should be 234000"

    def test_parse_irish_gridref_4_digit(self):
        """Test parsing 4-digit Irish grid reference."""
        gridref = "O 1620 3400"

        e, n = irish_gridref_to_eastings_northings(gridref)

        assert e == 316200, f"Eastings {e} should be 316200"
        assert n == 234000, f"Northings {n} should be 234000"

    def test_parse_invalid_irish_gridref_raises(self):
        """Test that invalid grid references raise ValueError."""
        # Invalid letter (I is not used in Irish Grid)
        with pytest.raises(ValueError):
            irish_gridref_to_eastings_northings("I 12345 67890")

        # OSGB-style two-letter grid reference
        with pytest.raises(ValueError):
            irish_gridref_to_eastings_northings("TQ 12345 67890")


class TestGridRefRecognition:
    """Tests for recognising OSGB vs Irish grid references."""

    def test_is_irish_gridref_valid(self):
        """Test recognition of valid Irish grid references."""
        assert is_irish_gridref("O 16200 34000") is True
        assert is_irish_gridref("J 34000 73000") is True
        assert is_irish_gridref("M3100025000") is True
        assert is_irish_gridref("W 67000 72000") is True
        assert is_irish_gridref("A 12345 67890") is True
        assert is_irish_gridref("Z 00000 00000") is True

    def test_is_irish_gridref_invalid(self):
        """Test rejection of non-Irish grid references."""
        # OSGB two-letter references
        assert is_irish_gridref("TQ 12345 67890") is False
        assert is_irish_gridref("NT 25200 73400") is False
        assert is_irish_gridref("NL 70095 98813") is False

        # Letter I is not used in Irish Grid
        assert is_irish_gridref("I 12345 67890") is False

        # Odd number of digits (invalid format)
        assert is_irish_gridref("O 123") is False

        # Not a grid reference
        assert is_irish_gridref("Dublin") is False
        assert is_irish_gridref("") is False

    def test_is_osgb_gridref_valid(self):
        """Test recognition of valid OSGB grid references."""
        assert is_osgb_gridref("TQ 30005 80433") is True
        assert is_osgb_gridref("NT 25200 73400") is True
        assert is_osgb_gridref("NL 70095 98813") is True
        assert is_osgb_gridref("SW 15000 05000") is True
        assert is_osgb_gridref("TQ3000580433") is True

    def test_is_osgb_gridref_invalid(self):
        """Test rejection of non-OSGB grid references."""
        # Irish single-letter references
        assert is_osgb_gridref("O 16200 34000") is False
        assert is_osgb_gridref("J 34000 73000") is False

        # Odd number of digits (invalid format)
        assert is_osgb_gridref("TQ 123") is False

        # Not a grid reference
        assert is_osgb_gridref("London") is False
        assert is_osgb_gridref("") is False

    def test_ambiguous_cases(self):
        """Test that OSGB and Irish grid refs are distinguished correctly."""
        # Irish grid ref (single letter O)
        assert is_irish_gridref("O1234567890") is True
        assert is_osgb_gridref("O1234567890") is False

        # OSGB grid ref (two letters starting with O)
        assert is_irish_gridref("OT1234567890") is False
        assert is_osgb_gridref("OT1234567890") is True


class TestParseIrishGridref:
    """Tests for the parse_irish_gridref function."""

    def test_parse_dublin(self):
        """Test parsing Dublin grid reference to lat/lon."""
        result = parse_irish_gridref("O 16200 34000")

        assert result is not None
        lat, lon, normalized = result

        # Dublin is approximately lat=53.35, lon=-6.26
        assert 53.3 < lat < 53.4, f"Latitude {lat} outside expected range"
        assert -6.3 < lon < -6.2, f"Longitude {lon} outside expected range"
        assert normalized == "O 16200 34000"

    def test_parse_invalid_returns_none(self):
        """Test that invalid grid references return None."""
        assert parse_irish_gridref("TQ 12345 67890") is None  # OSGB
        assert parse_irish_gridref("Invalid") is None
        assert parse_irish_gridref("") is None
