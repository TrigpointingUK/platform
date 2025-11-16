"""
Tests for CRUD operations.
"""

import pytest
from sqlalchemy.orm import Session

from api.crud.tlog import get_trig_count
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


@pytest.mark.skip(
    reason="Test expects specific count incompatible with shared PostgreSQL database."
)
def test_get_trig_count_with_data(db: Session, test_tlog_entries):
    """Test getting trig count with existing data."""
    count = get_trig_count(db, 1)
    assert count == 3

    count = get_trig_count(db, 2)
    assert count == 2


def test_get_trig_count_no_data(db: Session):
    """Test getting trig count with no data."""
    count = get_trig_count(db, 999)
    assert count == 0


@pytest.mark.skip(
    reason="Test expects empty database incompatible with shared PostgreSQL database."
)
def test_get_trig_count_empty_table(db: Session):
    """Test getting trig count from empty table."""
    count = get_trig_count(db, 1)
    assert count == 0
