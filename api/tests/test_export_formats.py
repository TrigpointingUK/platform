"""
Tests for export format generators.
"""

import io
import zipfile
from unittest.mock import MagicMock

from api.services.export_formats import trigs_to_gpx, trigs_to_kmz


def _make_mock_trig(
    id: int = 1,
    waypoint: str = "TP0001",
    name: str = "Test Trig",
    physical_type: str = "Pillar",
    condition: str = "G",
    status_id: int = 1,
    wgs_lat: float = 51.5074,
    wgs_long: float = -0.1278,
    wgs_height: int = 100,
    osgb_gridref: str = "TQ 30000 80000",
    county: str = "Greater London",
    fb_number: str = "S1234",
    group_code: str = "PILLAR",
    group_name: str = "Pillar",
) -> MagicMock:
    """Create a mock Trig object for testing."""
    mock_trig = MagicMock()
    mock_trig.id = id
    mock_trig.waypoint = waypoint
    mock_trig.name = name
    mock_trig.physical_type = physical_type
    mock_trig.condition = condition
    mock_trig.status_id = status_id
    mock_trig.wgs_lat = wgs_lat
    mock_trig.wgs_long = wgs_long
    mock_trig.wgs_height = wgs_height
    mock_trig.osgb_gridref = osgb_gridref
    mock_trig.county = county
    mock_trig.fb_number = fb_number

    # Mock trig_type and group relationships
    mock_group = MagicMock()
    mock_group.code = group_code
    mock_group.name = group_name

    mock_type = MagicMock()
    mock_type.group = mock_group

    mock_trig.trig_type = mock_type

    return mock_trig


class TestTrigsToGpx:
    """Tests for trigs_to_gpx function."""

    def test_gpx_contains_link_element(self):
        """Test that GPX output contains link element with correct URL."""
        trig = _make_mock_trig(id=12345)
        result = trigs_to_gpx([trig])

        assert '<link href="https://trigpointing.uk/trigs/12345">' in result
        assert "<text>View on TrigpointingUK</text>" in result
        assert "</link>" in result

    def test_gpx_contains_type_element(self):
        """Test that GPX output contains type element with physical_type."""
        trig = _make_mock_trig(physical_type="Pillar")
        result = trigs_to_gpx([trig])

        assert "<type>Pillar</type>" in result

    def test_gpx_element_order_with_user_logs(self):
        """Test that GPX elements are in correct schema order when user_logs provided."""
        trig = _make_mock_trig(id=1)
        user_logs = {1: {"date": "2024-01-01", "condition": "G"}}
        result = trigs_to_gpx([trig], user_logs=user_logs)

        # Find positions of key elements
        cmt_pos = result.find("<cmt>")
        desc_pos = result.find("<desc>")
        link_pos = result.find("<link")
        sym_pos = result.find("<sym>")
        type_pos = result.find("<type>")

        # Verify order: cmt < desc < link < sym < type
        assert cmt_pos < desc_pos, "cmt must come before desc"
        assert desc_pos < link_pos, "desc must come before link"
        assert link_pos < sym_pos, "link must come before sym"
        assert sym_pos < type_pos, "sym must come before type"

    def test_gpx_basic_structure(self):
        """Test basic GPX structure is valid."""
        trig = _make_mock_trig()
        result = trigs_to_gpx([trig])

        assert '<?xml version="1.0" encoding="UTF-8"?>' in result
        assert '<gpx version="1.1" creator="TrigpointingUK"' in result
        assert "</gpx>" in result
        assert "<metadata>" in result
        assert "<name>TrigpointingUK Export</name>" in result

    def test_gpx_waypoint_coordinates(self):
        """Test waypoint has correct coordinates."""
        trig = _make_mock_trig(wgs_lat=52.1234, wgs_long=-1.5678)
        result = trigs_to_gpx([trig])

        assert 'lat="52.1234"' in result
        assert 'lon="-1.5678"' in result

    def test_gpx_name_includes_trig_name(self):
        """Test that name element includes both waypoint and trig name."""
        trig = _make_mock_trig(waypoint="TP0001", name="Fetlar")
        result = trigs_to_gpx([trig])

        assert "<name>TP0001 - Fetlar</name>" in result

    def test_gpx_xml_escaping(self):
        """Test that special characters are properly escaped."""
        trig = _make_mock_trig(name="Test & <Trig>")
        result = trigs_to_gpx([trig])

        assert "TP0001 - Test &amp; &lt;Trig&gt;" in result

    def test_gpx_multiple_trigs(self):
        """Test GPX output with multiple trigpoints."""
        trigs = [
            _make_mock_trig(id=1, waypoint="TP0001", name="First"),
            _make_mock_trig(id=2, waypoint="TP0002", name="Second"),
        ]
        result = trigs_to_gpx(trigs)

        assert "<name>TP0001 - First</name>" in result
        assert "<name>TP0002 - Second</name>" in result
        assert '<link href="https://trigpointing.uk/trigs/1">' in result
        assert '<link href="https://trigpointing.uk/trigs/2">' in result

    def test_gpx_cmt_omitted_when_no_user_logs(self):
        """Test that cmt element is omitted when user_logs is not provided."""
        trig = _make_mock_trig()
        result = trigs_to_gpx([trig])

        assert "<cmt>" not in result

    def test_gpx_cmt_logged_when_user_has_log(self):
        """Test that cmt shows 'Logged' when user has logged this trig."""
        trig = _make_mock_trig(id=1)
        user_logs = {1: {"date": "2024-01-01", "condition": "G"}}
        result = trigs_to_gpx([trig], user_logs=user_logs)

        assert "<cmt>Logged</cmt>" in result

    def test_gpx_cmt_not_logged_when_user_has_no_log(self):
        """Test that cmt shows 'Not Logged' when user hasn't logged this trig."""
        trig = _make_mock_trig(id=1)
        user_logs = {}  # Empty dict - user_logs provided but no log for this trig
        result = trigs_to_gpx([trig], user_logs=user_logs)

        assert "<cmt>Not Logged</cmt>" in result

    def test_gpx_desc_includes_log_date_when_logged(self):
        """Test that desc includes log date when user has logged this trig."""
        trig = _make_mock_trig(id=1)
        user_logs = {1: {"date": "2024-01-15", "condition": "G"}}
        result = trigs_to_gpx([trig], user_logs=user_logs)

        assert "Log Date: 2024-01-15" in result
        assert "My Condition: G" in result


