"""
Tests for the /v1/admin/osnet endpoint.

Tests admin authorization and response structure for OS Net comparison.
"""

import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud.user import create_user
from api.services.osnet_service import (
    SECTION_CURRENT,
    SECTION_DESTROYED,
    OSNetComparisonResult,
    StationDifference,
)


@pytest.fixture
def admin_user(db: Session):
    """Create an admin user for testing."""
    unique_suffix = uuid.uuid4().hex[:8]
    user = create_user(
        db=db,
        username=f"osnet_admin_{unique_suffix}",
        email=f"osnet_admin_{unique_suffix}@example.com",
        auth0_user_id=f"auth0|osnet_admin_{unique_suffix}",
    )
    return user


@pytest.fixture
def non_admin_user(db: Session):
    """Create a non-admin user for testing."""
    unique_suffix = uuid.uuid4().hex[:8]
    user = create_user(
        db=db,
        username=f"osnet_user_{unique_suffix}",
        email=f"osnet_user_{unique_suffix}@example.com",
        auth0_user_id=f"auth0|osnet_user_{unique_suffix}",
    )
    return user


@pytest.fixture
def admin_auth_mock(admin_user):
    """Mock authentication to return admin token using real user."""

    def _mock():
        return {
            "token_type": "auth0",
            "auth0_user_id": admin_user.auth0_user_id,
            "sub": admin_user.auth0_user_id,
            "scope": "api:write api:admin",
        }

    return _mock


@pytest.fixture
def non_admin_auth_mock(non_admin_user):
    """Mock authentication to return non-admin token using real user."""

    def _mock():
        return {
            "token_type": "auth0",
            "auth0_user_id": non_admin_user.auth0_user_id,
            "sub": non_admin_user.auth0_user_id,
            "scope": "api:write",  # Missing api:admin
        }

    return _mock


@pytest.fixture
def mock_comparison_result():
    """Create a mock comparison result."""
    return OSNetComparisonResult(
        osnet_count=150,
        osnet_current_count=120,
        osnet_legacy_count=10,
        osnet_destroyed_count=20,
        db_count=100,
        matched_count=95,
        differences=[
            StationDifference(
                station_code="NEW1",
                difference_type="new_in_osnet",
                description="Current station NEW1 in OS Net but not in database",
                osnet_data={
                    "code": "NEW1",
                    "easting": 100000.0,
                    "northing": 200000.0,
                    "gridref": "AA0000",
                    "height": 50.0,
                    "lat_dms": "N 50 00 00",
                    "lon_dms": "W 001 00 00",
                },
                osnet_section=SECTION_CURRENT,
            ),
            StationDifference(
                station_code="MISS",
                difference_type="missing_from_osnet",
                description="Station MISS in database but not found in OS Net",
                db_data={
                    "trig_id": 99,
                    "waypoint": "TP0099",
                    "name": "Missing Station",
                    "stn_number_active": "MISS",
                    "easting": 500000,
                    "northing": 600000,
                    "gridref": "ZZ9999",
                },
            ),
            StationDifference(
                station_code="DEST",
                difference_type="destroyed_not_in_db",
                description="Destroyed station DEST not in database (informational)",
                osnet_data={
                    "code": "DEST",
                    "easting": 300000.0,
                    "northing": 400000.0,
                    "gridref": "CC0000",
                    "height": 75.0,
                    "lat_dms": "N 51 00 00",
                    "lon_dms": "W 002 00 00",
                },
                osnet_section=SECTION_DESTROYED,
            ),
        ],
        osnet_fetch_time=datetime.now(),
        changelog_entries=[
            "2026-01-15. New station TEST added.",
            "2025-12-18. Station OLD destroyed.",
        ],
    )


