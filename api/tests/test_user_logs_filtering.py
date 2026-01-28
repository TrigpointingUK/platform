"""
Tests for user logs filtering functionality.

Tests the filtering parameters added to the /v1/users/{user_id}/logs endpoint:
- groups: Filter by trigpoint type group codes
- lat/lon/max_km: Filter by distance from a location
- from_date/to_date: Filter by date range
- area_id: Filter by area
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.user import User


def _get_test_user_id(db: Session) -> int:
    """Get or create a test user for the tests."""
    user = db.query(User).first()
    if user:
        return int(user.id)
    # If no user exists, return a dummy ID (tests will still work for param validation)
    return 1


class TestUserLogsFilteringEndpointParams:
    """Tests for /v1/users/{user_id}/logs filtering parameter handling."""

    def test_list_user_logs_no_filters(self, client: TestClient, db: Session):
        """Test listing user logs without any filters returns valid response."""
        user_id = _get_test_user_id(db)
        resp = client.get(f"{settings.API_V1_STR}/users/{user_id}/logs")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body
        assert "pagination" in body
        assert "links" in body

    def test_list_user_logs_with_groups_param(self, client: TestClient, db: Session):
        """Test that groups parameter is accepted."""
        user_id = _get_test_user_id(db)
        resp = client.get(f"{settings.API_V1_STR}/users/{user_id}/logs?groups=PILLAR")
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_user_logs_with_multiple_groups(self, client: TestClient, db: Session):
        """Test that multiple groups are accepted."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs?groups=PILLAR,FBM,SURVEY_MARK"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_user_logs_with_location_params(self, client: TestClient, db: Session):
        """Test that lat/lon/max_km parameters are accepted."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs?lat=52.0&lon=-1.5&max_km=100"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_user_logs_with_combined_filter_params(
        self, client: TestClient, db: Session
    ):
        """Test that groups and location parameters can be combined."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs"
            "?lat=52.0&lon=-1.5&max_km=100"
            "&groups=PILLAR,FBM"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_user_logs_with_from_date_param(self, client: TestClient, db: Session):
        """Test that from_date parameter is accepted."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs?from_date=2024-01-01"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_user_logs_with_to_date_param(self, client: TestClient, db: Session):
        """Test that to_date parameter is accepted."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs?to_date=2024-12-31"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_user_logs_with_date_range_params(
        self, client: TestClient, db: Session
    ):
        """Test that from_date and to_date parameters can be combined."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs"
            "?from_date=2024-01-01&to_date=2024-12-31"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body

    def test_list_user_logs_with_all_filter_params_except_area(
        self, client: TestClient, db: Session
    ):
        """Test that all filter parameters (except area_id) can be combined.

        Note: area_id is not tested here as it requires the trig_area
        table which isn't present in the test database.
        """
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs"
            "?lat=52.0&lon=-1.5&max_km=100"
            "&groups=PILLAR,FBM,SURVEY_MARK"
            "&from_date=2024-01-01&to_date=2024-12-31"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "items" in body


class TestUserLogsFilteringLinks:
    """Tests for pagination links with filter parameters."""

    def test_list_user_logs_links_include_groups(self, client: TestClient, db: Session):
        """Test that pagination links include groups parameter."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs?groups=PILLAR&limit=1"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "groups=PILLAR" in body["links"]["self"]

    def test_list_user_logs_links_include_location_params(
        self, client: TestClient, db: Session
    ):
        """Test that pagination links include location parameters."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs"
            "?lat=52.0&lon=-1.5&max_km=50&limit=1"
        )
        assert resp.status_code == 200
        body = resp.json()
        links_self = body["links"]["self"]
        assert "lat=52.0" in links_self
        assert "lon=-1.5" in links_self
        assert "max_km=50" in links_self

    def test_list_user_logs_links_include_from_date(
        self, client: TestClient, db: Session
    ):
        """Test that pagination links include from_date parameter."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs?from_date=2024-01-01&limit=1"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "from_date=2024-01-01" in body["links"]["self"]

    def test_list_user_logs_links_include_to_date(
        self, client: TestClient, db: Session
    ):
        """Test that pagination links include to_date parameter."""
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs?to_date=2024-12-31&limit=1"
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "to_date=2024-12-31" in body["links"]["self"]

    def test_list_user_logs_links_include_all_params_except_area(
        self, client: TestClient, db: Session
    ):
        """Test that pagination links include all filter parameters.

        Note: area_id is not tested here as it requires the trig_area
        table which isn't present in the test database.
        """
        user_id = _get_test_user_id(db)
        resp = client.get(
            f"{settings.API_V1_STR}/users/{user_id}/logs"
            "?lat=52.0&lon=-1.5&max_km=50"
            "&groups=PILLAR,FBM"
            "&from_date=2024-01-01&to_date=2024-12-31"
            "&limit=1"
        )
        assert resp.status_code == 200
        body = resp.json()
        links_self = body["links"]["self"]
        assert "lat=52.0" in links_self
        assert "lon=-1.5" in links_self
        assert "max_km=50" in links_self
        assert "groups=PILLAR,FBM" in links_self or "groups=PILLAR%2CFBM" in links_self
        assert "from_date=2024-01-01" in links_self
        assert "to_date=2024-12-31" in links_self
