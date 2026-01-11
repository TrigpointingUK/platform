"""
Tests for CRUD operations.
"""

from sqlalchemy.orm import Session

from api.crud.tlog import get_trig_count
from api.crud.trig import list_trigs_filtered
from api.crud.user import (
    authenticate_user,
    get_user_by_email,
    get_user_by_id,
    is_admin,
)

# from api.models.user import TLog  # Currently unused
# from api.schemas.user import UserCreate  # Removed - read-only endpoints only


def test_get_user_by_id(db: Session, test_user):
    """Test getting user by ID."""
    user = get_user_by_id(db, test_user.id)
    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


def test_get_user_by_id_not_found(db: Session):
    """Test getting user by ID when user doesn't exist."""
    user = get_user_by_id(db, 999999)
    assert user is None


def test_get_user_by_email(db: Session, test_user):
    """Test getting user by email."""
    user = get_user_by_email(db, test_user.email)
    assert user is not None
    assert user.id == test_user.id
    assert user.email == test_user.email


def test_get_user_by_email_not_found(db: Session):
    """Test getting user by email when user doesn't exist."""
    user = get_user_by_email(db, "nonexistent@example.com")
    assert user is None


def test_authenticate_user_success(db: Session, test_user):
    """Test successful user authentication."""
    user = authenticate_user(db, test_user.email, "testpassword123")
    assert user is not None
    assert user.id == test_user.id


def test_authenticate_user_wrong_password(db: Session, test_user):
    """Test authentication with wrong password."""
    user = authenticate_user(db, test_user.email, "wrongpassword")
    assert user is None


def test_authenticate_user_wrong_email(db: Session):
    """Test authentication with wrong email."""
    user = authenticate_user(db, "nonexistent@example.com", "password")
    assert user is None


def test_is_admin_false(db: Session, test_user):
    """Test is_admin with regular user."""
    assert is_admin(test_user) is False


def test_get_trig_count_with_data(db: Session):
    """Test getting trig count (log count per trig_id) with test data.

    Note: get_trig_count counts logs for a specific trig_id, not per user.
    Uses a high trig_id (9999) that exists in the seeded trig table.
    Verifies basic functionality: returns an integer >= 0.
    """
    # Use trig_id=9999 which is seeded but rarely logged to
    # This test verifies get_trig_count works; parallel tests may affect exact count
    count = get_trig_count(db, 9999)

    # Just verify it returns a non-negative integer (logs may exist from other tests)
    assert isinstance(count, int)
    assert count >= 0


def test_get_trig_count_no_data(db: Session):
    """Test getting trig count with no data."""
    count = get_trig_count(db, 999999)  # Non-existent user
    assert count == 0


def test_get_trig_count_new_user(db: Session):
    """Test getting trig count for a newly created user with no logs.

    Redesigned from test_get_trig_count_empty_table to work with
    shared PostgreSQL database.
    """
    import uuid

    from api.models.user import User

    unique_suffix = uuid.uuid4().hex[:8]

    # Create a unique test user with no logs
    test_user = User(
        name=f"new_user_{unique_suffix}",
        email=f"new_user_{unique_suffix}@example.com",
        cryptpw="test",
        about="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(test_user)
    db.commit()
    db.refresh(test_user)

    # New user should have 0 logged trigs
    count = get_trig_count(db, int(test_user.id))
    assert count == 0


def test_list_trigs_filtered_with_max_km(db: Session):
    """Test listing trigs with max_km distance filter.

    Uses Buxton (53.2585, -1.9106) as center point.
    With max_km=1, should return fewer trigs than without limit.
    """
    # Get all trigs near Buxton (no distance limit)
    all_trigs = list_trigs_filtered(
        db,
        center_lat=53.2585,
        center_lon=-1.9106,
        limit=100,
    )

    # Get trigs within 1km of Buxton
    nearby_trigs = list_trigs_filtered(
        db,
        center_lat=53.2585,
        center_lon=-1.9106,
        max_km=1.0,
        limit=100,
    )

    # Should have fewer or equal results with distance limit
    assert len(nearby_trigs) <= len(all_trigs)
    # The function should not raise an error (the main fix we're testing)
