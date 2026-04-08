"""
Tests for county lookup functions in export_formats and area CRUD.

These tests cover the county lookup functionality that uses the trig_area table
and spatial point-in-polygon queries. Since SQLite doesn't support PostGIS or
the trig_area table, we use mocking to test all code paths including
PostgreSQL-specific ones.
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
        mock_db.query.assert_not_called()

    def test_with_mock_postgres_and_results(self):
        """Test successful county lookup with mocked PostgreSQL database."""
        mock_db = MagicMock()

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["trig_area", "area"]

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
        mock_inspector.get_table_names.return_value = ["area", "trig"]

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = export_formats.get_county_names_for_trigs(mock_db, [1, 2, 3])

        assert result == {}
        mock_db.query.assert_not_called()

    def test_with_exception_during_inspect(self):
        """Test that exception during inspection returns empty dict."""
        mock_db = MagicMock()

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.side_effect = Exception("Inspection failed")
            result = export_formats.get_county_names_for_trigs(mock_db, [1, 2, 3])

        assert result == {}


class TestGetCountyNamesForTrigsAreaCrud:
    """Tests for area_crud.get_county_names_for_trigs (canonical location)."""

    def test_empty_trig_ids_returns_empty_dict(self):
        """Test that empty list returns empty dict without querying."""
        mock_db = MagicMock()
        result = area_crud.get_county_names_for_trigs(mock_db, [])
        assert result == {}
        mock_db.query.assert_not_called()

    def test_sqlite_returns_empty_dict(self):
        """Test that SQLite database returns empty dict."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"
        result = area_crud.get_county_names_for_trigs(mock_db, [1, 2])
        assert result == {}

    def test_with_mock_postgres_and_results(self):
        """Test batch county lookup returns correct mapping."""
        mock_db = MagicMock()

        mock_inspector = MagicMock()
        mock_inspector.get_table_names.return_value = ["trig_area", "area"]

        mock_result = [(10, "Derbyshire"), (20, "Staffordshire")]
        mock_query = MagicMock()
        mock_query.join.return_value = mock_query
        mock_query.filter.return_value = mock_query
        mock_query.all.return_value = mock_result
        mock_db.query.return_value = mock_query

        with patch("sqlalchemy.inspect") as mock_inspect:
            mock_inspect.return_value = mock_inspector
            result = area_crud.get_county_names_for_trigs(mock_db, [10, 20, 30])

        assert result == {10: "Derbyshire", 20: "Staffordshire"}
        assert 30 not in result


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


