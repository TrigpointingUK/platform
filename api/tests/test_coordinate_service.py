"""
Unit tests for the coordinate conversion service.

Tests OSTN15 (horizontal) and OSGM15 (vertical) transformations.
"""

import pytest

from api.services.coordinate_service import (
    convert_osgb_to_wgs84,
    convert_wgs84_to_osgb,
    eastings_northings_to_gridref,
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
