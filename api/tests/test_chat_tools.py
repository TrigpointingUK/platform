"""
Tests for services/chat/tools.py — SQL validation, result formatting, trig lookup.
"""

from unittest.mock import MagicMock, patch

import pytest

from api.services.chat.tools import (
    _format_results,
    _trig_to_dict,
    _validate_sql,
    lookup_trig,
)


class TestValidateSql:
    def test_valid_select(self):
        _validate_sql("SELECT id, name FROM trig LIMIT 10")

    def test_rejects_insert(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("INSERT INTO trig (name) VALUES ('test')")

    def test_rejects_update(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("UPDATE trig SET name = 'x'")

    def test_rejects_delete(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("DELETE FROM trig WHERE id = 1")

    def test_rejects_drop(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("DROP TABLE trig")

    def test_rejects_multiple_statements(self):
        with pytest.raises(ValueError, match="Multiple"):
            _validate_sql("SELECT 1; SELECT 2")

    def test_allows_trailing_semicolon(self):
        _validate_sql("SELECT id FROM trig;")

    def test_rejects_pii_columns(self):
        with pytest.raises(ValueError, match="personal data"):
            _validate_sql('SELECT email FROM "user"')

    def test_rejects_auth0_user_id(self):
        with pytest.raises(ValueError, match="personal data"):
            _validate_sql('SELECT auth0_user_id FROM "user"')

    def test_rejects_firstname(self):
        with pytest.raises(ValueError, match="personal data"):
            _validate_sql('SELECT firstname FROM "user"')

    def test_rejects_non_select(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("EXPLAIN SELECT 1")

    def test_rejects_truncate(self):
        with pytest.raises(ValueError, match="SELECT"):
            _validate_sql("TRUNCATE trig")


class TestFormatResults:
    def test_empty_results(self):
        result = _format_results(["id", "name"], [], "SELECT 1")
        assert "no results" in result

    def test_formats_rows(self):
        result = _format_results(
            ["id", "name"],
            [(1, "Test"), (2, "Other")],
            "SELECT id, name FROM trig",
        )
        assert "1" in result
        assert "Test" in result
        assert "Other" in result

    def test_caps_at_50_rows(self):
        rows = [(i, f"Name {i}") for i in range(100)]
        result = _format_results(["id", "name"], rows, "SELECT 1")
        assert "50 more rows" in result

    def test_handles_none_values(self):
        result = _format_results(["id", "val"], [(1, None)], "SELECT 1")
        assert "NULL" in result


class TestTrigToDict:
    def test_converts_trig_model(self):
        trig = MagicMock()
        trig.waypoint = "TP1234"
        trig.name = "Leith Hill"
        trig.fb_number = "S1234"
        trig.type_name = "Pillar"
        trig.category_name = "Primary"
        trig.condition = "G"
        trig.town = "Dorking"
        trig.wgs_lat = 51.1756
        trig.wgs_long = -0.3754
        trig.osgb_gridref = "TQ 13900 43200"
        trig.historic_use = "Primary"
        trig.current_use = "Passive station"

        result = _trig_to_dict(trig)
        assert result["waypoint"] == "TP1234"
        assert result["name"] == "Leith Hill"
        assert result["wgs_lat"] == 51.1756

    def test_handles_none_coordinates(self):
        trig = MagicMock()
        trig.waypoint = "TP0001"
        trig.name = "Unknown"
        trig.fb_number = None
        trig.type_name = None
        trig.category_name = None
        trig.condition = None
        trig.town = None
        trig.wgs_lat = None
        trig.wgs_long = None
        trig.osgb_gridref = None
        trig.historic_use = None
        trig.current_use = None

        result = _trig_to_dict(trig)
        assert result["wgs_lat"] is None
        assert result["wgs_long"] is None


class TestLookupTrig:
    def test_returns_empty_for_blank_query(self):
        db = MagicMock()
        assert lookup_trig("", db) == []
        assert lookup_trig("   ", db) == []

    @patch("api.services.chat.tools.trig_crud")
    def test_waypoint_exact_match(self, mock_crud):
        db = MagicMock()
        mock_trig = MagicMock()
        mock_trig.waypoint = "TP1234"
        mock_trig.name = "Test"
        mock_trig.fb_number = "FB1"
        mock_trig.type_name = "Pillar"
        mock_trig.category_name = "Primary"
        mock_trig.condition = "G"
        mock_trig.town = "Town"
        mock_trig.wgs_lat = 51.0
        mock_trig.wgs_long = -1.0
        mock_trig.osgb_gridref = "TQ 000 000"
        mock_trig.historic_use = "Primary"
        mock_trig.current_use = "Passive"

        mock_crud.get_trig_by_waypoint.return_value = mock_trig
        results = lookup_trig("TP1234", db)
        assert len(results) == 1
        assert results[0]["waypoint"] == "TP1234"

    @patch("api.services.chat.tools.trig_crud")
    @patch("api.services.chat.tools.locations_crud")
    def test_falls_back_to_name_search(self, mock_loc_crud, mock_trig_crud):
        db = MagicMock()
        mock_trig = MagicMock()
        mock_trig.waypoint = "TP5678"
        mock_trig.name = "Leith Hill"
        mock_trig.fb_number = "S5678"
        mock_trig.type_name = "Pillar"
        mock_trig.category_name = "Primary"
        mock_trig.condition = "G"
        mock_trig.town = "Dorking"
        mock_trig.wgs_lat = 51.17
        mock_trig.wgs_long = -0.37
        mock_trig.osgb_gridref = "TQ 139 432"
        mock_trig.historic_use = "Primary"
        mock_trig.current_use = "Passive"

        mock_loc_crud.search_trigpoints_by_name_or_waypoint.return_value = [mock_trig]
        results = lookup_trig("Leith Hill", db)
        assert len(results) == 1
        assert results[0]["name"] == "Leith Hill"
