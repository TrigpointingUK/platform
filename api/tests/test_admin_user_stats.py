"""Tests for the admin user stats refresh endpoint."""

from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from api.api.v1.endpoints import admin as admin_endpoints
from api.main import app

client = TestClient(app)


def test_refresh_user_stats_requires_admin_scope():
    """The endpoint should reject callers without api:admin scope."""

    def deny_scope():
        raise HTTPException(status_code=403, detail="Missing required scope: api:admin")

    app.dependency_overrides[admin_endpoints.ADMIN_SCOPE_DEPENDENCY] = deny_scope
    try:
        response = client.post("/v1/admin/user-stats/refresh")
    finally:
        app.dependency_overrides.pop(admin_endpoints.ADMIN_SCOPE_DEPENDENCY, None)

    assert response.status_code == 403
    assert "api:admin" in response.json()["detail"]


def test_refresh_user_stats_triggers_refresh():
    """An admin request should run the refresh helper and return 202."""
    with patch(
        "api.api.v1.endpoints.admin.refresh_user_activity_summary"
    ) as mock_refresh:
        app.dependency_overrides[admin_endpoints.ADMIN_SCOPE_DEPENDENCY] = (
            lambda: SimpleNamespace(id=1, _token_payload={"scope": "api:admin"})
        )
        try:
            response = client.post(
                "/v1/admin/user-stats/refresh",
                headers={"Authorization": "Bearer token"},
            )
        finally:
            app.dependency_overrides.pop(admin_endpoints.ADMIN_SCOPE_DEPENDENCY, None)

        assert response.status_code == 202
        mock_refresh.assert_called_once()
        args, kwargs = mock_refresh.call_args
        # First positional argument is the DB session
        assert "concurrently" in kwargs and kwargs["concurrently"] is True
        assert args, "Expected DB session to be passed to refresh helper"
