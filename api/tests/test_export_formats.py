"""
Tests for export format generators.
"""

from unittest.mock import MagicMock

from api.services.export_formats import trigs_to_gpx


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

    def test_gpx_element_order(self):
        """Test that GPX elements are in correct schema order: cmt before desc."""
        trig = _make_mock_trig()
        result = trigs_to_gpx([trig])

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

    def test_gpx_xml_escaping(self):
        """Test that special characters are properly escaped."""
        trig = _make_mock_trig(name="Test & <Trig>")
        result = trigs_to_gpx([trig])

        assert "Test &amp; &lt;Trig&gt;" in result

    def test_gpx_multiple_trigs(self):
        """Test GPX output with multiple trigpoints."""
        trigs = [
            _make_mock_trig(id=1, waypoint="TP0001"),
            _make_mock_trig(id=2, waypoint="TP0002"),
        ]
        result = trigs_to_gpx(trigs)

        assert "<name>TP0001</name>" in result
        assert "<name>TP0002</name>" in result
        assert '<link href="https://trigpointing.uk/trigs/1">' in result
        assert '<link href="https://trigpointing.uk/trigs/2">' in result
