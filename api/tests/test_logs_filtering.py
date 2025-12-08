"""
Tests for logs filtering functionality.

Tests the new filtering parameters added to the /v1/logs endpoint:
- status_ids: Filter by trigpoint status
- lat/lon/max_km: Filter by distance from a location
- area_id: Filter by area (not tested here as it requires area data)
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud import tlog as tlog_crud


class TestLogsFilteringEndpointParams:
    """Tests for /v1/logs filtering parameter handling."""

    def test_list_logs_no_filters(self, client: TestClient):
        """Test listing logs without any filters returns valid response."""
        resp = client.get(f"{settings.API_V1_STR}/logs")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "pagination" in body
        assert "links" in body

    def test_list_logs_with_status_ids_param(self, client: TestClient):
        """Test that status_ids parameter is accepted."""
        resp = client.get(f"{settings.API_V1_STR}/logs?status_ids=10")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_multiple_status_ids(self, client: TestClient):
        """Test that multiple status_ids are accepted."""
        resp = client.get(f"{settings.API_V1_STR}/logs?status_ids=10,20,30")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_invalid_status_ids(self, client: TestClient):
        """Test filtering with invalid status_ids format returns 400."""
        resp = client.get(f"{settings.API_V1_STR}/logs?status_ids=invalid")
        assert resp.status_code == 400
        body = resp.json()
        assert "Invalid status_ids format" in body["detail"]

    def test_list_logs_with_location_params(self, client: TestClient):
        """Test that lat/lon/max_km parameters are accepted."""
        resp = client.get(f"{settings.API_V1_STR}/logs?lat=52.0&lon=-1.5&max_km=100")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_combined_filter_params(self, client: TestClient):
        """Test that status_ids and location parameters can be combined."""
        resp = client.get(
            f"{settings.API_V1_STR}/logs"
            "?lat=52.0&lon=-1.5&max_km=100"
            "&status_ids=10,20"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body


class TestLogsFilteringLinks:
    """Tests for pagination links with filter parameters."""

    def test_list_logs_links_include_status_ids(self, client: TestClient):
        """Test that pagination links include status_ids parameter."""
        resp = client.get(f"{settings.API_V1_STR}/logs?status_ids=10&limit=1")
        assert resp.status_code == 200
        body = resp.json()
        assert "status_ids=10" in body["links"]["self"]

    def test_list_logs_links_include_location_params(self, client: TestClient):
        """Test that pagination links include location parameters."""
        resp = client.get(
            f"{settings.API_V1_STR}/logs?lat=52.0&lon=-1.5&max_km=50&limit=1"
        )
        assert resp.status_code == 200
        body = resp.json()
        links_self = body["links"]["self"]
        assert "lat=52.0" in links_self
        assert "lon=-1.5" in links_self
        assert "max_km=50" in links_self


class TestLogsCrudFiltering:
    """Tests for tlog CRUD filtering functions."""

    def test_list_logs_filtered_accepts_status_ids(self, db: Session):
        """Test CRUD list_logs_filtered accepts status_ids parameter."""
        # Should not raise an error
        logs = tlog_crud.list_logs_filtered(db, status_ids=[10])
        assert isinstance(logs, list)

    def test_list_logs_filtered_accepts_multiple_status_ids(self, db: Session):
        """Test CRUD list_logs_filtered accepts multiple status_ids."""
        logs = tlog_crud.list_logs_filtered(db, status_ids=[10, 20, 30])
        assert isinstance(logs, list)

    def test_list_logs_filtered_accepts_location_params(self, db: Session):
        """Test CRUD list_logs_filtered accepts location parameters."""
        logs = tlog_crud.list_logs_filtered(
            db, center_lat=52.0, center_lon=-1.5, max_km=100
        )
        assert isinstance(logs, list)

    def test_list_logs_filtered_accepts_combined_params(self, db: Session):
        """Test CRUD list_logs_filtered accepts combined parameters."""
        logs = tlog_crud.list_logs_filtered(
            db,
            status_ids=[10, 20],
            center_lat=52.0,
            center_lon=-1.5,
            max_km=100,
        )
        assert isinstance(logs, list)

    def test_count_logs_filtered_accepts_status_ids(self, db: Session):
        """Test CRUD count_logs_filtered accepts status_ids parameter."""
        count = tlog_crud.count_logs_filtered(db, status_ids=[10])
        assert isinstance(count, int)
        assert count >= 0

    def test_count_logs_filtered_accepts_location_params(self, db: Session):
        """Test CRUD count_logs_filtered accepts location parameters."""
        count = tlog_crud.count_logs_filtered(
            db, center_lat=52.0, center_lon=-1.5, max_km=100
        )
        assert isinstance(count, int)
        assert count >= 0

    def test_count_logs_filtered_accepts_combined_params(self, db: Session):
        """Test CRUD count_logs_filtered accepts combined parameters."""
        count = tlog_crud.count_logs_filtered(
            db,
            status_ids=[10, 20],
            center_lat=52.0,
            center_lon=-1.5,
            max_km=100,
        )
        assert isinstance(count, int)
        assert count >= 0