class TestOSNetComparisonEndpointAuth:
    """Tests for authorization on the OS Net comparison endpoint."""

    def test_no_auth_returns_401(self, client: TestClient):
        """Test that unauthenticated requests return 401."""
        response = client.get(f"{settings.API_V1_STR}/admin/osnet/comparison")
        assert response.status_code == 401

    def test_non_admin_returns_403(self, client: TestClient, non_admin_auth_mock):
        """Test that non-admin users get 403."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )
        assert response.status_code == 403

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_admin_can_access(
        self, mock_compare, client: TestClient, admin_auth_mock, mock_comparison_result
    ):
        """Test that admin users can access the endpoint."""
        mock_compare.return_value = mock_comparison_result

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 200


class TestOSNetComparisonEndpointResponse:
    """Tests for the response structure of the OS Net comparison endpoint."""

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_response_structure(
        self, mock_compare, client: TestClient, admin_auth_mock, mock_comparison_result
    ):
        """Test that the response has the correct structure."""
        mock_compare.return_value = mock_comparison_result

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 200
        data = response.json()

        # Check top-level fields
        assert "osnet_count" in data
        assert "osnet_current_count" in data
        assert "osnet_legacy_count" in data
        assert "osnet_destroyed_count" in data
        assert "db_count" in data
        assert "matched_count" in data
        assert "differences" in data
        assert "osnet_fetch_time" in data
        assert "changelog_entries" in data

        # Check summary counts
        assert "new_in_osnet_count" in data
        assert "missing_from_osnet_count" in data
        assert "coordinate_mismatch_count" in data
        assert "unmatched_db_count" in data
        assert "destroyed_not_in_db_count" in data
        assert "legacy_not_in_db_count" in data

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_response_counts(
        self, mock_compare, client: TestClient, admin_auth_mock, mock_comparison_result
    ):
        """Test that counts are correctly calculated."""
        mock_compare.return_value = mock_comparison_result

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )

        data = response.json()

        assert data["osnet_count"] == 150
        assert data["osnet_current_count"] == 120
        assert data["osnet_legacy_count"] == 10
        assert data["osnet_destroyed_count"] == 20
        assert data["db_count"] == 100
        assert data["matched_count"] == 95

        # Summary counts should match the mock differences
        assert data["new_in_osnet_count"] == 1
        assert data["missing_from_osnet_count"] == 1
        assert data["destroyed_not_in_db_count"] == 1
        assert data["coordinate_mismatch_count"] == 0
        assert data["unmatched_db_count"] == 0
        assert data["legacy_not_in_db_count"] == 0

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_difference_structure(
        self, mock_compare, client: TestClient, admin_auth_mock, mock_comparison_result
    ):
        """Test that differences have the correct structure."""
        mock_compare.return_value = mock_comparison_result

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )

        data = response.json()
        differences = data["differences"]

        assert len(differences) == 3

        # Check new_in_osnet difference
        new_diff = next(
            d for d in differences if d["difference_type"] == "new_in_osnet"
        )
        assert new_diff["station_code"] == "NEW1"
        assert new_diff["osnet_data"] is not None
        assert new_diff["osnet_data"]["code"] == "NEW1"
        assert new_diff["osnet_section"] == SECTION_CURRENT
        assert new_diff["osnet_section_name"] == "Current (v2009)"

        # Check missing_from_osnet difference
        missing_diff = next(
            d for d in differences if d["difference_type"] == "missing_from_osnet"
        )
        assert missing_diff["station_code"] == "MISS"
        assert missing_diff["db_data"] is not None
        assert missing_diff["db_data"]["trig_id"] == 99

        # Check destroyed_not_in_db difference
        destroyed_diff = next(
            d for d in differences if d["difference_type"] == "destroyed_not_in_db"
        )
        assert destroyed_diff["station_code"] == "DEST"
        assert destroyed_diff["osnet_section"] == SECTION_DESTROYED
        assert destroyed_diff["osnet_section_name"] == "Destroyed/Moved"

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_changelog_entries(
        self, mock_compare, client: TestClient, admin_auth_mock, mock_comparison_result
    ):
        """Test that changelog entries are included."""
        mock_compare.return_value = mock_comparison_result

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )

        data = response.json()
        changelog = data["changelog_entries"]

        assert len(changelog) == 2
        assert "2026-01-15" in changelog[0]
        assert "2025-12-18" in changelog[1]


class TestOSNetComparisonEndpointForceRefresh:
    """Tests for force_refresh parameter."""

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_force_refresh_false_by_default(
        self, mock_compare, client: TestClient, admin_auth_mock, mock_comparison_result
    ):
        """Test that force_refresh defaults to False."""
        mock_compare.return_value = mock_comparison_result

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 200
        mock_compare.assert_called_once()
        call_kwargs = mock_compare.call_args[1]
        assert call_kwargs["force_refresh"] is False

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_force_refresh_true(
        self, mock_compare, client: TestClient, admin_auth_mock, mock_comparison_result
    ):
        """Test that force_refresh=true is passed through."""
        mock_compare.return_value = mock_comparison_result

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison?force_refresh=true",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 200
        mock_compare.assert_called_once()
        call_kwargs = mock_compare.call_args[1]
        assert call_kwargs["force_refresh"] is True


class TestOSNetComparisonEndpointErrors:
    """Tests for error handling."""

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_runtime_error_returns_503(
        self, mock_compare, client: TestClient, admin_auth_mock
    ):
        """Test that RuntimeError (fetch failure) returns 503."""
        mock_compare.side_effect = RuntimeError("Failed to fetch OS Net data")

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 503
        assert "Failed to fetch OS Net data" in response.json()["detail"]

    @patch("api.api.v1.endpoints.osnet_admin.compare_osnet_with_db")
    def test_general_exception_returns_500(
        self, mock_compare, client: TestClient, admin_auth_mock
    ):
        """Test that unexpected exceptions return 500."""
        mock_compare.side_effect = Exception("Unexpected error")

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.get(
                f"{settings.API_V1_STR}/admin/osnet/comparison",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 500
        assert "error occurred" in response.json()["detail"]


class TestOSNetCacheClearEndpoint:
    """Tests for the cache clear endpoint."""

    def test_no_auth_returns_401(self, client: TestClient):
        """Test that unauthenticated requests return 401."""
        response = client.post(f"{settings.API_V1_STR}/admin/osnet/cache/clear")
        assert response.status_code == 401

    def test_non_admin_returns_403(self, client: TestClient, non_admin_auth_mock):
        """Test that non-admin users get 403."""
        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = non_admin_auth_mock()
            response = client.post(
                f"{settings.API_V1_STR}/admin/osnet/cache/clear",
                headers={"Authorization": "Bearer fake_token"},
            )
        assert response.status_code == 403

    @patch("api.services.osnet_service.OSNetCache")
    def test_admin_can_clear_cache(
        self, mock_cache_class, client: TestClient, admin_auth_mock
    ):
        """Test that admin users can clear the cache."""
        mock_cache = MagicMock()
        mock_cache_class.get_instance.return_value = mock_cache

        with patch("api.api.deps.auth0_validator.validate_auth0_token") as mock:
            mock.return_value = admin_auth_mock()
            response = client.post(
                f"{settings.API_V1_STR}/admin/osnet/cache/clear",
                headers={"Authorization": "Bearer fake_token"},
            )

        assert response.status_code == 204
        mock_cache.clear.assert_called_once()
