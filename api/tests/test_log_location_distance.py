"""
Tests for log location distance calculation.

These tests verify that the distance between a log's location (OSGB coordinates)
and the trig's location (WGS84 coordinates) is calculated accurately using
OSTN15 transformation.
"""

from unittest.mock import MagicMock, patch

from api.services.coordinate_service import convert_osgb_to_wgs84
from api.utils.geodesy import haversine_distance


class TestOSTN15VsHelmert:
    """Tests comparing OSTN15 accuracy vs Helmert transformation."""

    def test_ostn15_more_accurate_than_helmert(self):
        """Verify OSTN15 is significantly more accurate than Helmert.

        Uses official OS test data where we know the correct WGS84 coordinates.
        OSTN15 should be accurate to ~1cm, Helmert to ~5-7m.
        """
        from api.utils.geodesy import osgb_to_wgs84 as helmert_convert

        # Official OS test point (from OSTN15 documentation)
        # OSGB36: 530005.241, 180432.636
        # ETRS89/WGS84: 51.507879, -0.128094
        eastings = 530005.241
        northings = 180432.636
        expected_lat = 51.507879
        expected_lon = -0.128094

        # Convert using OSTN15
        ostn_lon, ostn_lat, _ = convert_osgb_to_wgs84(eastings, northings)

        # Convert using Helmert
        helmert_lat, helmert_lon = helmert_convert(int(eastings), int(northings))

        # Calculate errors (in degrees, ~111km per degree at this latitude)
        ostn_lat_error = abs(ostn_lat - expected_lat)
        ostn_lon_error = abs(ostn_lon - expected_lon)
        helmert_lat_error = abs(helmert_lat - expected_lat)
        helmert_lon_error = abs(helmert_lon - expected_lon)

        # OSTN15 should be much more accurate
        # 0.00001 degrees ≈ 1.1m at UK latitudes
        assert ostn_lat_error < 0.00001, f"OSTN15 lat error {ostn_lat_error} too large"
        assert ostn_lon_error < 0.00001, f"OSTN15 lon error {ostn_lon_error} too large"

        # Helmert should be less accurate (typically 5-7m ≈ 0.00005 degrees)
        # This test ensures we're actually using different transformations
        assert helmert_lat_error > ostn_lat_error, "Helmert should be less accurate"
        assert helmert_lon_error > ostn_lon_error, "Helmert should be less accurate"


class TestLogLocationDistance:
    """Tests for log location distance calculation logic."""

    def test_identical_coordinates_zero_distance(self):
        """When log OSGB converts to same WGS84 as trig, distance should be ~0."""
        # Use a known point where we have both OSGB and WGS84
        # TQ 30005 80433 → approximately 51.5079, -0.1281
        log_eastings = 530005.0
        log_northings = 180433.0

        # Convert log coordinates using OSTN15
        log_lon, log_lat, _ = convert_osgb_to_wgs84(log_eastings, log_northings)

        # Trig coordinates (same as converted log coordinates)
        trig_lat = log_lat
        trig_lon = log_lon

        # Calculate distance
        distance = haversine_distance(log_lat, log_lon, trig_lat, trig_lon)

        assert distance == 0.0, f"Distance should be 0, got {distance}"

    def test_nearby_coordinates_small_distance(self):
        """Log 10m from trig should show ~10m distance."""
        # Trig location (TQ 30005 80433)
        trig_eastings = 530005.0
        trig_northings = 180433.0
        trig_lon, trig_lat, _ = convert_osgb_to_wgs84(trig_eastings, trig_northings)

        # Log location 10m north (TQ 30005 80443)
        log_eastings = 530005.0
        log_northings = 180443.0  # 10m north
        log_lon, log_lat, _ = convert_osgb_to_wgs84(log_eastings, log_northings)

        # Calculate distance
        distance = haversine_distance(log_lat, log_lon, trig_lat, trig_lon)

        # Should be very close to 10m (within 1cm tolerance for OSTN15)
        assert 9.99 < distance < 10.01, f"Distance should be ~10m, got {distance:.2f}m"

    def test_same_gridref_different_precision_minimal_distance(self):
        """Same grid reference at different precisions should give minimal distance.

        This was a bug with Helmert where identical grid refs showed several metres
        difference due to transformation inaccuracy.
        """
        # SD 65113 72134 - trig coordinates
        trig_eastings = 365113.0
        trig_northings = 472134.0
        trig_lon, trig_lat, _ = convert_osgb_to_wgs84(trig_eastings, trig_northings)

        # SD 65113 72134 - log coordinates (same grid ref)
        log_eastings = 365113.0
        log_northings = 472134.0
        log_lon, log_lat, _ = convert_osgb_to_wgs84(log_eastings, log_northings)

        distance = haversine_distance(log_lat, log_lon, trig_lat, trig_lon)

        # Same coordinates should give exactly 0
        assert (
            distance == 0.0
        ), f"Same coordinates should give 0 distance, got {distance}"

    def test_one_metre_apart_shows_one_metre(self):
        """Coordinates 1m apart in OSGB should show ~1m in WGS84 distance."""
        # Base point
        base_eastings = 400000.0
        base_northings = 300000.0
        base_lon, base_lat, _ = convert_osgb_to_wgs84(base_eastings, base_northings)

        # Point 1m east
        east_lon, east_lat, _ = convert_osgb_to_wgs84(base_eastings + 1, base_northings)
        distance_east = haversine_distance(base_lat, base_lon, east_lat, east_lon)

        # Point 1m north
        north_lon, north_lat, _ = convert_osgb_to_wgs84(
            base_eastings, base_northings + 1
        )
        distance_north = haversine_distance(base_lat, base_lon, north_lat, north_lon)

        # Both should be very close to 1m
        assert (
            0.99 < distance_east < 1.01
        ), f"1m east should be ~1m, got {distance_east:.3f}m"
        assert (
            0.99 < distance_north < 1.01
        ), f"1m north should be ~1m, got {distance_north:.3f}m"


