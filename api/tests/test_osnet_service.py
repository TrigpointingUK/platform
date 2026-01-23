"""
Tests for the OS Net comparison service.

Tests parsing, caching, and comparison logic for OS Net active station data.
"""

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest

from api.services.osnet_service import (
    COORDINATE_TOLERANCE_METRES,
    SECTION_CURRENT,
    SECTION_DESTROYED,
    SECTION_LEGACY,
    ActiveStationDB,
    OSNetCache,
    calculate_distance,
    compare_osnet_with_db,
    fetch_osnet_file,
    parse_osnet_file,
)


class TestParseOSNetFile:
    """Tests for parse_osnet_file function."""

    def test_parse_single_station(self):
        """Test parsing a single station entry."""
        content = """# Header comment
THUR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,299721.880,967202.983,46.005,Newlyn,02,NC9967,0.0000
"""
        stations, changelog = parse_osnet_file(content)

        assert len(stations) == 1
        assert stations[0].code == "THUR"
        assert stations[0].easting == pytest.approx(299721.880)
        assert stations[0].northing == pytest.approx(967202.983)
        assert stations[0].gridref == "NC9967"
        assert stations[0].height == pytest.approx(46.005)
        assert stations[0].lat_dms == "N 58 34 52.336404"
        assert stations[0].lon_dms == "W 003 43 34.716720"
        assert stations[0].datum == "Newlyn"
        assert stations[0].section == SECTION_CURRENT

    def test_parse_multiple_stations(self):
        """Test parsing multiple station entries."""
        content = """# Part (i) - Current stations
THUR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,299721.880,967202.983,46.005,Newlyn,02,NC9967,0.0000
ULLA,3384245.4624,-305571.0692,5379585.0995,N 57 53 41.894037,W 005 09 33.743264,65.3694,212840.563,893882.898,10.317,Newlyn,02,NH1293,0.0000
"""
        stations, changelog = parse_osnet_file(content)

        assert len(stations) == 2
        assert stations[0].code == "THUR"
        assert stations[1].code == "ULLA"

    def test_parse_section_detection_current(self):
        """Test that Part (i) section is correctly detected."""
        content = """# Part (i) - Current OS Net v2009 stations
THUR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,299721.880,967202.983,46.005,Newlyn,02,NC9967,0.0000
"""
        stations, _ = parse_osnet_file(content)

        assert len(stations) == 1
        assert stations[0].section == SECTION_CURRENT

    def test_parse_section_detection_legacy(self):
        """Test that Part (ii) section is correctly detected."""
        content = """# Part (i) - Current stations
CURR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,100000.000,200000.000,46.005,Newlyn,02,NC9967,0.0000
# Part (ii) - Legacy OS Net v2001 stations
LEGC,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,300000.000,400000.000,46.005,Newlyn,02,NC9967,0.0000
"""
        stations, _ = parse_osnet_file(content)

        assert len(stations) == 2
        assert stations[0].code == "CURR"
        assert stations[0].section == SECTION_CURRENT
        assert stations[1].code == "LEGC"
        assert stations[1].section == SECTION_LEGACY

    def test_parse_section_detection_destroyed(self):
        """Test that Part (iii) section is correctly detected."""
        content = """# Part (i) - Current stations
CURR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,100000.000,200000.000,46.005,Newlyn,02,NC9967,0.0000
# Part (iii) - Destroyed or Moved stations
DEST,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,300000.000,400000.000,46.005,Newlyn,02,NC9967,0.0000
"""
        stations, _ = parse_osnet_file(content)

        assert len(stations) == 2
        assert stations[0].code == "CURR"
        assert stations[0].section == SECTION_CURRENT
        assert stations[1].code == "DEST"
        assert stations[1].section == SECTION_DESTROYED

    def test_parse_all_three_sections(self):
        """Test parsing a file with all three sections."""
        content = """# Part (i) - Current OS Net v2009 stations
STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
STN2,0,0,0,N 50 00 00,W 001 00 00,100,100001.000,200001.000,50,Newlyn,02,AA0001,0.0
# Part (ii) - Legacy OS Net v2001 coordinates
LEG1,0,0,0,N 50 00 00,W 001 00 00,100,300000.000,400000.000,50,Newlyn,02,BB0000,0.0
# Part (iii) - Destroyed or Moved stations
OLD1,0,0,0,N 50 00 00,W 001 00 00,100,500000.000,600000.000,50,Newlyn,02,CC0000,0.0
OLD2,0,0,0,N 50 00 00,W 001 00 00,100,500001.000,600001.000,50,Newlyn,02,CC0001,0.0
"""
        stations, _ = parse_osnet_file(content)

        assert len(stations) == 5

        current = [s for s in stations if s.section == SECTION_CURRENT]
        legacy = [s for s in stations if s.section == SECTION_LEGACY]
        destroyed = [s for s in stations if s.section == SECTION_DESTROYED]

        assert len(current) == 2
        assert len(legacy) == 1
        assert len(destroyed) == 2

    def test_parse_changelog_extraction(self):
        """Test that changelog entries are extracted from comments."""
        content = """# 2026-01-15. New station WALL added.
# 2025-12-18. Station TEST removed.
# Some other comment without date
THUR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,299721.880,967202.983,46.005,Newlyn,02,NC9967,0.0000
"""
        stations, changelog = parse_osnet_file(content)

        assert len(changelog) == 2
        assert "2026-01-15. New station WALL added." in changelog
        assert "2025-12-18. Station TEST removed." in changelog

    def test_parse_skips_empty_lines(self):
        """Test that empty lines are skipped."""
        content = """

THUR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,299721.880,967202.983,46.005,Newlyn,02,NC9967,0.0000

"""
        stations, _ = parse_osnet_file(content)

        assert len(stations) == 1

    def test_parse_skips_malformed_lines(self):
        """Test that malformed lines are skipped."""
        content = """# Header
THUR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,299721.880,967202.983,46.005,Newlyn,02,NC9967,0.0000
malformed line with not enough fields
ULLA,3384245.4624,-305571.0692,5379585.0995,N 57 53 41.894037,W 005 09 33.743264,65.3694,212840.563,893882.898,10.317,Newlyn,02,NH1293,0.0000
"""
        stations, _ = parse_osnet_file(content)

        assert len(stations) == 2
        assert stations[0].code == "THUR"
        assert stations[1].code == "ULLA"

    def test_parse_skips_header_rows(self):
        """Test that header rows (STATION, CODE, NAME) are skipped."""
        content = """STATION,X,Y,Z,LAT,LON,H,EASTING,NORTHING,ORTHO,DATUM,ORDER,GRIDREF,ANT
THUR,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,299721.880,967202.983,46.005,Newlyn,02,NC9967,0.0000
"""
        stations, _ = parse_osnet_file(content)

        assert len(stations) == 1
        assert stations[0].code == "THUR"

    def test_parse_handles_invalid_numbers(self):
        """Test that lines with invalid numbers are skipped."""
        content = """GOOD,3325995.9521,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,299721.880,967202.983,46.005,Newlyn,02,NC9967,0.0000
BAD1,invalid,-216616.2387,5419847.7932,N 58 34 52.336404,W 003 43 34.716720,98.6279,invalid,invalid,46.005,Newlyn,02,NC9967,0.0000
"""
        stations, _ = parse_osnet_file(content)

        assert len(stations) == 1
        assert stations[0].code == "GOOD"

    def test_parse_section_marker_case_insensitive(self):
        """Test that section markers are detected case-insensitively."""
        content = """# PART (I) - Current stations
STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
# PART (II) - Legacy stations
STN2,0,0,0,N 50 00 00,W 001 00 00,100,200000.000,300000.000,50,Newlyn,02,BB0000,0.0
# PART (III) - Destroyed stations
STN3,0,0,0,N 50 00 00,W 001 00 00,100,300000.000,400000.000,50,Newlyn,02,CC0000,0.0
"""
        stations, _ = parse_osnet_file(content)

        assert stations[0].section == SECTION_CURRENT
        assert stations[1].section == SECTION_LEGACY
        assert stations[2].section == SECTION_DESTROYED

    def test_parse_section_marker_without_space(self):
        """Test that section markers without spaces are detected (part(i) vs part (i))."""
        content = """# part(i) - Current stations
STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
# part(iii) - Destroyed stations
STN2,0,0,0,N 50 00 00,W 001 00 00,100,300000.000,400000.000,50,Newlyn,02,CC0000,0.0
"""
        stations, _ = parse_osnet_file(content)

        assert stations[0].section == SECTION_CURRENT
        assert stations[1].section == SECTION_DESTROYED


