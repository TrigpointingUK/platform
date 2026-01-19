"""
API tests for the coordinate conversion endpoint.

Tests the /v1/coordinates/convert endpoint.
"""

from fastapi.testclient import TestClient

from api.main import app

client = TestClient(app)


class TestCoordinateConversionEndpoint:
    """Tests for the /v1/coordinates/convert endpoint."""

    def test_wgs84_to_osgb_2d_official_os_data(self):
        """Test WGS84 to OSGB conversion (2D) using official OS reference data.

        Official OS test data:
        - ETRS89: 51.507879, -0.128094
        - OSGB36: 530005.2410, 180432.6360

        Note: API rounds eastings/northings to integers for practical use.
        """
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "osgb",
                "lat": 51.507879,
                "lon": -0.128094,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["from_crs"] == "wgs84"
        assert data["to_crs"] == "osgb"
        assert data["input"]["lat"] == 51.507879
        assert data["input"]["lon"] == -0.128094
        assert data["input"]["height"] is None

        # API rounds to integers - check within 1m of expected values
        assert abs(data["output"]["e"] - 530005) <= 1
        assert abs(data["output"]["n"] - 180433) <= 1
        assert data["output"]["height"] is None

        # Check grid reference is generated
        assert data["output"]["gridref"] is not None
        assert data["output"]["gridref"].startswith("TQ")

    def test_wgs84_to_osgb_3d_official_os_data(self):
        """Test WGS84 to OSGB conversion (3D) using official OS reference data.

        Official OS test data:
        - ETRS89: 51.507879, -0.128094, 10m (ellipsoidal)
        - OSGB36: 530005.2410, 180432.6360, -35.549m (ODN)

        Note: API rounds height to 1 decimal place.
        """
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "osgb",
                "lat": 51.507879,
                "lon": -0.128094,
                "height": 10.0,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["input"]["height"] == 10.0

        # API rounds height to 1 decimal place - check within 0.1m
        assert data["output"]["height"] is not None
        assert abs(data["output"]["height"] - (-35.5)) < 0.2

    def test_osgb_to_wgs84_2d_official_os_data(self):
        """Test OSGB to WGS84 conversion (2D) using official OS reference data.

        Official OS test data:
        - OSGB36: 530005.2410, 180432.6360 (we input rounded: 530005, 180433)
        - ETRS89: 51.507879, -0.128094

        Note: Since input is rounded to integers, output will be slightly off.
        """
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "osgb",
                "to": "wgs84",
                "e": 530005,
                "n": 180433,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["from_crs"] == "osgb"
        assert data["to_crs"] == "wgs84"
        assert data["input"]["e"] == 530005
        assert data["input"]["n"] == 180433

        # Allow ~10m tolerance due to input rounding (1m input -> ~0.00001 degree)
        assert abs(data["output"]["lon"] - (-0.128094)) < 0.0001
        assert abs(data["output"]["lat"] - 51.507879) < 0.0001
        assert data["output"]["height"] is None

        # Grid reference should be included in input for convenience
        assert data["input"]["gridref"] is not None

    def test_osgb_to_wgs84_3d_official_os_data(self):
        """Test OSGB to WGS84 conversion (3D) using official OS reference data.

        Official OS test data:
        - OSGB36: 530005.2410, 180432.6360, -35.549m (ODN)
        - ETRS89: 51.507879, -0.128094, 10m (ellipsoidal)
        """
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "osgb",
                "to": "wgs84",
                "e": 530005,
                "n": 180433,
                "height": -35.549,  # -35.549m orthometric (ODN)
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["input"]["height"] == -35.549

        # OSTN15/OSGM15 should achieve high accuracy
        # Expected ellipsoidal height is ~10m
        assert data["output"]["height"] is not None
        assert abs(data["output"]["height"] - 10.0) < 1.0  # Within 1m (input rounded)

    def test_barra_differential_wgs_to_osgb(self):
        """Test conversion for Barra Differential (reference point from database).

        Note: Barra (lon=-7.43) is outside the OSGM15 geoid coverage (extends to -7.06),
        so height conversion is not available and we only test horizontal conversion.
        """
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "osgb",
                "lat": 56.96243,
                "lon": -7.43001,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Expected from schema: e=70095, n=798813 (within 10m tolerance)
        assert abs(data["output"]["e"] - 70095) < 10
        assert abs(data["output"]["n"] - 798813) < 10

        # Grid reference should be in NL square (Barra area)
        assert data["output"]["gridref"] is not None
        assert data["output"]["gridref"].startswith("NL")

    def test_missing_lat_lon_for_wgs84(self):
        """Test that missing lat/lon returns 400 error."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "osgb",
                "lat": 51.5074,
                # lon is missing
            },
        )

        assert response.status_code == 400
        assert "lon" in response.json()["detail"].lower()

    def test_missing_eastings_northings_for_osgb(self):
        """Test that missing e/n returns 400 error."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "osgb",
                "to": "wgs84",
                "e": 530034,
                # n is missing
            },
        )

        assert response.status_code == 400
        assert "n" in response.json()["detail"].lower()

    def test_same_crs_conversion_rejected(self):
        """Test that converting to same CRS returns 400 error."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "wgs84",
                "lat": 51.5074,
                "lon": -0.1276,
            },
        )

        assert response.status_code == 400
        assert "different" in response.json()["detail"].lower()

    def test_invalid_from_crs(self):
        """Test that invalid 'from' CRS returns 422 validation error."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "invalid",
                "to": "osgb",
                "lat": 51.5074,
                "lon": -0.1276,
            },
        )

        assert response.status_code == 422  # Validation error

    def test_latitude_out_of_range(self):
        """Test that latitude outside valid range returns 422 error."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "osgb",
                "lat": 91.0,  # Invalid: max is 90
                "lon": -0.1276,
            },
        )

        assert response.status_code == 422

    def test_longitude_out_of_range(self):
        """Test that longitude outside valid range returns 422 error."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "osgb",
                "lat": 51.5074,
                "lon": 181.0,  # Invalid: max is 180
            },
        )

        assert response.status_code == 422

    def test_eastings_out_of_range(self):
        """Test that eastings outside valid range returns 422 error."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "osgb",
                "to": "wgs84",
                "e": 800000,  # Invalid: max is 700000
                "n": 179382,
            },
        )

        assert response.status_code == 422

    def test_round_trip_consistency(self):
        """Test that WGS84 -> OSGB -> WGS84 gives consistent results."""
        # First conversion: WGS84 to OSGB
        response1 = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "osgb",
                "lat": 52.5,
                "lon": -1.5,
                "height": 150.0,
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Second conversion: OSGB back to WGS84
        response2 = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "osgb",
                "to": "wgs84",
                "e": data1["output"]["e"],
                "n": data1["output"]["n"],
                "height": data1["output"]["height"],
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Should get back approximately the original coordinates
        assert abs(data2["output"]["lat"] - 52.5) < 0.00001
        assert abs(data2["output"]["lon"] - (-1.5)) < 0.00001
        assert abs(data2["output"]["height"] - 150.0) < 0.5


class TestCoordinateConversionNoAuth:
    """Test that the endpoint is publicly accessible (no auth required)."""

    def test_endpoint_is_public(self):
        """Test that the endpoint works without authentication."""
        # Make request without any Authorization header
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "osgb",
                "lat": 51.5074,
                "lon": -0.1276,
            },
        )

        # Should succeed without authentication
        assert response.status_code == 200


# =============================================================================
# Irish Grid Tests
# =============================================================================


class TestIrishGridConversion:
    """Tests for Irish Grid (EPSG:29903) coordinate conversion."""

    def test_wgs84_to_irish_dublin(self):
        """Test WGS84 to Irish Grid conversion for Dublin.

        Dublin city centre: approximately lat=53.3498, lon=-6.2603
        Expected Irish Grid: approximately E=315900, N=234670
        """
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "irish",
                "lat": 53.3498,
                "lon": -6.2603,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["from_crs"] == "wgs84"
        assert data["to_crs"] == "irish"
        assert data["input"]["lat"] == 53.3498
        assert data["input"]["lon"] == -6.2603

        # Dublin should be around E=315900, N=234670 (within 500m tolerance)
        assert abs(data["output"]["e"] - 315900) < 500
        assert abs(data["output"]["n"] - 234670) < 500

        # Grid reference should be in O grid square
        assert data["output"]["gridref"] is not None
        assert data["output"]["gridref"].startswith("O")

    def test_wgs84_to_irish_belfast(self):
        """Test WGS84 to Irish Grid conversion for Belfast (Northern Ireland).

        Belfast city centre: approximately lat=54.5973, lon=-5.9301
        Expected Irish Grid: approximately E=333828, N=374087
        """
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "irish",
                "lat": 54.5973,
                "lon": -5.9301,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Belfast should be around E=333828, N=374087 (within 500m tolerance)
        assert abs(data["output"]["e"] - 333828) < 500
        assert abs(data["output"]["n"] - 374087) < 500

        # Grid reference should be in J grid square
        assert data["output"]["gridref"] is not None
        assert data["output"]["gridref"].startswith("J")

    def test_irish_to_wgs84_dublin(self):
        """Test Irish Grid to WGS84 conversion for Dublin."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "irish",
                "to": "wgs84",
                "e": 316200,
                "n": 234000,
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert data["from_crs"] == "irish"
        assert data["to_crs"] == "wgs84"

        # Dublin is approximately lat=53.35, lon=-6.26
        assert abs(data["output"]["lat"] - 53.35) < 0.05
        assert abs(data["output"]["lon"] - (-6.26)) < 0.05

        # Grid reference should be included in input
        assert data["input"]["gridref"] is not None
        assert data["input"]["gridref"].startswith("O")

    def test_irish_to_wgs84_belfast(self):
        """Test Irish Grid to WGS84 conversion for Belfast."""
        response = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "irish",
                "to": "wgs84",
                "e": 334000,
                "n": 373000,
            },
        )

        assert response.status_code == 200
        data = response.json()

        # Belfast is approximately lat=54.6, lon=-5.9
        assert abs(data["output"]["lat"] - 54.6) < 0.1
        assert abs(data["output"]["lon"] - (-5.9)) < 0.1

        # Grid reference should be in J grid square
        assert data["input"]["gridref"] is not None
        assert data["input"]["gridref"].startswith("J")

    def test_irish_grid_round_trip(self):
        """Test that WGS84 -> Irish -> WGS84 gives consistent results."""
        # First conversion: WGS84 to Irish Grid
        response1 = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "wgs84",
                "to": "irish",
                "lat": 53.5,
                "lon": -7.5,
            },
        )
        assert response1.status_code == 200
        data1 = response1.json()

        # Second conversion: Irish Grid back to WGS84
        response2 = client.get(
            "/v1/coordinates/convert",
            params={
                "from": "irish",
                "to": "wgs84",
                "e": data1["output"]["e"],
                "n": data1["output"]["n"],
            },
        )
        assert response2.status_code == 200
        data2 = response2.json()

        # Should get back approximately the original coordinates
        assert abs(data2["output"]["lat"] - 53.5) < 0.001
        assert abs(data2["output"]["lon"] - (-7.5)) < 0.001

    # Note: Auto-detect tests (to=grid) and gridref parsing tests (from=gridref)
    # require the database to have country polygon data loaded, which is not
    # available in the unit test environment. These features are tested in
    # integration tests that run against the real database.
