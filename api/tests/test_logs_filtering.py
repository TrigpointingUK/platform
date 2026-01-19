"""
Tests for logs filtering functionality.

Tests the new filtering parameters added to the /v1/logs endpoint:
- groups: Filter by trigpoint type group codes
- lat/lon/max_km: Filter by distance from a location
- from_date/to_date: Filter by date range
- area_id: Filter by area (not tested here as it requires area data)
"""

from datetime import date

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

    def test_list_logs_with_groups_param(self, client: TestClient):
        """Test that groups parameter is accepted."""
        resp = client.get(f"{settings.API_V1_STR}/logs?groups=PILLAR")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_multiple_groups(self, client: TestClient):
        """Test that multiple groups are accepted."""
        resp = client.get(f"{settings.API_V1_STR}/logs?groups=PILLAR,FBM,SURVEY_MARK")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_location_params(self, client: TestClient):
        """Test that lat/lon/max_km parameters are accepted."""
        resp = client.get(f"{settings.API_V1_STR}/logs?lat=52.0&lon=-1.5&max_km=100")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_combined_filter_params(self, client: TestClient):
        """Test that groups and location parameters can be combined."""
        resp = client.get(
            f"{settings.API_V1_STR}/logs"
            "?lat=52.0&lon=-1.5&max_km=100"
            "&groups=PILLAR,FBM"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_from_date_param(self, client: TestClient):
        """Test that from_date parameter is accepted."""
        resp = client.get(f"{settings.API_V1_STR}/logs?from_date=2024-01-01")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_to_date_param(self, client: TestClient):
        """Test that to_date parameter is accepted."""
        resp = client.get(f"{settings.API_V1_STR}/logs?to_date=2024-12-31")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_logs_with_date_range_params(self, client: TestClient):
        """Test that from_date and to_date parameters can be combined."""
        resp = client.get(
            f"{settings.API_V1_STR}/logs?from_date=2024-01-01&to_date=2024-12-31"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body


class TestLogsFilteringLinks:
    """Tests for pagination links with filter parameters."""

    def test_list_logs_links_include_groups(self, client: TestClient):
        """Test that pagination links include groups parameter."""
        resp = client.get(f"{settings.API_V1_STR}/logs?groups=PILLAR&limit=1")
        assert resp.status_code == 200
        body = resp.json()
        assert "groups=PILLAR" in body["links"]["self"]

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

    def test_list_logs_links_include_from_date(self, client: TestClient):
        """Test that pagination links include from_date parameter."""
        resp = client.get(f"{settings.API_V1_STR}/logs?from_date=2024-01-01&limit=1")
        assert resp.status_code == 200
        body = resp.json()
        assert "from_date=2024-01-01" in body["links"]["self"]

    def test_list_logs_links_include_to_date(self, client: TestClient):
        """Test that pagination links include to_date parameter."""
        resp = client.get(f"{settings.API_V1_STR}/logs?to_date=2024-12-31&limit=1")
        assert resp.status_code == 200
        body = resp.json()
        assert "to_date=2024-12-31" in body["links"]["self"]


class TestLogsCrudFiltering:
    """Tests for tlog CRUD filtering functions."""

    def test_list_logs_filtered_accepts_category_codes(self, db: Session):
        """Test CRUD list_logs_filtered accepts category_codes parameter."""
        # Should not raise an error
        logs = tlog_crud.list_logs_filtered(db, category_codes=["PILLAR"])
        assert isinstance(logs, list)

    def test_list_logs_filtered_accepts_multiple_category_codes(self, db: Session):
        """Test CRUD list_logs_filtered accepts multiple category_codes."""
        logs = tlog_crud.list_logs_filtered(
            db, category_codes=["PILLAR", "FBM", "SURVEY_MARK"]
        )
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
            category_codes=["PILLAR", "FBM"],
            center_lat=52.0,
            center_lon=-1.5,
            max_km=100,
        )
        assert isinstance(logs, list)

    def test_count_logs_filtered_accepts_category_codes(self, db: Session):
        """Test CRUD count_logs_filtered accepts category_codes parameter."""
        count = tlog_crud.count_logs_filtered(db, category_codes=["PILLAR"])
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
            category_codes=["PILLAR", "FBM"],
            center_lat=52.0,
            center_lon=-1.5,
            max_km=100,
        )
        assert isinstance(count, int)
        assert count >= 0

    def test_list_logs_filtered_accepts_from_date(self, db: Session):
        """Test CRUD list_logs_filtered accepts from_date parameter."""
        logs = tlog_crud.list_logs_filtered(db, from_date=date(2024, 1, 1))
        assert isinstance(logs, list)

    def test_list_logs_filtered_accepts_to_date(self, db: Session):
        """Test CRUD list_logs_filtered accepts to_date parameter."""
        logs = tlog_crud.list_logs_filtered(db, to_date=date(2024, 12, 31))
        assert isinstance(logs, list)

    def test_list_logs_filtered_accepts_date_range(self, db: Session):
        """Test CRUD list_logs_filtered accepts from_date and to_date together."""
        logs = tlog_crud.list_logs_filtered(
            db, from_date=date(2024, 1, 1), to_date=date(2024, 12, 31)
        )
        assert isinstance(logs, list)

    def test_count_logs_filtered_accepts_from_date(self, db: Session):
        """Test CRUD count_logs_filtered accepts from_date parameter."""
        count = tlog_crud.count_logs_filtered(db, from_date=date(2024, 1, 1))
        assert isinstance(count, int)
        assert count >= 0

    def test_count_logs_filtered_accepts_to_date(self, db: Session):
        """Test CRUD count_logs_filtered accepts to_date parameter."""
        count = tlog_crud.count_logs_filtered(db, to_date=date(2024, 12, 31))
        assert isinstance(count, int)
        assert count >= 0

    def test_count_logs_filtered_accepts_date_range(self, db: Session):
        """Test CRUD count_logs_filtered accepts from_date and to_date together."""
        count = tlog_crud.count_logs_filtered(
            db, from_date=date(2024, 1, 1), to_date=date(2024, 12, 31)
        )
        assert isinstance(count, int)
        assert count >= 0
