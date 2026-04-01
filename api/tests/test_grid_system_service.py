"""
Tests for the grid system classification service.
"""

from unittest.mock import MagicMock

from api.services.grid_system import (
    GB_COUNTRY_CODES,
    IE_COUNTRY_CODES,
    classify_country_for_point,
    classify_country_name_for_point,
    get_country_info_for_point,
    grid_system_for_country_code,
    grid_system_for_point,
)


class TestGridSystemForCountryCode:
    def test_gb_codes(self):
        for code in GB_COUNTRY_CODES:
            assert grid_system_for_country_code(code) == "gb"

    def test_ie_codes(self):
        for code in IE_COUNTRY_CODES:
            assert grid_system_for_country_code(code) == "ie"

    def test_none_code(self):
        assert grid_system_for_country_code(None) is None

    def test_unknown_code(self):
        assert grid_system_for_country_code("XX000") is None


class TestClassifyCountryForPoint:
    def test_returns_code_when_found(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = ("E92000001",)
        result = classify_country_for_point(db, 51.5, -0.1)
        assert result == "E92000001"

    def test_returns_none_when_not_found(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        result = classify_country_for_point(db, 0.0, 0.0)
        assert result is None


class TestClassifyCountryNameForPoint:
    def test_returns_name_when_found(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = ("England",)
        result = classify_country_name_for_point(db, 51.5, -0.1)
        assert result == "England"

    def test_returns_none_when_not_found(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        result = classify_country_name_for_point(db, 0.0, 0.0)
        assert result is None


class TestGridSystemForPoint:
    def test_returns_gb_for_england(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = ("E92000001",)
        result = grid_system_for_point(db, 51.5, -0.1)
        assert result == "gb"

    def test_returns_ie_for_ireland(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = ("IE",)
        result = grid_system_for_point(db, 53.3, -6.3)
        assert result == "ie"

    def test_returns_none_for_unknown_country(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = ("FR",)
        result = grid_system_for_point(db, 48.8, 2.3)
        assert result is None

    def test_returns_none_when_no_country(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        result = grid_system_for_point(db, 0.0, 0.0)
        assert result is None


class TestGetCountryInfoForPoint:
    def test_returns_full_info_for_gb(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = ("S92000003", "Scotland")
        gs, code, name = get_country_info_for_point(db, 56.0, -4.0)
        assert gs == "gb"
        assert code == "S92000003"
        assert name == "Scotland"

    def test_returns_full_info_for_ie(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = (
            "N92000002",
            "Northern Ireland",
        )
        gs, code, name = get_country_info_for_point(db, 54.6, -5.9)
        assert gs == "ie"
        assert code == "N92000002"
        assert name == "Northern Ireland"

    def test_returns_nones_when_not_found(self):
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = None
        gs, code, name = get_country_info_for_point(db, 0.0, 0.0)
        assert gs is None
        assert code is None
        assert name is None
