"""
Tests for user endpoints.
"""

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.user import User


def test_get_user_not_found(client: TestClient, db: Session):
    """Test getting a non-existent user returns 404."""
    response = client.get(f"{settings.API_V1_STR}/users/99999")
    assert response.status_code == 404
    assert response.json()["detail"] == "User not found"


def test_get_user_public_unauthenticated(client: TestClient, db: Session):
    """Test getting a public user while unauthenticated."""
    # Create a test user with public profile
    import uuid

    unique_name = f"testuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=unique_name,
        firstname="Test",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="$1$test$hash",
        about="Test user bio",
        email_valid="Y",
        public_ind="Y",  # Public profile
    )
    db.add(user)
    db.commit()
    db.refresh(user)  # Get the auto-generated ID

    response = client.get(f"{settings.API_V1_STR}/users/{user.id}")
    assert response.status_code == 200
    data = response.json()

    # Should include basic fields and public email in base response
    assert data["id"] == user.id
    assert data["name"] == unique_name
    assert data["firstname"] == "Test"
    assert data["surname"] == "User"
    assert data["about"] == "Test user bio"
    # Email field deprecated - no longer returned


def test_get_user_private_unauthenticated(client: TestClient, db: Session):
    """Test getting a private user while unauthenticated."""
    # Create a test user with private profile
    import uuid

    unique_name = f"privateuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=unique_name,
        firstname="Private",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw="$1$test$hash",
        about="Private user bio",
        email_valid="Y",
        public_ind="N",  # Private profile
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    response = client.get(f"{settings.API_V1_STR}/users/{user.id}")
    assert response.status_code == 200
    data = response.json()

    # Should include basic fields
    assert data["id"] == user.id
    assert data["name"] == unique_name
    assert data["firstname"] == "Private"
    assert data["surname"] == "User"
    assert data["about"] == "Private user bio"

    # Email field deprecated - no longer returned


# removed name lookup endpoint tests


def test_list_users_envelope_and_filter(client: TestClient, db: Session):
    """Test users list envelope, pagination, and name filter."""
    import uuid

    suffix = uuid.uuid4().hex[:6]
    users = [
        User(
            name=f"alice_{suffix}",
            firstname="Alice",
            surname="Smith",
            email=f"alice_{suffix}@test.com",
            cryptpw="$1$test$hash",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"bob_{suffix}",
            firstname="Bob",
            surname="Jones",
            email=f"bob_{suffix}@test.com",
            cryptpw="$1$test$hash",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"charlie_{suffix}",
            firstname="Charlie",
            surname="Brown",
            email=f"charlie_{suffix}@test.com",
            cryptpw="$1$test$hash",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
    ]
    for u in users:
        db.add(u)
    db.commit()

    # No filter (all)
    resp = client.get(f"{settings.API_V1_STR}/users")
    assert resp.status_code == 200
    body = resp.json()
    assert "items" in body and "pagination" in body and "links" in body
    assert len(body["items"]) >= 3

    # Filter by name contains 'li' - should include alice and charlie
    resp = client.get(f"{settings.API_V1_STR}/users?name=li")
    assert resp.status_code == 200
    # Check for our test users with dynamic suffixes
    # In a shared DB with parallel tests, filter by the unique suffix to be more precise
    resp_suffix = client.get(f"{settings.API_V1_STR}/users?name={suffix}")
    assert resp_suffix.status_code == 200
    body_suffix = resp_suffix.json()
    suffix_names = [u["name"] for u in body_suffix["items"]]
    # All 3 users should match when filtering by suffix
    assert len(suffix_names) >= 3
    assert f"alice_{suffix}" in suffix_names
    assert f"charlie_{suffix}" in suffix_names
    assert f"bob_{suffix}" in suffix_names

    # Envelope structure with pagination
    resp = client.get(f"{settings.API_V1_STR}/users?limit=1&skip=0")
    assert resp.status_code == 200
    body = resp.json()
    assert body["pagination"]["limit"] == 1
    assert body["pagination"]["offset"] == 0
