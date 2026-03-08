"""
Tests for the Ireland import comparison service.

Tests CSV parsing, proximity matching, field comparison, and data mapping.
"""

from typing import Optional
from unittest.mock import MagicMock, patch

import pytest

from api.services.ireland_import_service import (
    MATCH_THRESHOLD_METRES,
    ORD_TO_HISTORIC_USE,
    CSVRow,
    DBIrishTrig,
    _compare_fields,
    _euclidean_distance,
    _extract_condition_from_notes,
    build_trig_data_from_csv,
    compare_ireland_csv_with_db,
    parse_csv,
)

# ============================================================================
# CSV Parsing Tests
# ============================================================================


class TestParseCSV:
    """Tests for parse_csv function."""

    def test_parse_csv_returns_rows(self):
        """Test that parse_csv returns a non-empty list of rows."""
        rows = parse_csv()
        assert len(rows) > 0

    def test_parse_csv_first_row(self):
        """Test first row is parsed correctly (Lackagh)."""
        rows = parse_csv()
        first = rows[0]
        assert first.row_index == 0
        assert first.station_name == "Lackagh"
        assert first.osi_ni_no == "OSI"
        assert first.eastings == pytest.approx(193100.0)
        assert first.northings == pytest.approx(332100.0)
        assert first.height == pytest.approx(449.0)
        assert first.fb_number == "0004"
        assert first.grid_ref == "G 931 321"
        assert first.order == "U"

    def test_parse_csv_height_unknown(self):
        """Test that height 'H' is parsed as None."""
        rows = parse_csv()
        # Find Dunloy which has "H" for height
        dunloy = [r for r in rows if r.station_name == "Dunloy"]
        assert len(dunloy) == 1
        assert dunloy[0].height is None

    def test_parse_csv_row_count(self):
        """Test the expected number of CSV rows (881 data rows)."""
        rows = parse_csv()
        assert len(rows) == 881

    def test_parse_csv_with_notes(self):
        """Test row with notes column populated."""
        rows = parse_csv()
        # Find Ouley which has "X1" in notes
        ouley = [r for r in rows if r.station_name == "Ouley"]
        assert len(ouley) == 1
        assert ouley[0].notes == "X1"

    def test_parse_csv_decimal_coords(self):
        """Test row with decimal eastings/northings (sub-metre)."""
        rows = parse_csv()
        # Find Dunloy which has sub-metre coords
        dunloy = [r for r in rows if r.station_name == "Dunloy"]
        assert len(dunloy) == 1
        assert dunloy[0].eastings == pytest.approx(300620.953)
        assert dunloy[0].northings == pytest.approx(418392.408)


# ============================================================================
# Distance Calculation Tests
# ============================================================================


class TestEuclideanDistance:
    """Tests for _euclidean_distance function."""

    def test_zero_distance(self):
        """Test distance between identical points is zero."""
        assert _euclidean_distance(100.0, 200.0, 100.0, 200.0) == 0.0

    def test_horizontal_distance(self):
        """Test purely horizontal distance."""
        assert _euclidean_distance(0.0, 0.0, 10.0, 0.0) == pytest.approx(10.0)

    def test_vertical_distance(self):
        """Test purely vertical distance."""
        assert _euclidean_distance(0.0, 0.0, 0.0, 5.0) == pytest.approx(5.0)

    def test_diagonal_distance(self):
        """Test diagonal distance (3-4-5 triangle)."""
        assert _euclidean_distance(0.0, 0.0, 3.0, 4.0) == pytest.approx(5.0)

    def test_within_threshold(self):
        """Test distance within 500m threshold."""
        dist = _euclidean_distance(193100.0, 332100.0, 193150.0, 332160.0)
        assert dist < MATCH_THRESHOLD_METRES

    def test_outside_threshold(self):
        """Test distance outside 500m threshold."""
        dist = _euclidean_distance(193100.0, 332100.0, 193500.0, 332500.0)
        assert dist > MATCH_THRESHOLD_METRES


# ============================================================================
# Condition Extraction Tests
# ============================================================================


class TestExtractConditionFromNotes:
    """Tests for _extract_condition_from_notes function."""

    def test_empty_notes(self):
        """Test empty notes returns None."""
        assert _extract_condition_from_notes("") is None
        assert _extract_condition_from_notes("  ") is None

    def test_destroyed_x(self):
        """Test 'X' notes map to destroyed condition."""
        assert _extract_condition_from_notes("X") == "X"
        assert _extract_condition_from_notes("X1") == "X"

    def test_remains_r(self):
        """Test 'R' notes map to remains condition."""
        assert _extract_condition_from_notes("R") == "R"
        assert _extract_condition_from_notes("R  H") == "R"

    def test_non_condition_notes(self):
        """Test non-condition notes return None."""
        assert _extract_condition_from_notes("bolt") is None
        assert _extract_condition_from_notes("H") is None