class TestCalculateDistance:
    """Tests for calculate_distance function."""

    def test_zero_distance(self):
        """Test that identical points have zero distance."""
        dist = calculate_distance(100.0, 200.0, 100.0, 200.0)
        assert dist == pytest.approx(0.0)

    def test_horizontal_distance(self):
        """Test horizontal distance calculation."""
        dist = calculate_distance(0.0, 0.0, 3.0, 0.0)
        assert dist == pytest.approx(3.0)

    def test_vertical_distance(self):
        """Test vertical distance calculation."""
        dist = calculate_distance(0.0, 0.0, 0.0, 4.0)
        assert dist == pytest.approx(4.0)

    def test_diagonal_distance(self):
        """Test diagonal distance (3-4-5 triangle)."""
        dist = calculate_distance(0.0, 0.0, 3.0, 4.0)
        assert dist == pytest.approx(5.0)

    def test_negative_coordinates(self):
        """Test with negative coordinates."""
        dist = calculate_distance(-10.0, -10.0, -7.0, -6.0)
        assert dist == pytest.approx(5.0)

    def test_realistic_coordinates(self):
        """Test with realistic OSGB coordinates (small difference)."""
        # 1.5m east, 2m north = sqrt(1.5^2 + 2^2) = sqrt(2.25 + 4) = sqrt(6.25) = 2.5m
        dist = calculate_distance(299721.880, 967202.983, 299723.380, 967204.983)
        assert dist == pytest.approx(2.5, rel=0.01)


