"""
Tests for the pure parsing helpers in api.crud.locations.

These functions (grid-reference and lat/lon string parsing, OSGB→WGS84
conversion) take no database session — the DB-backed search functions are
covered separately in test_locations_search.py.
"""

from unittest.mock import patch

from api.crud import locations
from api.crud.locations import (
    osgb_to_wgs84,
    parse_grid_reference,
    parse_grid_reference_legacy,
    parse_latlon_string,
)


class TestOsgbToWgs84:
    def test_converts_known_point(self):
        # SK 123 456 region — roughly Derbyshire.
        lat, lon = osgb_to_wgs84(412300, 345600)
        assert 52.9 < lat < 53.1
        assert -1.9 < lon < -1.7


class TestParseGridReference:
    def test_parses_osgb(self):
        result = parse_grid_reference("SK123456")
        assert result is not None
        lat, lon, normalized, system = result
        assert system == "gb"
        assert normalized == "SK 12300 45600"
        assert 52.9 < lat < 53.1

    def test_parses_osgb_with_spaces(self):
        result = parse_grid_reference("SK 123 456")
        assert result is not None
        assert result[3] == "gb"

    def test_parses_irish(self):
        result = parse_grid_reference("O123456")
        assert result is not None
        lat, lon, normalized, system = result
        assert system == "ie"
        assert normalized == "O 12300 45600"

    def test_invalid_osgb_letters_returns_none(self):
        # XX passes the regex shape check but is not a real 100km square.
        assert parse_grid_reference("XX123456") is None

    def test_odd_digit_count_returns_none(self):
        assert parse_grid_reference("SK12345") is None

    def test_non_gridref_returns_none(self):
        assert parse_grid_reference("not a gridref") is None

    def test_falls_back_to_helmert_when_ostn15_fails(self):
        with patch.object(
            locations, "convert_osgb_to_wgs84", side_effect=Exception("OSTN15 down")
        ):
            result = parse_grid_reference("SK123456")
        assert result is not None
        # Helmert fallback still yields a sensible GB coordinate.
        assert result[3] == "gb"
        assert 52.9 < result[0] < 53.1


class TestParseGridReferenceLegacy:
    def test_returns_three_tuple_on_success(self):
        result = parse_grid_reference_legacy("SK123456")
        assert result is not None
        assert len(result) == 3

    def test_returns_none_on_invalid(self):
        assert parse_grid_reference_legacy("not a gridref") is None


class TestParseLatlonString:
    def test_comma_separated(self):
        assert parse_latlon_string("51.5, -0.12") == (51.5, -0.12)

    def test_comma_with_nsew(self):
        assert parse_latlon_string("51.5N, 0.12W") == (51.5, -0.12)

    def test_comma_invalid_floats_returns_none(self):
        assert parse_latlon_string("abc, def") is None

    def test_space_separated(self):
        assert parse_latlon_string("51.5 -0.12") == (51.5, -0.12)

    def test_comma_southern_hemisphere_negation(self):
        # Exercises the comma-path 'S' negation (result rejected by bounds).
        assert parse_latlon_string("54.5S, 6.0W") is None

    def test_space_with_nsew(self):
        assert parse_latlon_string("51.5N 0.12W") == (51.5, -0.12)

    def test_space_invalid_floats_returns_none(self):
        assert parse_latlon_string("foo bar") is None

    def test_out_of_bounds_returns_none(self):
        # Valid numbers but well outside the UK/IE window.
        assert parse_latlon_string("10.0, 10.0") is None

    def test_southern_hemisphere_out_of_bounds(self):
        # Exercises the 'S' negation branch (result still rejected by bounds).
        assert parse_latlon_string("54.5S 6.0W") is None

    def test_empty_returns_none(self):
        assert parse_latlon_string("") is None