# ============================================================================
# Field Comparison Tests
# ============================================================================


class TestCompareFields:
    """Tests for _compare_fields function."""

    @staticmethod
    def _make_csv_row(
        row_index: int = 0,
        station_name: str = "Test Station",
        osi_ni_no: str = "OSI",
        eastings: float = 200000.0,
        northings: float = 300000.0,
        height: Optional[float] = 100.0,
        fb_sort: str = "",
        fb_number: str = "1234",
        date_built: str = "",
        order: str = "1",
        dr: str = "",
        grid_ref: str = "N 000 000",
        notes: str = "",
    ) -> CSVRow:
        """Create a CSVRow with defaults."""
        return CSVRow(
            row_index=row_index,
            station_name=station_name,
            osi_ni_no=osi_ni_no,
            eastings=eastings,
            northings=northings,
            height=height,
            fb_sort=fb_sort,
            fb_number=fb_number,
            date_built=date_built,
            order=order,
            dr=dr,
            grid_ref=grid_ref,
            notes=notes,
        )

    @staticmethod
    def _make_db_trig(
        trig_id: int = 1,
        waypoint: str = "TP0001",
        name: str = "Test Station",
        fb_number: str = "1234",
        stn_number: str = "OSI",
        osgb_eastings: float = 200000.0,
        osgb_northings: float = 300000.0,
        osgb_gridref: str = "N 000 000",
        osgb_height: Optional[float] = 100.0,
        condition: str = "G",
        historic_use: str = "Primary",
        current_use: str = "none",
        status_id: int = 1,
        type_id: Optional[int] = None,
        area_id: int = 342,
        has_non_irish_gridref: bool = False,
    ) -> DBIrishTrig:
        """Create a DBIrishTrig with defaults."""
        return DBIrishTrig(
            trig_id=trig_id,
            waypoint=waypoint,
            name=name,
            fb_number=fb_number,
            stn_number=stn_number,
            osgb_eastings=osgb_eastings,
            osgb_northings=osgb_northings,
            osgb_gridref=osgb_gridref,
            osgb_height=osgb_height,
            condition=condition,
            historic_use=historic_use,
            current_use=current_use,
            status_id=status_id,
            type_id=type_id,
            area_id=area_id,
            has_non_irish_gridref=has_non_irish_gridref,
        )

    def test_identical_records_no_diffs(self):
        """Test that identical records produce no differences."""
        csv_row = self._make_csv_row()
        db_trig = self._make_db_trig()
        diffs = _compare_fields(csv_row, db_trig)
        assert len(diffs) == 0

    def test_name_difference(self):
        """Test name difference is detected."""
        csv_row = self._make_csv_row(station_name="Foo Hill")
        db_trig = self._make_db_trig(name="Bar Hill")
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "name" in names

    def test_name_case_insensitive(self):
        """Test name comparison is case-insensitive."""
        csv_row = self._make_csv_row(station_name="test station")
        db_trig = self._make_db_trig(name="Test Station")
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "name" not in names

    def test_fb_number_leading_zeros(self):
        """Test FB number comparison ignores leading zeros."""
        csv_row = self._make_csv_row(fb_number="0004")
        db_trig = self._make_db_trig(fb_number="4")
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "fb_number" not in names

    def test_eastings_within_tolerance(self):
        """Test eastings within 1m tolerance are identical."""
        csv_row = self._make_csv_row(eastings=200000.5)
        db_trig = self._make_db_trig(osgb_eastings=200000.0)
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "osgb_eastings" not in names

    def test_eastings_outside_tolerance(self):
        """Test eastings outside 1m tolerance are flagged."""
        csv_row = self._make_csv_row(eastings=200002.0)
        db_trig = self._make_db_trig(osgb_eastings=200000.0)
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "osgb_eastings" in names

    def test_height_difference(self):
        """Test height difference is detected."""
        csv_row = self._make_csv_row(height=150.0)
        db_trig = self._make_db_trig(osgb_height=100.0)
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "osgb_height" in names

    def test_height_within_tolerance(self):
        """Test height within 0.5m tolerance is identical."""
        csv_row = self._make_csv_row(height=100.3)
        db_trig = self._make_db_trig(osgb_height=100.0)
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "osgb_height" not in names

    def test_historic_use_mapping(self):
        """Test historic use mapping from Ord column."""
        csv_row = self._make_csv_row(order="2")
        db_trig = self._make_db_trig(historic_use="Primary")
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "historic_use" in names
        use_diff = [d for d in diffs if d.field_name == "historic_use"][0]
        assert use_diff.csv_value == "Secondary"

    def test_condition_from_notes(self):
        """Test condition extracted from notes."""
        csv_row = self._make_csv_row(notes="X1")
        db_trig = self._make_db_trig(condition="G")
        diffs = _compare_fields(csv_row, db_trig)
        names = [d.field_name for d in diffs]
        assert "condition" in names
        cond_diff = [d for d in diffs if d.field_name == "condition"][0]
        assert cond_diff.csv_value == "X"