class TestOSNetCache:
    """Tests for OSNetCache class."""

    def setup_method(self):
        """Clear cache before each test."""
        cache = OSNetCache.get_instance()
        cache.clear()

    def test_singleton_pattern(self):
        """Test that get_instance returns the same instance."""
        cache1 = OSNetCache.get_instance()
        cache2 = OSNetCache.get_instance()
        assert cache1 is cache2

    def test_empty_cache_returns_none(self):
        """Test that empty cache returns None."""
        cache = OSNetCache.get_instance()
        assert cache.get_cached_data() is None

    def test_set_and_get_data(self):
        """Test setting and retrieving cached data."""
        cache = OSNetCache.get_instance()
        cache.set_data("test content")

        result = cache.get_cached_data()
        assert result is not None
        content, fetch_time = result
        assert content == "test content"
        assert isinstance(fetch_time, datetime)

    def test_clear_cache(self):
        """Test clearing the cache."""
        cache = OSNetCache.get_instance()
        cache.set_data("test content")
        cache.clear()
        assert cache.get_cached_data() is None

    def test_cache_expiry(self):
        """Test that expired cache returns None."""
        cache = OSNetCache.get_instance()
        cache.set_data("test content")

        # Manually set fetch time to past
        cache._fetch_time = datetime.now() - timedelta(hours=2)

        assert cache.get_cached_data() is None


class TestFetchOSNetFile:
    """Tests for fetch_osnet_file function."""

    def setup_method(self):
        """Clear cache before each test."""
        OSNetCache.get_instance().clear()

    def test_fetch_with_cache_hit(self):
        """Test that cached data is returned when available."""
        cache = OSNetCache.get_instance()
        cache.set_data("cached content")

        content, fetch_time = fetch_osnet_file(force_refresh=False)

        assert content == "cached content"

    @patch("api.services.osnet_service.httpx.Client")
    def test_fetch_with_cache_miss(self, mock_client_class):
        """Test that fresh data is fetched when cache is empty."""
        mock_response = MagicMock()
        mock_response.text = "fresh content"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        content, fetch_time = fetch_osnet_file(force_refresh=False)

        assert content == "fresh content"
        mock_client.get.assert_called_once()

    @patch("api.services.osnet_service.httpx.Client")
    def test_fetch_force_refresh_bypasses_cache(self, mock_client_class):
        """Test that force_refresh bypasses the cache."""
        cache = OSNetCache.get_instance()
        cache.set_data("cached content")

        mock_response = MagicMock()
        mock_response.text = "fresh content"
        mock_response.raise_for_status = MagicMock()

        mock_client = MagicMock()
        mock_client.get.return_value = mock_response
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        content, fetch_time = fetch_osnet_file(force_refresh=True)

        assert content == "fresh content"
        mock_client.get.assert_called_once()

    @patch("api.services.osnet_service.httpx.Client")
    def test_fetch_http_error_raises_runtime_error(self, mock_client_class):
        """Test that HTTP errors are converted to RuntimeError."""
        import httpx

        mock_client = MagicMock()
        mock_client.get.side_effect = httpx.HTTPError("Connection failed")
        mock_client.__enter__ = MagicMock(return_value=mock_client)
        mock_client.__exit__ = MagicMock(return_value=False)
        mock_client_class.return_value = mock_client

        with pytest.raises(RuntimeError, match="Failed to fetch OS Net"):
            fetch_osnet_file(force_refresh=True)