class TestTrigsToKmz:
    def test_kmz_is_zip_with_doc_kml(self):
        trig = _make_mock_trig(
            id=7177,
            waypoint="TP7177",
            name="Cat and Fiddle",
            group_code="PILLAR",
            group_name="Pillar",
        )
        kmz = trigs_to_kmz([trig])

        with zipfile.ZipFile(io.BytesIO(kmz)) as zf:
            assert "doc.kml" in zf.namelist()
            kml = zf.read("doc.kml").decode("utf-8")
            assert "<name>TrigpointingUK</name>" in kml

    def test_kmz_embeds_icons_and_references_stylemap(self):
        trig = _make_mock_trig(
            id=1,
            physical_type="Pillar",
            condition="G",
            group_code="PILLAR",
            group_name="Pillar",
        )
        kmz = trigs_to_kmz([trig])

        with zipfile.ZipFile(io.BytesIO(kmz)) as zf:
            names = set(zf.namelist())
            assert "icons/mapicon_pillar_green.png" in names
            assert "icons/mapicon_pillar_green_h.png" in names
            kml = zf.read("doc.kml").decode("utf-8")
            assert "#sm_pillar_green" in kml
            assert "icons/mapicon_pillar_green.png" in kml
            assert "icons/mapicon_pillar_green_h.png" in kml

    def test_kmz_colour_mapping_mylog_vs_condition(self):
        trig = _make_mock_trig(
            id=1,
            physical_type="Pillar",
            condition="P",
            group_code="PILLAR",
            group_name="Pillar",
        )

        # Condition mode: P => grey
        kmz = trigs_to_kmz([trig], user_logs=None)
        with zipfile.ZipFile(io.BytesIO(kmz)) as zf:
            kml = zf.read("doc.kml").decode("utf-8")
            assert "#sm_pillar_grey" in kml

        # My log mode: logged P => red
        kmz2 = trigs_to_kmz(
            [trig],
            user_logs={1: {"date": "2024-01-01", "condition": "P"}},
        )
        with zipfile.ZipFile(io.BytesIO(kmz2)) as zf:
            kml2 = zf.read("doc.kml").decode("utf-8")
            assert "#sm_pillar_red" in kml2

    def test_kmz_blank_logged_condition_is_green(self):
        trig = _make_mock_trig(
            id=1,
            physical_type="Pillar",
            condition="U",
            group_code="PILLAR",
            group_name="Pillar",
        )
        kmz = trigs_to_kmz(
            [trig],
            user_logs={1: {"date": "2024-01-01", "condition": ""}},
        )
        with zipfile.ZipFile(io.BytesIO(kmz)) as zf:
            kml = zf.read("doc.kml").decode("utf-8")
            assert "#sm_pillar_green" in kml

    def test_kmz_bolt_is_passive_icon_family(self):
        trig = _make_mock_trig(
            id=1,
            physical_type="Bolt",
            condition="G",
            group_code="SURVEY_MARK",
            group_name="Survey mark",
        )
        kmz = trigs_to_kmz([trig])
        with zipfile.ZipFile(io.BytesIO(kmz)) as zf:
            names = set(zf.namelist())
            assert "icons/mapicon_passive_green.png" in names