# ============================================================================
# Build Trig Data Tests
# ============================================================================


class TestBuildTrigDataFromCSV:
    """Tests for build_trig_data_from_csv function."""

    def test_basic_field_mapping(self):
        """Test that basic fields are correctly mapped."""
        csv_row = CSVRow(
            row_index=0,
            station_name="Test Station",
            osi_ni_no="P20 OSI",
            eastings=200000.0,
            northings=300000.0,
            height=150.0,
            fb_sort="",
            fb_number="1234",
            date_built="OSI",
            order="1",
            dr=".035",
            grid_ref="N 000 000",
            notes="",
        )
        data = build_trig_data_from_csv(csv_row)

        assert data["name"] == "Test Station"
        assert data["stn_number"] == "P20 OSI"
        assert data["fb_number"] == "1234"
        assert data["historic_use"] == "Primary"
        assert data["osgb_eastings"] == 200000.0
        assert data["osgb_northings"] == 300000.0
        assert data["osgb_height"] == 150.0
        assert data["original_grid_system"] == "ie"
        assert data["original_provenance"] == "Ireland25"

    def test_wgs84_conversion_populated(self):
        """Test that WGS84 coords are computed from Irish Grid."""
        csv_row = CSVRow(
            row_index=0,
            station_name="Howth Head",
            osi_ni_no="P29 OSI",
            eastings=328546.0,
            northings=237617.0,
            height=171.0,
            fb_sort="",
            fb_number="0009",
            date_built="OSI",
            order="1",
            dr=".150",
            grid_ref="O 285 376",
            notes="",
        )
        data = build_trig_data_from_csv(csv_row)

        # WGS84 lat should be roughly 53.3-53.4 for Howth Head
        assert data["wgs_lat"] is not None
        assert 53.3 < float(data["wgs_lat"]) < 53.5

        # WGS84 lon should be roughly -6.0 to -6.1
        assert data["wgs_long"] is not None
        assert -6.2 < float(data["wgs_long"]) < -5.9

    def test_condition_from_notes_destroyed(self):
        """Test destroyed condition from notes."""
        csv_row = CSVRow(
            row_index=0,
            station_name="Ouley",
            osi_ni_no="OSNI",
            eastings=338260.0,
            northings=362690.0,
            height=181.0,
            fb_sort="",
            fb_number="2060",
            date_built="tbc",
            order="2",
            dr=".020",
            grid_ref="J 382 626",
            notes="X1",
        )
        data = build_trig_data_from_csv(csv_row)
        assert data["condition"] == "X"

    def test_height_none_when_unknown(self):
        """Test height is None when CSV has no height."""
        csv_row = CSVRow(
            row_index=0,
            station_name="Test",
            osi_ni_no="OSI",
            eastings=200000.0,
            northings=300000.0,
            height=None,
            fb_sort="",
            fb_number="1234",
            date_built="",
            order="",
            dr="",
            grid_ref="N 000 000",
            notes="",
        )
        data = build_trig_data_from_csv(csv_row)
        assert data["osgb_height"] is None
        assert data["original_osgb_height"] is None

    def test_ord_to_historic_use_mapping(self):
        """Test all Ord to historic_use mappings."""
        for ord_val, expected_use in ORD_TO_HISTORIC_USE.items():
            csv_row = CSVRow(
                row_index=0,
                station_name="Test",
                osi_ni_no="",
                eastings=200000.0,
                northings=300000.0,
                height=None,
                fb_sort="",
                fb_number="",
                date_built="",
                order=ord_val,
                dr="",
                grid_ref="N 000 000",
                notes="",
            )
            data = build_trig_data_from_csv(csv_row)
            assert (
                data["historic_use"] == expected_use
            ), f"Ord '{ord_val}' should map to '{expected_use}'"


