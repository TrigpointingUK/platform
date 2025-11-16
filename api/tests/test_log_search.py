"""
Tests for log search functionality.
"""

from datetime import date, time

import pytest
from sqlalchemy.orm import Session

from api.crud import tlog as tlog_crud
from api.models.user import TLog


@pytest.mark.skip(
    reason="Search tests expect specific counts incompatible with shared PostgreSQL database. Need redesign for parallel execution."
)
def test_search_logs_by_text(db: Session):
    """Test searching logs by text substring."""
    # Create test logs with different comments
    log1 = TLog(
        trig_id=1,
        user_id=1,
        date=date(2024, 1, 1),
        time=time(12, 0, 0),
        fb_number="S1234",
        condition="G",
        comment="Found the pillar in good condition",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log2 = TLog(
        trig_id=2,
        user_id=1,
        date=date(2024, 1, 2),
        time=time(13, 0, 0),
        fb_number="S1235",
        condition="G",
        comment="The pillar was covered in vegetation",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log3 = TLog(
        trig_id=3,
        user_id=1,
        date=date(2024, 1, 3),
        time=time(14, 0, 0),
        fb_number="S1236",
        condition="G",
        comment="Nice walk to the trig point",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )

    db.add_all([log1, log2, log3])
    db.commit()

    # Search for "pillar"
    results = tlog_crud.search_logs_by_text(db, "pillar")
    assert len(results) == 2
    assert all("pillar" in log.comment.lower() for log in results)

    # Search for "vegetation"
    results = tlog_crud.search_logs_by_text(db, "vegetation")
    assert len(results) == 1
    assert "vegetation" in results[0].comment.lower()

    # Search for non-existent text
    results = tlog_crud.search_logs_by_text(db, "nonexistent")
    assert len(results) == 0


@pytest.mark.skip(
    reason="Search tests expect specific counts incompatible with shared PostgreSQL database. Need redesign for parallel execution."
)
def test_count_logs_by_text(db: Session):
    """Test counting logs by text substring."""
    # Create test logs
    log1 = TLog(
        trig_id=1,
        user_id=1,
        date=date(2024, 1, 1),
        time=time(12, 0, 0),
        fb_number="S1234",
        condition="G",
        comment="Test comment with specific word",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log2 = TLog(
        trig_id=2,
        user_id=1,
        date=date(2024, 1, 2),
        time=time(13, 0, 0),
        fb_number="S1235",
        condition="G",
        comment="Another test with the specific word",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )

    db.add_all([log1, log2])
    db.commit()

    # Count logs with "specific"
    count = tlog_crud.count_logs_by_text(db, "specific")
    assert count == 2

    # Count logs with non-existent text
    count = tlog_crud.count_logs_by_text(db, "nonexistent")
    assert count == 0


@pytest.mark.skip(
    reason="Search tests expect specific counts incompatible with shared PostgreSQL database. Need redesign for parallel execution."
)
def test_search_logs_by_regex(db: Session):
    """Test searching logs by regex pattern."""
    # Create test logs
    log1 = TLog(
        trig_id=1,
        user_id=1,
        date=date(2024, 1, 1),
        time=time(12, 0, 0),
        fb_number="S1234",
        condition="G",
        comment="Found trig TP1234",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log2 = TLog(
        trig_id=2,
        user_id=1,
        date=date(2024, 1, 2),
        time=time(13, 0, 0),
        fb_number="S1235",
        condition="G",
        comment="Located trig TP5678",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log3 = TLog(
        trig_id=3,
        user_id=1,
        date=date(2024, 1, 3),
        time=time(14, 0, 0),
        fb_number="S1236",
        condition="G",
        comment="No waypoint code here",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )

    db.add_all([log1, log2, log3])
    db.commit()

    # Search for TP followed by digits (MySQL REGEXP pattern)
    results = tlog_crud.search_logs_by_regex(db, "TP[0-9]+")
    assert len(results) == 2
    assert all("TP" in log.comment for log in results)

    # Search for pattern that doesn't match
    results = tlog_crud.search_logs_by_regex(db, "^Starting")
    assert len(results) == 0


@pytest.mark.skip(
    reason="Search tests expect specific counts incompatible with shared PostgreSQL database. Need redesign for parallel execution."
)
def test_count_logs_by_regex(db: Session):
    """Test counting logs by regex pattern."""
    # Create test logs
    log1 = TLog(
        trig_id=1,
        user_id=1,
        date=date(2024, 1, 1),
        time=time(12, 0, 0),
        fb_number="S1234",
        condition="G",
        comment="Email: user@example.com",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )
    log2 = TLog(
        trig_id=2,
        user_id=1,
        date=date(2024, 1, 2),
        time=time(13, 0, 0),
        fb_number="S1235",
        condition="G",
        comment="Contact: admin@test.org",
        score=0,
        ip_addr="127.0.0.1",
        source="W",
    )

    db.add_all([log1, log2])
    db.commit()

    # Count logs with email pattern
    count = tlog_crud.count_logs_by_regex(db, "[a-z]+@[a-z]+\\.[a-z]+")
    assert count == 2

    # Count logs with pattern that doesn't match
    count = tlog_crud.count_logs_by_regex(db, "^Phone:")
    assert count == 0


@pytest.mark.skip(
    reason="Search tests expect specific counts incompatible with shared PostgreSQL database. Need redesign for parallel execution."
)
def test_search_logs_pagination(db: Session):
    """Test pagination in log search."""
    # Create 25 test logs
    logs = []
    for i in range(25):
        log = TLog(
            trig_id=i + 1,
            user_id=1,
            date=date(2024, 1, 1),
            time=time(12, 0, 0),
            fb_number=f"S{1000 + i}",
            condition="G",
            comment=f"Test log number {i}",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        logs.append(log)

    db.add_all(logs)
    db.commit()

    # Get first 10
    page1 = tlog_crud.search_logs_by_text(db, "Test", skip=0, limit=10)
    assert len(page1) == 10

    # Get next 10
    page2 = tlog_crud.search_logs_by_text(db, "Test", skip=10, limit=10)
    assert len(page2) == 10

    # Get last 5
    page3 = tlog_crud.search_logs_by_text(db, "Test", skip=20, limit=10)
    assert len(page3) == 5

    # Verify total count
    total = tlog_crud.count_logs_by_text(db, "Test")
    assert total == 25
