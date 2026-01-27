"""
Tests for county lookup functions in export_formats and area CRUD.

These tests cover the county lookup functionality that uses the trig_area table.
Since SQLite doesn't support the trig_area table, we use mocking to test
all code paths including PostgreSQL-specific ones.
"""

from unittest.mock import MagicMock, patch

from api.crud import area as area_crud
from api.crud import trig as trig_crud
from api.services import export_formats


class TestGetCountyNamesForTrigs:
    """Tests for get_county_names_for_trigs function."""

    def test_empty_trig_ids_returns_empty_dict(self):
        """Test that empty trig_ids list returns empty dict immediately."""
        mock_db = MagicMock()
        result = export_formats.get_county_names_for_trigs(mock_db, [])
        assert result == {}
        # Ensure no database queries were made
        mock_db.query.assert_not_called()

    def test_with_mock_postgres_and_results(self):
        """Test successful county lookup with mocked PostgreSQL database."""
        mock_db = MagicMock()

        # Mock the inspector to simulate trig_area table exists
        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["trig_area", "area"]

        # Mock query result
        mock_result = [(1, "Greater London"), (2, "Surrey")]
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_result
        mock_db.query.return_value = mock_query

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = export_formats.get_county_names_for_trigs(mock_db, [1, 2, 3])

        assert result == {1: "Greater London", 2: "Surrey"}

    def test_with_mock_postgres_no_trig_area_table(self):
        """Test when trig_area table doesn't exist in PostgreSQL."""
        mock_db = MagicMock()

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["area", "trig"]  # No trig_area

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = export_formats.get_county_names_for_trigs(mock_db, [1, 2, 3])

        assert result == {}
        # Ensure no query was executed after finding table doesn't exist
        mock_db.query.assert_not_called()

    def test_with_exception_during_inspect(self):
        """Test that exception during inspection returns empty dict."""
        mock_db = MagicMock()

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.side_effect = Exception("Inspection failed")
            result = export_formats.get_county_names_for_trigs(mock_db, [1, 2, 3])

        assert result == {}


class TestGetCountyNameForTrig:
    """Tests for get_county_name_for_trig function."""

    def test_sqlite_returns_none(self):
        """Test that SQLite database returns None (no trig_area table)."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"

        result = area_crud.get_county_name_for_trig(mock_db, 1)
        assert result is None

    def test_with_mock_postgres_and_result(self):
        """Test successful county lookup with mocked PostgreSQL database."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["trig_area", "area"]

        mock_result = ("Greater London",)
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = mock_result
        mock_db.query.return_value = mock_query

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = area_crud.get_county_name_for_trig(mock_db, 1)

        assert result == "Greater London"

    def test_with_mock_postgres_no_result(self):
        """Test when trig has no county in trig_area table."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["trig_area", "area"]

        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = area_crud.get_county_name_for_trig(mock_db, 999)

        assert result is None

    def test_with_mock_postgres_no_trig_area_table(self):
        """Test when trig_area table doesn't exist in PostgreSQL."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["area", "trig"]

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = area_crud.get_county_name_for_trig(mock_db, 1)

        assert result is None

    def test_with_exception_during_inspect(self):
        """Test that exception during inspection returns None."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.side_effect = Exception("Inspection failed")
            result = area_crud.get_county_name_for_trig(mock_db, 1)

        assert result is None


class TestTrigAreaTableExists:
    """Tests for _trig_area_table_exists function."""

    def test_sqlite_returns_false(self):
        """Test that SQLite database returns False."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"

        result = trig_crud._trig_area_table_exists(mock_db)
        assert result is False

    def test_with_mock_postgres_table_exists(self):
        """Test when trig_area table exists in PostgreSQL."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["trig_area", "area"]

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = trig_crud._trig_area_table_exists(mock_db)

        assert result is True

    def test_with_mock_postgres_table_not_exists(self):
        """Test when trig_area table doesn't exist in PostgreSQL."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["area", "trig"]

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = trig_crud._trig_area_table_exists(mock_db)

        assert result is False

    def test_with_exception_during_inspect(self):
        """Test that exception during inspection returns False."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.side_effect = Exception("Inspection failed")
            result = trig_crud._trig_area_table_exists(mock_db)

        assert result is False


class TestExportWithCountyNames:
    """Tests for export functions with county_names parameter."""

    def _make_mock_trig(
        self,
        id: int = 1,
        waypoint: str = "TP0001",
        name: str = "Test Trig",
        condition: str = "G",
        status_id: int = 1,
        wgs_lat: float = 51.5074,
        wgs_long: float = -0.1278,
        wgs_height: int = 100,
        osgb_gridref: str = "TQ 30000 80000",
        fb_number: str = "S1234",
        type_code: str = "PILLAR",
        type_name: str = "Pillar",
        category_code: str = "PILLAR",
        category_name: str = "Pillar",
    ) -> MagicMock:
        """Create a mock Trig object for testing."""
        mock_trig = MagicMock()
        mock_trig.id = id
        mock_trig.waypoint = waypoint
        mock_trig.name = name
        mock_trig.condition = condition
        mock_trig.status_id = status_id
        mock_trig.wgs_lat = wgs_lat
        mock_trig.wgs_long = wgs_long
        mock_trig.wgs_height = wgs_height
        mock_trig.osgb_gridref = osgb_gridref
        mock_trig.fb_number = fb_number

        mock_category = MagicMock()
        mock_category.code = category_code
        mock_category.name = category_name
        mock_type = MagicMock()
        mock_type.code = type_code
        mock_type.name = type_name
        mock_type.category = mock_category
        mock_trig.trig_type = mock_type

        return mock_trig

    def test_csv_export_with_county_names(self):
        """Test CSV export includes county names when provided."""
        trig = self._make_mock_trig(id=1)
        county_names = {1: "Greater London"}

        result = export_formats.trigs_to_csv([trig], county_names=county_names)

        assert "Greater London" in result
        assert "county" in result.lower()

    def test_csv_export_without_county_names(self):
        """Test CSV export works without county_names (uses empty string)."""
        trig = self._make_mock_trig(id=1)

        result = export_formats.trigs_to_csv([trig], county_names={})

        # Should still have county column but empty
        assert "county" in result.lower()

    def test_geojson_export_with_county_names(self):
        """Test GeoJSON export includes county names when provided."""
        trig = self._make_mock_trig(id=1)
        county_names = {1: "Greater London"}

        result = export_formats.trigs_to_geojson([trig], county_names=county_names)

        assert result["features"][0]["properties"]["county"] == "Greater London"

    def test_geojson_export_without_county_names(self):
        """Test GeoJSON export works without county_names."""
        trig = self._make_mock_trig(id=1)

        result = export_formats.trigs_to_geojson([trig], county_names={})

        # Should still have county property but empty string
        assert result["features"][0]["properties"]["county"] == ""

    def test_kml_export_with_county_names(self):
        """Test KML export includes county names when provided."""
        trig = self._make_mock_trig(id=1)
        county_names = {1: "Greater London"}

        result = export_formats.trigs_to_kml([trig], county_names=county_names)

        assert "Greater London" in result

    def test_kml_export_without_county_names(self):
        """Test KML export works without county_names."""
        trig = self._make_mock_trig(id=1)

        # Should not raise an error
        result = export_formats.trigs_to_kml([trig], county_names={})
        assert result is not None
        assert "<?xml" in result
