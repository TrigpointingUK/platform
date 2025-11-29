"""
Tests for CRUD email-related functions.
"""

from sqlalchemy.orm import Session

from api.crud.user import find_duplicate_emails, get_all_emails, get_users_by_email
from api.models.user import User


def test_get_all_emails_empty_database(db: Session):
    """Test get_all_emails with empty database."""
    # Note: Shared database may have data from other tests, so this test
    # is really checking that the function returns a list
    emails = get_all_emails(db)
    assert isinstance(emails, list)


def test_get_all_emails_with_users(db: Session):
    """Test get_all_emails with users having emails."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    users = [
        User(
            name=f"user1_{unique_suffix}",
            email=f"user1_{unique_suffix}@example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user2_{unique_suffix}",
            email=f"user2_{unique_suffix}@example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user3_{unique_suffix}",
            email=f"user3_{unique_suffix}@example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
    ]
    for user in users:
        db.add(user)
    db.commit()

    emails = get_all_emails(db)
    # Check that our test emails are in the list
    assert f"user1_{unique_suffix}@example.com" in emails
    assert f"user2_{unique_suffix}@example.com" in emails
    assert f"user3_{unique_suffix}@example.com" in emails


def test_get_all_emails_with_none_emails(db: Session):
    """Test get_all_emails with users having None emails."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    users = [
        User(
            name=f"user1_{unique_suffix}",
            email=f"user1_{unique_suffix}@example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user2_{unique_suffix}",
            email=None,
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user3_{unique_suffix}",
            email=f"user3_{unique_suffix}@example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
    ]
    for user in users:
        db.add(user)
    db.commit()

    emails = get_all_emails(db)
    # Check that our test emails are in the list (but not None)
    assert f"user1_{unique_suffix}@example.com" in emails
    assert f"user3_{unique_suffix}@example.com" in emails
    # The None email should not be in the list
    assert None not in emails


def test_find_duplicate_emails_no_duplicates(db: Session):
    """Test find_duplicate_emails with no duplicates."""
    emails = ["user1@example.com", "user2@example.com", "user3@example.com"]
    duplicates = find_duplicate_emails(emails)
    assert duplicates == {}


def test_find_duplicate_emails_with_duplicates(db: Session):
    """Test find_duplicate_emails with duplicates."""
    emails = [
        "user@example.com",
        "User@Example.com",  # Case variation
        "admin@test.com",
        "Admin@Test.com",  # Case variation
        "unique@example.com",
    ]
    duplicates = find_duplicate_emails(emails)

    assert len(duplicates) == 2
    assert "user@example.com" in duplicates
    assert "admin@test.com" in duplicates

    # Check that case variations are grouped together
    assert set(duplicates["user@example.com"]) == {
        "user@example.com",
        "User@Example.com",
    }
    assert set(duplicates["admin@test.com"]) == {"admin@test.com", "Admin@Test.com"}


def test_find_duplicate_emails_with_whitespace(db: Session):
    """Test find_duplicate_emails with whitespace variations."""
    emails = [
        "user@example.com",
        " user@example.com ",  # Whitespace
        "user@example.com\t",  # Tab
        "admin@test.com",
    ]
    duplicates = find_duplicate_emails(emails)

    assert len(duplicates) == 1
    assert "user@example.com" in duplicates
    assert len(duplicates["user@example.com"]) == 3


def test_find_duplicate_emails_empty_emails(db: Session):
    """Test find_duplicate_emails with empty emails."""
    emails = ["", "user@example.com", "  ", "admin@test.com"]
    duplicates = find_duplicate_emails(emails)

    # Should only find duplicates for valid emails
    assert len(duplicates) == 0


def test_get_users_by_email_exact_match(db: Session):
    """Test get_users_by_email with exact match."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]
    test_email = f"user_{unique_suffix}@example.com"

    users = [
        User(
            name=f"user1_{unique_suffix}",
            email=test_email,
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user2_{unique_suffix}",
            email=f"admin_{unique_suffix}@test.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user3_{unique_suffix}",
            email=test_email,
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
    ]
    for user in users:
        db.add(user)
    db.commit()

    found_users = get_users_by_email(db, test_email)
    assert len(found_users) == 2
    assert all(user.email == test_email for user in found_users)


def test_get_users_by_email_case_insensitive(db: Session):
    """Test get_users_by_email with case insensitive search."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    users = [
        User(
            name=f"user1_{unique_suffix}",
            email=f"user_{unique_suffix}@example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user2_{unique_suffix}",
            email=f"User_{unique_suffix}@Example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
    ]
    for user in users:
        db.add(user)
    db.commit()

    found_users = get_users_by_email(db, f"USER_{unique_suffix}@EXAMPLE.COM")
    assert len(found_users) == 2
    assert all(
        user.email.lower() == f"user_{unique_suffix}@example.com"
        for user in found_users
    )


def test_get_users_by_email_no_match(db: Session):
    """Test get_users_by_email with no matching users."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    users = [
        User(
            name=f"user1_{unique_suffix}",
            email=f"user_{unique_suffix}@example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user2_{unique_suffix}",
            email=f"admin_{unique_suffix}@test.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
    ]
    for user in users:
        db.add(user)
    db.commit()

    found_users = get_users_by_email(db, f"nonexistent_{unique_suffix}@example.com")
    assert found_users == []


def test_get_users_by_email_empty_string(db: Session):
    """Test get_users_by_email with empty string."""
    import uuid

    unique_suffix = uuid.uuid4().hex[:8]

    users = [
        User(
            name=f"user1_{unique_suffix}",
            email=f"user_{unique_suffix}@example.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
        User(
            name=f"user2_{unique_suffix}",
            email=f"admin_{unique_suffix}@test.com",
            cryptpw="test",
            about="",
            email_valid="Y",
            public_ind="Y",
        ),
    ]
    for user in users:
        db.add(user)
    db.commit()

    # Search for empty string
    found_users = get_users_by_email(db, "")
    # In shared database, may return users with empty emails from other tests
    # but should NOT return our test users with non-empty emails
    test_emails = [
        f"user_{unique_suffix}@example.com",
        f"admin_{unique_suffix}@test.com",
    ]
    assert not any(user.email in test_emails for user in found_users)