class TestCompareOSNetWithDB:
    """Tests for compare_osnet_with_db function using mocked data."""

    @pytest.fixture
    def mock_osnet_content(self):
        """Sample OS Net file content for testing."""
        return """# 2026-01-15. New station TEST added.
# Part (i) - Current OS Net v2009 stations
STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
STN2,0,0,0,N 50 00 00,W 001 00 00,100,100010.000,200010.000,50,Newlyn,02,AA0001,0.0
# Part (iii) - Destroyed stations
DEST,0,0,0,N 50 00 00,W 001 00 00,100,300000.000,400000.000,50,Newlyn,02,CC0000,0.0
"""

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_all_matched(self, mock_get_db, mock_fetch, mock_osnet_content):
        """Test comparison when all stations match."""
        mock_fetch.return_value = (mock_osnet_content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station 1",
                stn_number_active="STN1",
                osgb_eastings=100000,
                osgb_northings=200000,
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
            ActiveStationDB(
                trig_id=2,
                waypoint="TP0002",
                name="Station 2",
                stn_number_active="STN2",
                osgb_eastings=100010,
                osgb_northings=200010,
                osgb_gridref="AA0001",
                osgb_height=50,
            ),
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        assert result.matched_count == 2
        assert result.osnet_current_count == 2
        assert result.osnet_destroyed_count == 1

        # Should only have the destroyed station difference
        diffs_by_type = {d.difference_type: d for d in result.differences}
        assert "destroyed_not_in_db" in diffs_by_type
        assert "new_in_osnet" not in diffs_by_type

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_new_in_osnet(self, mock_get_db, mock_fetch, mock_osnet_content):
        """Test detection of new stations in OS Net."""
        mock_fetch.return_value = (mock_osnet_content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station 1",
                stn_number_active="STN1",
                osgb_eastings=100000,
                osgb_northings=200000,
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
            # STN2 is missing from DB
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        new_diffs = [
            d for d in result.differences if d.difference_type == "new_in_osnet"
        ]
        assert len(new_diffs) == 1
        assert new_diffs[0].station_code == "STN2"
        assert new_diffs[0].osnet_section == SECTION_CURRENT

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_missing_from_osnet(
        self, mock_get_db, mock_fetch, mock_osnet_content
    ):
        """Test detection of stations missing from OS Net."""
        mock_fetch.return_value = (mock_osnet_content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station 1",
                stn_number_active="STN1",
                osgb_eastings=100000,
                osgb_northings=200000,
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
            ActiveStationDB(
                trig_id=99,
                waypoint="TP0099",
                name="Missing Station",
                stn_number_active="MISS",  # Not in OS Net
                osgb_eastings=500000,
                osgb_northings=600000,
                osgb_gridref="ZZ9999",
                osgb_height=100,
            ),
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        missing_diffs = [
            d for d in result.differences if d.difference_type == "missing_from_osnet"
        ]
        assert len(missing_diffs) == 1
        assert missing_diffs[0].station_code == "MISS"

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_coordinate_mismatch(self, mock_get_db, mock_fetch):
        """Test detection of coordinate mismatches."""
        content = """STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
"""
        mock_fetch.return_value = (content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station 1",
                stn_number_active="STN1",
                osgb_eastings=100005,  # 5m difference
                osgb_northings=200005,  # 5m difference
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        mismatch_diffs = [
            d for d in result.differences if d.difference_type == "coordinate_mismatch"
        ]
        assert len(mismatch_diffs) == 1
        assert mismatch_diffs[0].station_code == "STN1"
        # Distance should be sqrt(25+25) = ~7.07m
        assert mismatch_diffs[0].distance_metres > COORDINATE_TOLERANCE_METRES

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_within_tolerance(self, mock_get_db, mock_fetch):
        """Test that small coordinate differences within tolerance are not flagged."""
        content = """STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
"""
        mock_fetch.return_value = (content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station 1",
                stn_number_active="STN1",
                osgb_eastings=100001,  # 1m difference
                osgb_northings=200001,  # 1m difference
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        mismatch_diffs = [
            d for d in result.differences if d.difference_type == "coordinate_mismatch"
        ]
        assert len(mismatch_diffs) == 0
        assert result.matched_count == 1

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_unmatched_db_no_station_code(self, mock_get_db, mock_fetch):
        """Test detection of DB stations without stn_number_active."""
        content = """STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
"""
        mock_fetch.return_value = (content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station Without Code",
                stn_number_active=None,  # No station code
                osgb_eastings=100000,
                osgb_northings=200000,
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        unmatched_diffs = [
            d for d in result.differences if d.difference_type == "unmatched_db"
        ]
        assert len(unmatched_diffs) == 1
        assert "Station Without Code" in unmatched_diffs[0].description

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_unmatched_db_empty_station_code(self, mock_get_db, mock_fetch):
        """Test detection of DB stations with empty stn_number_active."""
        content = """STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
"""
        mock_fetch.return_value = (content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station With Empty Code",
                stn_number_active="   ",  # Empty/whitespace
                osgb_eastings=100000,
                osgb_northings=200000,
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        unmatched_diffs = [
            d for d in result.differences if d.difference_type == "unmatched_db"
        ]
        assert len(unmatched_diffs) == 1

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_destroyed_not_in_db(
        self, mock_get_db, mock_fetch, mock_osnet_content
    ):
        """Test that destroyed stations not in DB are flagged correctly."""
        mock_fetch.return_value = (mock_osnet_content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station 1",
                stn_number_active="STN1",
                osgb_eastings=100000,
                osgb_northings=200000,
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
            ActiveStationDB(
                trig_id=2,
                waypoint="TP0002",
                name="Station 2",
                stn_number_active="STN2",
                osgb_eastings=100010,
                osgb_northings=200010,
                osgb_gridref="AA0001",
                osgb_height=50,
            ),
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        destroyed_diffs = [
            d for d in result.differences if d.difference_type == "destroyed_not_in_db"
        ]
        assert len(destroyed_diffs) == 1
        assert destroyed_diffs[0].station_code == "DEST"
        assert destroyed_diffs[0].osnet_section == SECTION_DESTROYED

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_case_insensitive_matching(self, mock_get_db, mock_fetch):
        """Test that station code matching is case-insensitive."""
        content = """STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
"""
        mock_fetch.return_value = (content, datetime.now())
        mock_get_db.return_value = [
            ActiveStationDB(
                trig_id=1,
                waypoint="TP0001",
                name="Station 1",
                stn_number_active="stn1",  # lowercase
                osgb_eastings=100000,
                osgb_northings=200000,
                osgb_gridref="AA0000",
                osgb_height=50,
            ),
        ]

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        assert result.matched_count == 1
        new_diffs = [
            d for d in result.differences if d.difference_type == "new_in_osnet"
        ]
        assert len(new_diffs) == 0

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_changelog_limited(self, mock_get_db, mock_fetch):
        """Test that changelog entries are limited to 20."""
        changelog_lines = "\n".join(
            [f"# 2026-01-{i:02d}. Entry {i}" for i in range(1, 26)]
        )
        content = f"""{changelog_lines}
STN1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
"""
        mock_fetch.return_value = (content, datetime.now())
        mock_get_db.return_value = []

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        assert len(result.changelog_entries) == 20

    @patch("api.services.osnet_service.fetch_osnet_file")
    @patch("api.services.osnet_service.get_active_stations_from_db")
    def test_compare_differences_sorted(self, mock_get_db, mock_fetch):
        """Test that differences are sorted by type then code."""
        content = """# Part (i)
ZZZ1,0,0,0,N 50 00 00,W 001 00 00,100,100000.000,200000.000,50,Newlyn,02,AA0000,0.0
AAA1,0,0,0,N 50 00 00,W 001 00 00,100,100010.000,200010.000,50,Newlyn,02,AA0001,0.0
"""
        mock_fetch.return_value = (content, datetime.now())
        mock_get_db.return_value = []

        mock_db = MagicMock()
        result = compare_osnet_with_db(mock_db)

        # Both should be "new_in_osnet", sorted alphabetically
        new_diffs = [
            d for d in result.differences if d.difference_type == "new_in_osnet"
        ]
        assert len(new_diffs) == 2
        assert new_diffs[0].station_code == "AAA1"
        assert new_diffs[1].station_code == "ZZZ1"
