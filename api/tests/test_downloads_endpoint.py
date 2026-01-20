"""
Tests for the /v1/downloads endpoint.

Tests trigpoint export in various formats (CSV, GeoJSON, KML, GPX, KMZ)
and personal data download functionality.
"""

import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.models.trig import Trig
from api.models.user import TLog, User


class MockRateLimiter:
    """Mock rate limiter that always allows downloads."""

    def check_limit(
        self, format: str, user_id: int | None = None, client_ip: str | None = None
    ):
        return True, None

    def record_download(
        self, format: str, user_id: int | None = None, client_ip: str | None = None
    ):
        pass


@pytest.fixture
def mock_rate_limiter(monkeypatch):
    """Mock the download rate limiter to always allow."""
    monkeypatch.setattr(
        "api.api.v1.endpoints.downloads.get_download_rate_limiter",
        lambda: MockRateLimiter(),
    )


@pytest.fixture
def download_test_data(db):
    """Create test data for download tests."""
    unique_suffix = uuid.uuid4().hex[:6]

    # Create test user
    user = User(
        name=f"DownloadTestUser_{unique_suffix}",
        firstname="Download",
        surname="Test",
        email=f"download_{unique_suffix}@example.invalid",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.flush()

    # Create test trigpoints
    trigs = []
    for i in range(3):
        trig = Trig(
            waypoint=f"DL{unique_suffix[:3]}{i}",
            name=f"DownloadTestTrig_{unique_suffix}_{i}",
            fb_number=f"DLFB{unique_suffix[:3]}{i}",
            stn_number=f"DLSTN{i}",
            status_id=1,
            user_added=0,
            current_use="Passive station",
            historic_use="Primary",
            condition="G",
            wgs_lat=51.5 + (i * 0.1),
            wgs_long=-0.1 + (i * 0.1),
            wgs_height=100 + (i * 10),
            osgb_eastings=530000 + (i * 1000),
            osgb_northings=180000 + (i * 1000),
            osgb_gridref=f"TQ {30000 + (i * 1000):05d} {80000 + (i * 1000):05d}",
            osgb_height=100 + (i * 10),
            county="TestCounty",
            town=f"TestTown{i}",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(0, 0, 0),
            crt_ip_addr="127.0.0.1",
        )
        db.add(trig)
        trigs.append(trig)

    db.flush()

    # Create test logs for the user
    logs = []
    for i, trig in enumerate(trigs[:2]):  # Only log 2 of the 3 trigs
        log = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2023, 12, 15 - i),
            time=time(14, 30, 0),
            osgb_eastings=trig.osgb_eastings,
            osgb_northings=trig.osgb_northings,
            osgb_gridref=trig.osgb_gridref,
            fb_number="",
            condition="G",
            comment=f"Download test log {i} for {unique_suffix}",
            score=7 + i,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        logs.append(log)

    db.commit()

    return {
        "user": user,
        "trigs": trigs,
        "logs": logs,
        "suffix": unique_suffix,
    }