class TestEnrichLogsLocationDistance:
    """Tests for the enrich_logs_with_names function's distance calculation."""

    def test_log_with_osgb_coordinates_gets_distance(self):
        """Log with OSGB coordinates should have location_distance_m populated."""
        from api.api.v1.endpoints.logs import enrich_logs_with_names

        # Create mock log with OSGB coordinates
        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.trig_id = 100
        mock_log.user_id = 1
        mock_log.osgb_eastings = 530005.0
        mock_log.osgb_northings = 180433.0
        mock_log.osgb_gridref = "TQ 30005 80433"

        # Create mock trig with WGS84 coordinates (slightly different location)
        mock_trig = MagicMock()
        mock_trig.id = 100
        mock_trig.name = "Test Trig"
        mock_trig.wgs_lat = 51.5080  # Slightly north of log
        mock_trig.wgs_long = -0.1281
        mock_trig.condition = "G"
        mock_trig.type_code = None
        mock_trig.type_name = None
        mock_trig.category_code = None
        mock_trig.category_name = None

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.name = "Test User"

        # Create mock db session
        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.side_effect = [[mock_trig], [mock_user]]
        mock_db.query.return_value = mock_query

        # Mock TLogResponse.model_validate to return a dict-like object
        with patch("api.api.v1.endpoints.logs.TLogResponse") as mock_response:
            mock_validated = MagicMock()
            mock_validated.model_dump.return_value = {
                "id": 1,
                "trig_id": 100,
                "user_id": 1,
                "date": "2024-01-01",
                "time": "12:00:00",
                "condition": "G",
                "comment": "Test",
                "score": 5,
                "osgb_eastings": 530005.0,
                "osgb_northings": 180433.0,
                "osgb_gridref": "TQ 30005 80433",
            }
            mock_response.model_validate.return_value = mock_validated

            result = enrich_logs_with_names(mock_db, [mock_log])

        assert len(result) == 1
        assert "location_distance_m" in result[0]
        assert result[0]["location_distance_m"] is not None
        # Distance should be reasonable (the trig is slightly north of the log)
        assert 0 < result[0]["location_distance_m"] < 100

    def test_log_without_osgb_coordinates_no_distance(self):
        """Log without OSGB coordinates should have location_distance_m = None."""
        from api.api.v1.endpoints.logs import enrich_logs_with_names

        # Create mock log without OSGB coordinates
        mock_log = MagicMock()
        mock_log.id = 1
        mock_log.trig_id = 100
        mock_log.user_id = 1
        mock_log.osgb_eastings = None
        mock_log.osgb_northings = None
        mock_log.osgb_gridref = None

        mock_trig = MagicMock()
        mock_trig.id = 100
        mock_trig.name = "Test Trig"
        mock_trig.wgs_lat = 51.5080
        mock_trig.wgs_long = -0.1281
        mock_trig.condition = "G"
        mock_trig.type_code = None
        mock_trig.type_name = None
        mock_trig.category_code = None
        mock_trig.category_name = None

        mock_user = MagicMock()
        mock_user.id = 1
        mock_user.name = "Test User"

        mock_db = MagicMock()
        mock_query = MagicMock()
        mock_query.outerjoin.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.side_effect = [[mock_trig], [mock_user]]
        mock_db.query.return_value = mock_query

        with patch("api.api.v1.endpoints.logs.TLogResponse") as mock_response:
            mock_validated = MagicMock()
            mock_validated.model_dump.return_value = {
                "id": 1,
                "trig_id": 100,
                "user_id": 1,
                "date": "2024-01-01",
                "time": "12:00:00",
                "condition": "G",
                "comment": "Test",
                "score": 5,
                "osgb_eastings": None,
                "osgb_northings": None,
                "osgb_gridref": None,
            }
            mock_response.model_validate.return_value = mock_validated

            result = enrich_logs_with_names(mock_db, [mock_log])

        assert len(result) == 1
        assert result[0]["location_distance_m"] is None
