"""
Coverage tests for /v1/debug/auth0 endpoint branches.
"""

from fastapi.testclient import TestClient

from api.core.config import settings


def test_debug_auth0_requires_auth(client: TestClient):
    r = client.get(f"{settings.API_V1_STR}/debug/auth0")
    assert r.status_code == 401
    assert "Authentication required" in r.json().get("detail", "")


def test_debug_auth0_invalid_token(client: TestClient, monkeypatch):
    # Ensure validator returns None to simulate invalid token
    monkeypatch.setattr(
        "api.core.security.auth0_validator.validate_auth0_token",
        lambda t: None,
        raising=False,
    )
    r = client.get(
        f"{settings.API_V1_STR}/debug/auth0",
        headers={"Authorization": "Bearer invalid"},
    )
    assert r.status_code == 401
    assert "Invalid token" in r.json().get("detail", "")


def test_debug_auth0_valid_token_with_db_user(client: TestClient, monkeypatch):
    # Simulate valid auth0 token and existing DB user
    token_payload = {"token_type": "auth0", "sub": "auth0|xyz", "email": "e@test"}
    # Patch where the endpoint imports it
    monkeypatch.setattr(
        "api.core.security.auth0_validator.validate_auth0_token",
        lambda t: token_payload,
        raising=False,
    )

    class U:
        id = 7
        name = "dbuser"
        email = "e@test"

    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_auth0_id", lambda db, auth0_user_id: U()
    )

    r = client.get(
        f"{settings.API_V1_STR}/debug/auth0",
        headers={"Authorization": "Bearer good"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["database_user_found"] is True
    assert data["database_user_id"] == 7


def test_debug_auth0_user_found_by_email(client: TestClient, monkeypatch):
    """Test fallback to email lookup when auth0_id not found."""
    token_payload = {
        "token_type": "auth0",
        "sub": "auth0|unknown",
        "email": "found@test.com",
        "nickname": "testuser",
    }
    monkeypatch.setattr(
        "api.core.security.auth0_validator.validate_auth0_token",
        lambda t: token_payload,
    )

    class U:
        id = 42
        name = "emailuser"
        email = "found@test.com"

    # auth0_id lookup returns None, email lookup returns user
    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_auth0_id",
        lambda db, auth0_user_id: None,
    )
    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_email", lambda db, email: U()
    )

    r = client.get(
        f"{settings.API_V1_STR}/debug/auth0",
        headers={"Authorization": "Bearer good"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["database_user_found"] is True
    assert data["database_user_id"] == 42
    assert data["database_username"] == "emailuser"


def test_debug_auth0_user_found_by_nickname(client: TestClient, monkeypatch):
    """Test fallback to nickname lookup when auth0_id and email not found."""
    token_payload = {
        "token_type": "auth0",
        "sub": "auth0|unknown",
        "email": "notfound@test.com",
        "nickname": "knownuser",
    }
    monkeypatch.setattr(
        "api.core.security.auth0_validator.validate_auth0_token",
        lambda t: token_payload,
    )

    class U:
        id = 99
        name = "knownuser"
        email = "actual@test.com"

    # auth0_id and email lookups return None, nickname lookup returns user
    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_auth0_id",
        lambda db, auth0_user_id: None,
    )
    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_email", lambda db, email: None
    )
    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_name", lambda db, name: U()
    )

    r = client.get(
        f"{settings.API_V1_STR}/debug/auth0",
        headers={"Authorization": "Bearer good"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["database_user_found"] is True
    assert data["database_user_id"] == 99
    assert data["database_username"] == "knownuser"


def test_debug_auth0_user_not_found_anywhere(client: TestClient, monkeypatch):
    """Test when user is not found by any method."""
    token_payload = {
        "token_type": "auth0",
        "sub": "auth0|unknown",
        "email": "notfound@test.com",
        "nickname": "unknownuser",
    }
    monkeypatch.setattr(
        "api.core.security.auth0_validator.validate_auth0_token",
        lambda t: token_payload,
    )

    # All lookups return None
    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_auth0_id",
        lambda db, auth0_user_id: None,
    )
    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_email", lambda db, email: None
    )
    monkeypatch.setattr(
        "api.api.v1.endpoints.debug.get_user_by_name", lambda db, name: None
    )

    r = client.get(
        f"{settings.API_V1_STR}/debug/auth0",
        headers={"Authorization": "Bearer good"},
    )
    assert r.status_code == 200
    data = r.json()
    assert data["database_user_found"] is False
    assert data["database_user_id"] is None