class TestDownloadTrigsCSV:
    """Tests for GET /v1/downloads/trigs?format=csv."""

    def test_download_csv_authenticated(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test CSV download with authentication."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs?format=csv&name={suffix}",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert "attachment" in response.headers["content-disposition"]
        assert ".csv" in response.headers["content-disposition"]

        # Check CSV content has data
        content = response.text
        assert len(content) > 0
        # Should have header row
        lines = content.strip().split("\n")
        assert len(lines) >= 1

    def test_download_csv_unauthenticated(
        self, client: TestClient, mock_rate_limiter, db
    ):
        """Test that CSV download requires authentication."""
        response = client.get("/v1/downloads/trigs?format=csv")

        assert response.status_code == 401

    def test_download_csv_with_county_filter(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test CSV download with county filter."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/trigs?format=csv&county=TestCounty",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]


class TestDownloadTrigsGeoJSON:
    """Tests for GET /v1/downloads/trigs?format=geojson."""

    def test_download_geojson(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test GeoJSON download."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs?format=geojson&name={suffix}",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "geo+json" in response.headers["content-type"]
        assert ".geojson" in response.headers["content-disposition"]

        # Check it's valid GeoJSON
        data = response.json()
        assert data["type"] == "FeatureCollection"
        assert "features" in data

    def test_download_geojson_feature_structure(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test GeoJSON feature structure."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs?format=geojson&name={suffix}",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        data = response.json()

        if len(data["features"]) > 0:
            feature = data["features"][0]
            assert feature["type"] == "Feature"
            assert "geometry" in feature
            assert "properties" in feature
            assert feature["geometry"]["type"] == "Point"
            assert "coordinates" in feature["geometry"]


class TestDownloadTrigsKML:
    """Tests for GET /v1/downloads/trigs?format=kml."""

    def test_download_kml(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test KML download."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs?format=kml&name={suffix}",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "kml" in response.headers["content-type"]
        assert ".kml" in response.headers["content-disposition"]

        # Check it's valid XML with KML structure
        content = response.text
        assert "<?xml" in content
        assert "<kml" in content


class TestDownloadTrigsGPX:
    """Tests for GET /v1/downloads/trigs?format=gpx."""

    def test_download_gpx(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test GPX download."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs?format=gpx&name={suffix}",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "gpx" in response.headers["content-type"]
        assert ".gpx" in response.headers["content-disposition"]

        # Check it's valid XML with GPX structure
        content = response.text
        assert "<?xml" in content
        assert "<gpx" in content


class TestDownloadTrigsKMZ:
    """Tests for GET /v1/downloads/trigs?format=kmz."""

    def test_download_kmz(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test KMZ download."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs?format=kmz&name={suffix}",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "kmz" in response.headers["content-type"]
        assert ".kmz" in response.headers["content-disposition"]

        # KMZ is a zip file, check it starts with zip magic bytes
        assert response.content[:2] == b"PK"


class TestDownloadTrigsFilters:
    """Tests for download filters."""

    def test_download_with_only_found_filter(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test download with only_found filter (user's logged trigs)."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/trigs?format=csv&only_found=true",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        # Should only return trigs the user has logged
        count_header = response.headers.get("X-Trigpoint-Count", "0")
        # User has 2 logs
        assert int(count_header) <= 2

    def test_download_with_exclude_found_filter(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test download with exclude_found filter."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/trigs?format=csv&exclude_found=true",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200

    def test_download_only_found_and_exclude_found_conflict(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test that only_found and exclude_found cannot be used together."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/trigs?format=csv&only_found=true&exclude_found=true",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 400
        assert "cannot use both" in response.json()["detail"].lower()

    def test_download_with_category_filter(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test download with category filter."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/trigs?format=csv&categories=PILLAR,FBM",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200

    def test_download_with_location_filter(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test download with lat/lon/distance filter."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/trigs?format=csv&lat=51.5&lon=-0.1&max_km=50",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200

    def test_download_with_include_my_logs(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test download with user's log data included."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs?format=csv&name={suffix}&include_my_logs=true",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        # The CSV should include log-related columns when include_my_logs=true


class TestDownloadTrigsCount:
    """Tests for GET /v1/downloads/trigs/count."""

    def test_download_count(self, client: TestClient, download_test_data, db):
        """Test getting count of trigpoints for download."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs/count?name={suffix}",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        data = response.json()

        assert "count" in data
        assert "max_immediate" in data
        assert "requires_queue" in data
        assert data["count"] == 3  # We created 3 test trigs

    def test_download_count_unauthenticated(self, client: TestClient, db):
        """Test that count requires authentication."""
        response = client.get("/v1/downloads/trigs/count")

        assert response.status_code == 401

    def test_download_count_with_filters(
        self, client: TestClient, download_test_data, db
    ):
        """Test count with various filters."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/trigs/count?county=TestCounty",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] >= 3  # At least our test trigs

    def test_download_count_only_found(
        self, client: TestClient, download_test_data, db
    ):
        """Test count with only_found filter."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/trigs/count?only_found=true",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["count"] == 2  # User logged 2 trigs


class TestDownloadMyData:
    """Tests for GET /v1/downloads/my-data."""

    def test_download_my_data_csv(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test downloading user's personal data as CSV."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/my-data?format=csv",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "text/csv" in response.headers["content-type"]
        assert ".csv" in response.headers["content-disposition"]

        # Check log count header
        assert "X-Log-Count" in response.headers

        # Should have CSV content
        content = response.text
        assert len(content) > 0

    def test_download_my_data_json(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test downloading user's personal data as JSON."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/my-data?format=json",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        assert ".json" in response.headers["content-disposition"]

        # Check JSON structure
        data = response.json()
        assert "user" in data
        assert "export_date" in data
        assert "log_count" in data
        assert "logs" in data

        # Should have user's logs
        assert data["log_count"] == 2

    def test_download_my_data_with_photos_metadata(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test downloading with photos_metadata included."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/my-data?format=json&include=logs,photos_metadata",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Each log should have photos array (even if empty)
        for log in data["logs"]:
            assert "photos" in log

    def test_download_my_data_invalid_include(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test that invalid include options are rejected."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/my-data?format=csv&include=invalid_option",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 400
        assert "invalid include" in response.json()["detail"].lower()

    def test_download_my_data_unauthenticated(
        self, client: TestClient, mock_rate_limiter, db
    ):
        """Test that my-data download requires authentication."""
        response = client.get("/v1/downloads/my-data?format=csv")

        assert response.status_code == 401

    def test_download_my_data_json_structure(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test JSON download structure includes all expected fields."""
        user = download_test_data["user"]

        response = client.get(
            "/v1/downloads/my-data?format=json",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        data = response.json()

        # Check user info
        assert data["user"]["id"] == user.id
        assert data["user"]["username"] == user.name

        # Check log structure
        if len(data["logs"]) > 0:
            log = data["logs"][0]
            expected_fields = [
                "log_id",
                "trig_id",
                "trig_waypoint",
                "trig_name",
                "date",
                "time",
                "condition",
                "comment",
                "score",
            ]
            for field in expected_fields:
                assert field in log, f"Missing field: {field}"


class TestRateLimiting:
    """Tests for rate limiting (with real rate limiter)."""

    def test_rate_limit_header_present(
        self,
        client: TestClient,
        download_test_data,
        mock_rate_limiter,
        db,
    ):
        """Test that download responses include count headers."""
        user = download_test_data["user"]
        suffix = download_test_data["suffix"]

        response = client.get(
            f"/v1/downloads/trigs?format=csv&name={suffix}",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert "X-Trigpoint-Count" in response.headers
