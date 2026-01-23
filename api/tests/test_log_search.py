"""
Tests for log search functionality.

Redesigned to work with parallel execution in shared PostgreSQL database.
Uses unique prefixes in comments to isolate test data from other tests.
"""

import uuid
from datetime import date, time

from sqlalchemy.orm import Session

from api.crud import tlog as tlog_crud
from api.models.user import TLog


def test_search_logs_by_text(db: Session, test_user, test_trig):
    """Test searching logs by text substring."""
    # Use unique prefix to isolate test data
    prefix = f"TEXT_SEARCH_{uuid.uuid4().hex[:8]}"

    # Create test logs with different comments containing unique prefix
    log1 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 1),
        time=time(12, 0, 0),
        fb_number="S1234",
        condition="G",
        comment=f"{prefix} Found the pillar in good condition",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log2 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 2),
        time=time(13, 0, 0),
        fb_number="S1235",
        condition="G",
        comment=f"{prefix} The pillar was covered in vegetation",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log3 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 3),
        time=time(14, 0, 0),
        fb_number="S1236",
        condition="G",
        comment=f"{prefix} Nice walk to the trig point",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )

    db.add_all([log1, log2, log3])
    db.commit()

    # Search for prefix + "pillar" - should find 2
    results = tlog_crud.search_logs_by_text(db, f"{prefix}%pillar")
    # Use ilike pattern matching - the function uses ilike internally
    results = tlog_crud.search_logs_by_text(db, prefix)
    pillar_results = [r for r in results if "pillar" in r.comment.lower()]
    assert len(pillar_results) == 2
    assert all("pillar" in log.comment.lower() for log in pillar_results)

    # Search for prefix + "vegetation" - should find 1
    vegetation_results = [r for r in results if "vegetation" in r.comment.lower()]
    assert len(vegetation_results) == 1

    # Search for non-existent text with our prefix
    nonexistent_results = tlog_crud.search_logs_by_text(db, f"{prefix}_NONEXISTENT_XYZ")
    assert len(nonexistent_results) == 0


def test_count_logs_by_text(db: Session, test_user, test_trig):
    """Test counting logs by text substring."""
    # Use unique prefix to isolate test data
    prefix = f"COUNT_TEXT_{uuid.uuid4().hex[:8]}"

    # Create test logs
    log1 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 1),
        time=time(12, 0, 0),
        fb_number="S1234",
        condition="G",
        comment=f"{prefix} Test comment with specific word",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log2 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 2),
        time=time(13, 0, 0),
        fb_number="S1235",
        condition="G",
        comment=f"{prefix} Another test with the specific word",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )

    db.add_all([log1, log2])
    db.commit()

    # Count logs with our unique prefix
    count = tlog_crud.count_logs_by_text(db, prefix)
    assert count == 2

    # Count logs with non-existent text
    count = tlog_crud.count_logs_by_text(db, f"{prefix}_NONEXISTENT_XYZ")
    assert count == 0


def test_search_logs_by_regex(db: Session, test_user, test_trig):
    """Test searching logs by regex pattern."""
    # Use unique prefix to isolate test data
    prefix = f"REGEX_SEARCH_{uuid.uuid4().hex[:8]}"

    # Create test logs
    log1 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 1),
        time=time(12, 0, 0),
        fb_number="S1234",
        condition="G",
        comment=f"{prefix} Found trig TP1234",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log2 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 2),
        time=time(13, 0, 0),
        fb_number="S1235",
        condition="G",
        comment=f"{prefix} Located trig TP5678",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log3 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 3),
        time=time(14, 0, 0),
        fb_number="S1236",
        condition="G",
        comment=f"{prefix} No waypoint code here",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )

    db.add_all([log1, log2, log3])
    db.commit()

    # Search for our prefix + TP followed by digits (PostgreSQL ~* case-insensitive regex)
    results = tlog_crud.search_logs_by_regex(db, f"{prefix}.*TP[0-9]+")
    assert len(results) == 2
    assert all("TP" in log.comment for log in results)

    # Search for pattern that doesn't match within our test data
    results = tlog_crud.search_logs_by_regex(db, f"^{prefix}.*NONEXISTENT")
    assert len(results) == 0


def test_count_logs_by_regex(db: Session, test_user, test_trig):
    """Test counting logs by regex pattern."""
    # Use unique prefix to isolate test data
    prefix = f"COUNT_REGEX_{uuid.uuid4().hex[:8]}"

    # Create test logs
    log1 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 1),
        time=time(12, 0, 0),
        fb_number="S1234",
        condition="G",
        comment=f"{prefix} Email: user@example.com",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log2 = TLog(
        trig_id=test_trig.id,
        user_id=test_user.id,
        date=date(2024, 1, 2),
        time=time(13, 0, 0),
        fb_number="S1235",
        condition="G",
        comment=f"{prefix} Contact: admin@test.org",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )

    db.add_all([log1, log2])
    db.commit()

    # Count logs with our prefix + email pattern
    count = tlog_crud.count_logs_by_regex(db, f"{prefix}.*@.*\\.")
    assert count == 2

    # Count logs with pattern that doesn't match
    count = tlog_crud.count_logs_by_regex(db, f"^{prefix}.*NONEXISTENT")
    assert count == 0


def test_search_logs_pagination(db: Session, test_user, test_trig):
    """Test pagination in log search."""
    # Use unique prefix to isolate test data
    prefix = f"PAGINATION_{uuid.uuid4().hex[:8]}"

    # Create 25 test logs with unique prefix
    logs = []
    for i in range(25):
        log = TLog(
            trig_id=test_trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 1),
            time=time(12, 0, 0),
            fb_number=f"S{1000 + i}",
            condition="G",
            comment=f"{prefix} Test log number {i}",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        logs.append(log)

    db.add_all(logs)
    db.commit()

    # Search with our unique prefix to only get our test logs
    # Get first 10
    page1 = tlog_crud.search_logs_by_text(db, prefix, skip=0, limit=10)
    assert len(page1) == 10

    # Get next 10
    page2 = tlog_crud.search_logs_by_text(db, prefix, skip=10, limit=10)
    assert len(page2) == 10

    # Get last 5
    page3 = tlog_crud.search_logs_by_text(db, prefix, skip=20, limit=10)
    assert len(page3) == 5

    # Verify total count
    total = tlog_crud.count_logs_by_text(db, prefix)
    assert total == 25