# ============================================================================
# Full Comparison Tests (mocked DB)
# ============================================================================


class TestCompareIrelandCSVWithDB:
    """Tests for compare_ireland_csv_with_db with mocked database."""

    @patch("api.services.ireland_import_service.get_irish_trigs_from_db")
    @patch("api.services.ireland_import_service.parse_csv")
    def test_new_in_csv_when_no_db_trigs(self, mock_parse, mock_db):
        """Test that all CSV rows are 'new_in_csv' when DB has no Irish trigs."""
        mock_parse.return_value = [
            CSVRow(
                row_index=0,
                station_name="Test",
                osi_ni_no="OSI",
                eastings=200000.0,
                northings=300000.0,
                height=100.0,
                fb_sort="",
                fb_number="1234",
                date_built="",
                order="1",
                dr="",
                grid_ref="N 000 000",
                notes="",
            ),
        ]
        mock_db.return_value = []

        db = MagicMock()
        result = compare_ireland_csv_with_db(db)

        assert result.csv_count == 1
        assert result.db_irish_count == 0
        assert result.new_in_csv_count == 1
        assert result.items[0].category == "new_in_csv"

    @patch("api.services.ireland_import_service.get_irish_trigs_from_db")
    @patch("api.services.ireland_import_service.parse_csv")
    def test_matched_identical(self, mock_parse, mock_db):
        """Test matched_identical when CSV and DB agree on all fields."""
        mock_parse.return_value = [
            CSVRow(
                row_index=0,
                station_name="Test Station",
                osi_ni_no="OSI",
                eastings=200000.0,
                northings=300000.0,
                height=100.0,
                fb_sort="",
                fb_number="1234",
                date_built="",
                order="1",
                dr="",
                grid_ref="N 000 000",
                notes="",
            ),
        ]
        mock_db.return_value = [
            DBIrishTrig(
                trig_id=1,
                waypoint="TP0001",
                name="Test Station",
                fb_number="1234",
                stn_number="OSI",
                osgb_eastings=200000.0,
                osgb_northings=300000.0,
                osgb_gridref="N 000 000",
                osgb_height=100.0,
                condition="G",
                historic_use="Primary",
                current_use="none",
                status_id=1,
                type_id=None,
                area_id=342,
            ),
        ]

        db = MagicMock()
        result = compare_ireland_csv_with_db(db)

        assert result.matched_identical_count == 1
        assert result.matched_different_count == 0

    @patch("api.services.ireland_import_service.get_irish_trigs_from_db")
    @patch("api.services.ireland_import_service.parse_csv")
    def test_matched_different(self, mock_parse, mock_db):
        """Test matched_different when fields differ."""
        mock_parse.return_value = [
            CSVRow(
                row_index=0,
                station_name="New Name",
                osi_ni_no="OSI",
                eastings=200000.0,
                northings=300000.0,
                height=100.0,
                fb_sort="",
                fb_number="1234",
                date_built="",
                order="1",
                dr="",
                grid_ref="N 000 000",
                notes="",
            ),
        ]
        mock_db.return_value = [
            DBIrishTrig(
                trig_id=1,
                waypoint="TP0001",
                name="Old Name",
                fb_number="1234",
                stn_number="OSI",
                osgb_eastings=200000.0,
                osgb_northings=300000.0,
                osgb_gridref="N 000 000",
                osgb_height=100.0,
                condition="G",
                historic_use="Primary",
                current_use="none",
                status_id=1,
                type_id=None,
                area_id=342,
            ),
        ]

        db = MagicMock()
        result = compare_ireland_csv_with_db(db)

        assert result.matched_different_count == 1
        diff_item = [i for i in result.items if i.category == "matched_different"][0]
        field_names = [d.field_name for d in diff_item.differences]
        assert "name" in field_names

    @patch("api.services.ireland_import_service.get_irish_trigs_from_db")
    @patch("api.services.ireland_import_service.parse_csv")
    def test_ambiguous_multiple_matches(self, mock_parse, mock_db):
        """Test ambiguous when multiple DB trigs are within threshold."""
        mock_parse.return_value = [
            CSVRow(
                row_index=0,
                station_name="Overlap",
                osi_ni_no="OSI",
                eastings=200000.0,
                northings=300000.0,
                height=100.0,
                fb_sort="",
                fb_number="1234",
                date_built="",
                order="1",
                dr="",
                grid_ref="N 000 000",
                notes="",
            ),
        ]
        mock_db.return_value = [
            DBIrishTrig(
                trig_id=1,
                waypoint="TP0001",
                name="Overlap A",
                fb_number="1234",
                stn_number="OSI",
                osgb_eastings=200002.0,
                osgb_northings=300002.0,
                osgb_gridref="N 000 000",
                osgb_height=100.0,
                condition="G",
                historic_use="Primary",
                current_use="none",
                status_id=1,
                type_id=None,
                area_id=342,
            ),
            DBIrishTrig(
                trig_id=2,
                waypoint="TP0002",
                name="Overlap B",
                fb_number="1235",
                stn_number="OSI",
                osgb_eastings=200005.0,
                osgb_northings=300005.0,
                osgb_gridref="N 000 000",
                osgb_height=100.0,
                condition="G",
                historic_use="Primary",
                current_use="none",
                status_id=1,
                type_id=None,
                area_id=342,
            ),
        ]

        db = MagicMock()
        result = compare_ireland_csv_with_db(db)

        assert result.ambiguous_count == 1
        ambig_item = [i for i in result.items if i.category == "ambiguous"][0]
        assert len(ambig_item.additional_db_matches) == 1

    @patch("api.services.ireland_import_service.get_irish_trigs_from_db")
    @patch("api.services.ireland_import_service.parse_csv")
    def test_orphan_in_db(self, mock_parse, mock_db):
        """Test orphan_in_db when DB trig has no CSV match."""
        mock_parse.return_value = []
        mock_db.return_value = [
            DBIrishTrig(
                trig_id=1,
                waypoint="TP0001",
                name="Orphan Hill",
                fb_number="1234",
                stn_number="OSI",
                osgb_eastings=200000.0,
                osgb_northings=300000.0,
                osgb_gridref="N 000 000",
                osgb_height=100.0,
                condition="G",
                historic_use="Primary",
                current_use="none",
                status_id=1,
                type_id=None,
                area_id=342,
            ),
        ]

        db = MagicMock()
        result = compare_ireland_csv_with_db(db)

        assert result.orphan_in_db_count == 1
        assert result.items[0].category == "orphan_in_db"

    @patch("api.services.ireland_import_service.get_irish_trigs_from_db")
    @patch("api.services.ireland_import_service.parse_csv")
    def test_non_irish_gridref_count(self, mock_parse, mock_db):
        """Test non-Irish gridref count is calculated correctly."""
        mock_parse.return_value = []
        mock_db.return_value = [
            DBIrishTrig(
                trig_id=1,
                waypoint="TP0001",
                name="GB Gridref Trig",
                fb_number="",
                stn_number="",
                osgb_eastings=200000.0,
                osgb_northings=300000.0,
                osgb_gridref="TQ 123 456",  # GB format, not Irish
                osgb_height=100.0,
                condition="G",
                historic_use="none",
                current_use="none",
                status_id=1,
                type_id=None,
                area_id=342,
                has_non_irish_gridref=True,
            ),
        ]

        db = MagicMock()
        result = compare_ireland_csv_with_db(db)

        assert result.non_irish_gridref_count == 1

    @patch("api.services.ireland_import_service.get_irish_trigs_from_db")
    @patch("api.services.ireland_import_service.parse_csv")
    def test_outside_threshold_no_match(self, mock_parse, mock_db):
        """Test that points >500m apart are not matched."""
        mock_parse.return_value = [
            CSVRow(
                row_index=0,
                station_name="Far Away",
                osi_ni_no="OSI",
                eastings=200000.0,
                northings=300000.0,
                height=100.0,
                fb_sort="",
                fb_number="1234",
                date_built="",
                order="1",
                dr="",
                grid_ref="N 000 000",
                notes="",
            ),
        ]
        mock_db.return_value = [
            DBIrishTrig(
                trig_id=1,
                waypoint="TP0001",
                name="Far Away DB",
                fb_number="1234",
                stn_number="OSI",
                osgb_eastings=200400.0,  # ~566m away (400^2 + 400^2)
                osgb_northings=300400.0,
                osgb_gridref="N 000 000",
                osgb_height=100.0,
                condition="G",
                historic_use="Primary",
                current_use="none",
                status_id=1,
                type_id=None,
                area_id=342,
            ),
        ]

        db = MagicMock()
        result = compare_ireland_csv_with_db(db)

        assert result.new_in_csv_count == 1
        assert result.orphan_in_db_count == 1
        assert result.matched_identical_count == 0
        assert result.matched_different_count == 0