class TestGetCountyNameForPoint:
    """Tests for get_county_name_for_point spatial lookup."""

    def test_sqlite_returns_none(self):
        """Test that SQLite database returns None."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"

        result = area_crud.get_county_name_for_point(mock_db, 51.5, -0.1)
        assert result is None

    def test_with_mock_postgres_found(self):
        """Test successful spatial county lookup."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = ("Hertfordshire",)
        mock_db.query.return_value = mock_query

        result = area_crud.get_county_name_for_point(mock_db, 51.75, -0.34)
        assert result == "Hertfordshire"

    def test_with_mock_postgres_not_found(self):
        """Test spatial lookup when point is not in any county."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        mock_query = MagicMock()
        mock_query.filter.return_value = mock_query
        mock_query.first.return_value = None
        mock_db.query.return_value = mock_query

        result = area_crud.get_county_name_for_point(mock_db, 0.0, 0.0)
        assert result is None

    def test_with_exception_returns_none(self):
        """Test that database exceptions return None gracefully."""
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"
        mock_db.query.side_effect = Exception("PostGIS error")

        result = area_crud.get_county_name_for_point(mock_db, 51.5, -0.1)
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


class TestSearchLocationHelpers:
    """Tests for search result helper functions in the locations endpoint."""

    def _make_mock_trig(
        self,
        id: int = 1,
        waypoint: str = "TP0001",
        name: str = "Test Trig",
        town: str = "ST ALBANS",
        wgs_lat: float = 51.75,
        wgs_long: float = -0.34,
        type_name: str = "Pillar",
        category_code: str = "PILLAR",
        fb_number: str = "",
        stn_number_active: str = "",
        stn_number_passive: str = "",
        stn_number_osgb36: str = "",
    ) -> MagicMock:
        """Create a mock Trig for search helper tests."""
        mock_trig = MagicMock()
        mock_trig.id = id
        mock_trig.waypoint = waypoint
        mock_trig.name = name
        mock_trig.town = town
        mock_trig.wgs_lat = wgs_lat
        mock_trig.wgs_long = wgs_long
        mock_trig.fb_number = fb_number
        mock_trig.stn_number_active = stn_number_active
        mock_trig.stn_number_passive = stn_number_passive
        mock_trig.stn_number_osgb36 = stn_number_osgb36

        mock_category = MagicMock()
        mock_category.code = category_code
        mock_type = MagicMock()
        mock_type.name = type_name
        mock_type.category = mock_category
        mock_trig.trig_type = mock_type

        return mock_trig

    def test_trig_description_with_waypoint_and_type(self):
        """Test description contains waypoint and type name."""
        from api.api.v1.endpoints.locations import _trig_description

        trig = self._make_mock_trig(waypoint="TP1234", type_name="Pillar")
        result = _trig_description(trig)
        assert result == "TP1234 - Pillar"

    def test_trig_description_no_type(self):
        """Test description with waypoint only (no type)."""
        from api.api.v1.endpoints.locations import _trig_description

        trig = self._make_mock_trig(waypoint="TP1234")
        trig.trig_type = None
        result = _trig_description(trig)
        assert result == "TP1234"

    def test_trig_description_fallback(self):
        """Test description falls back to 'Trigpoint' when no data."""
        from api.api.v1.endpoints.locations import _trig_description

        trig = self._make_mock_trig(waypoint="")
        trig.trig_type = None
        result = _trig_description(trig)
        assert result == "Trigpoint"

    def test_trig_location_title_cases_town(self):
        """Test town name is title-cased (e.g. ST ALBANS -> St Albans)."""
        from api.api.v1.endpoints.locations import _trig_location

        trig = self._make_mock_trig(town="ST ALBANS")
        result = _trig_location(trig, county_name="Hertfordshire")
        assert result == "St Albans, Hertfordshire"

    def test_trig_location_town_only(self):
        """Test location with town but no county."""
        from api.api.v1.endpoints.locations import _trig_location

        trig = self._make_mock_trig(town="WESTMINSTER")
        result = _trig_location(trig, county_name=None)
        assert result == "Westminster"

    def test_trig_location_county_only(self):
        """Test location with county but empty town."""
        from api.api.v1.endpoints.locations import _trig_location

        trig = self._make_mock_trig(town="")
        result = _trig_location(trig, county_name="Greater London")
        assert result == "Greater London"

    def test_trig_location_none_when_empty(self):
        """Test location returns None when no town or county."""
        from api.api.v1.endpoints.locations import _trig_location

        trig = self._make_mock_trig(town="")
        result = _trig_location(trig, county_name=None)
        assert result is None

    def test_trig_category_code(self):
        """Test category code extraction."""
        from api.api.v1.endpoints.locations import _trig_category_code

        trig = self._make_mock_trig(category_code="FBM")
        result = _trig_category_code(trig)
        assert result == "FBM"

    def test_trig_category_code_none_when_no_type(self):
        """Test category code returns None when no type."""
        from api.api.v1.endpoints.locations import _trig_category_code

        trig = self._make_mock_trig()
        trig.trig_type = None
        result = _trig_category_code(trig)
        assert result is None

    def test_station_number_description_fb_match(self):
        """Test station number description shows matched FB number."""
        from api.api.v1.endpoints.locations import _station_number_description

        trig = self._make_mock_trig(waypoint="TP0001", fb_number="S1234")
        result = _station_number_description(trig, "S1234")
        assert "TP0001" in result
        assert "FB: S1234" in result

    def test_station_number_description_fallback(self):
        """Test station number description fallback."""
        from api.api.v1.endpoints.locations import _station_number_description

        trig = self._make_mock_trig(waypoint="")
        result = _station_number_description(trig, "NOMATCH")
        assert result == "Station Number"

    def test_trigs_to_search_results_populates_fields(self):
        """Test _trigs_to_search_results populates location and category_code."""
        from api.api.v1.endpoints.locations import _trigs_to_search_results

        trig = self._make_mock_trig(id=42, town="EDALE", category_code="PILLAR")
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"

        items = _trigs_to_search_results([trig], mock_db)
        assert len(items) == 1
        item = items[0]
        assert item.type == "trigpoint"
        assert item.description == "TP0001 - Pillar"
        assert item.location == "Edale"
        assert item.category_code == "PILLAR"
        assert item.id == "42"

    def test_trigs_to_search_results_skips_invalid(self):
        """Test that trigs with missing fields are skipped."""
        from api.api.v1.endpoints.locations import _trigs_to_search_results

        trig = self._make_mock_trig()
        trig.name = None
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"

        items = _trigs_to_search_results([trig], mock_db)
        assert len(items) == 0

    def test_station_trigs_to_search_results_populates_fields(self):
        """Test _station_trigs_to_search_results populates all new fields."""
        from api.api.v1.endpoints.locations import _station_trigs_to_search_results

        trig = self._make_mock_trig(
            id=99, fb_number="S5678", town="GLOSSOP", category_code="FBM"
        )
        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"

        items = _station_trigs_to_search_results([trig], "S5678", mock_db)
        assert len(items) == 1
        item = items[0]
        assert item.type == "station_number"
        assert "FB: S5678" in item.description
        assert item.location == "Glossop"
        assert item.category_code == "FBM"

    def test_towns_to_search_results_title_cases_name(self):
        """Test town results have title-cased names and UK Town description."""
        from api.api.v1.endpoints.locations import _towns_to_search_results

        mock_town = MagicMock()
        mock_town.name = "ST ALBANS"
        mock_town.wgs_lat = 51.75
        mock_town.wgs_long = -0.34

        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"

        items = _towns_to_search_results([mock_town], mock_db)
        assert len(items) == 1
        assert items[0].name == "St Albans"
        assert items[0].description == "UK Town"
        assert items[0].type == "town"

    def test_towns_to_search_results_with_county(self):
        """Test town results include county when spatial lookup succeeds."""
        from api.api.v1.endpoints.locations import _towns_to_search_results

        mock_town = MagicMock()
        mock_town.name = "WATFORD"
        mock_town.wgs_lat = 51.65
        mock_town.wgs_long = -0.39

        mock_db = MagicMock()
        mock_db.bind.dialect.name = "postgresql"

        with patch.object(
            area_crud, "get_county_name_for_point", return_value="Hertfordshire"
        ):
            items = _towns_to_search_results([mock_town], mock_db)

        assert len(items) == 1
        assert items[0].description == "UK Town - Hertfordshire"

    def test_towns_to_search_results_skips_invalid(self):
        """Test that towns with missing fields are skipped."""
        from api.api.v1.endpoints.locations import _towns_to_search_results

        mock_town = MagicMock()
        mock_town.name = None
        mock_town.wgs_lat = 51.0
        mock_town.wgs_long = -1.0

        mock_db = MagicMock()
        mock_db.bind.dialect.name = "sqlite"

        items = _towns_to_search_results([mock_town], mock_db)
        assert len(items) == 0


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
