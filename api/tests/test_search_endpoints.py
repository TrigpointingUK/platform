"""
API-level tests for search endpoints.

These tests exercise the actual API endpoints that use the search CRUD functions,
ensuring that syntax errors like MySQL REGEXP vs PostgreSQL ~* are caught.

Tests are designed to work with parallel execution in shared PostgreSQL database
by using unique prefixes to isolate test data.
"""

import uuid
from datetime import date, time

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.user import TLog


class TestLogSearchSubstringEndpoint:
    """Test cases for GET /search/logs/substring endpoint."""

    def test_search_logs_substring_returns_results(
        self, client: TestClient, db: Session, test_user, test_trig
    ):
        """Test that search returns matching logs."""
        prefix = f"API_SUBSTRING_{uuid.uuid4().hex[:8]}"

        # Create test logs with unique prefix
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
            comment=f"{prefix} Another log entry",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add_all([log1, log2])
        db.commit()

        # Search using the unique prefix
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/substring",
            params={"q": prefix},
        )

        assert response.status_code == 200
        body = response.json()
        assert "items" in body
        assert "total" in body
        assert body["total"] >= 2
        assert len(body["items"]) >= 2

        # Verify all returned items contain our prefix
        for item in body["items"]:
            if prefix in item["comment"]:
                assert item["id"] is not None
                assert item["comment_excerpt"] is not None

    def test_search_logs_substring_no_results(self, client: TestClient, db: Session):
        """Test search with no matching results."""
        unique_query = f"NONEXISTENT_{uuid.uuid4().hex[:16]}"

        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/substring",
            params={"q": unique_query},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0
        assert len(body["items"]) == 0

    def test_search_logs_substring_pagination(
        self, client: TestClient, db: Session, test_user, test_trig
    ):
        """Test pagination in search results."""
        prefix = f"API_PAGINATE_{uuid.uuid4().hex[:8]}"

        # Create 15 test logs
        logs = []
        for i in range(15):
            log = TLog(
                trig_id=test_trig.id,
                user_id=test_user.id,
                date=date(2024, 1, 1),
                time=time(12, 0, 0),
                fb_number=f"P{i}",
                condition="G",
                comment=f"{prefix} Pagination test log {i}",
                score=0,
                ip_addr="127.0.0.1",
                source="W",
            )
            logs.append(log)
        db.add_all(logs)
        db.commit()

        # Get first page
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/substring",
            params={"q": prefix, "skip": 0, "limit": 10},
        )
        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 15
        assert len(body["items"]) == 10
        assert body["has_more"] is True

        # Get second page
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/substring",
            params={"q": prefix, "skip": 10, "limit": 10},
        )
        assert response.status_code == 200
        body = response.json()
        assert len(body["items"]) == 5
        assert body["has_more"] is False

    def test_search_logs_substring_minimum_query_length(
        self, client: TestClient, db: Session
    ):
        """Test that short queries are rejected."""
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/substring",
            params={"q": "a"},  # Too short
        )
        assert response.status_code == 422  # Validation error


class TestLogSearchRegexEndpoint:
    """Test cases for GET /search/logs/regex endpoint.

    These tests specifically verify PostgreSQL regex syntax works correctly,
    which would have caught the REGEXP vs ~* syntax error.
    """

    def test_search_logs_regex_returns_results(
        self, client: TestClient, db: Session, test_user, test_trig
    ):
        """Test that regex search returns matching logs."""
        prefix = f"API_REGEX_{uuid.uuid4().hex[:8]}"

        # Create test logs with pattern-matchable content
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

        # Search using regex pattern - THIS IS THE CRITICAL TEST
        # This would have failed with MySQL REGEXP syntax error
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/regex",
            params={"q": f"{prefix}.*TP[0-9]+"},
        )

        assert (
            response.status_code == 200
        ), f"Regex search failed with {response.status_code}: {response.text}"
        body = response.json()
        assert "items" in body
        assert body["total"] == 2  # log1 and log2 match
        assert len(body["items"]) == 2

        # Verify all returned items contain TP followed by digits
        for item in body["items"]:
            assert "TP" in item["comment"]

    def test_search_logs_regex_no_results(
        self, client: TestClient, db: Session, test_user, test_trig
    ):
        """Test regex search with no matching results."""
        prefix = f"API_REGEX_NONE_{uuid.uuid4().hex[:8]}"

        # Create a log that won't match the pattern
        log = TLog(
            trig_id=test_trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 1),
            time=time(12, 0, 0),
            fb_number="S1234",
            condition="G",
            comment=f"{prefix} No pattern match here",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        db.commit()

        # Search for pattern that doesn't match
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/regex",
            params={"q": f"^{prefix}.*NONEXISTENT$"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] == 0

    def test_search_logs_regex_case_insensitive(
        self, client: TestClient, db: Session, test_user, test_trig
    ):
        """Test that regex search is case-insensitive (uses ~* operator)."""
        prefix = f"API_REGEX_CI_{uuid.uuid4().hex[:8]}"

        # Create log with mixed case
        log = TLog(
            trig_id=test_trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 1),
            time=time(12, 0, 0),
            fb_number="S1234",
            condition="G",
            comment=f"{prefix} UPPERCASE and lowercase MiXeD",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        db.commit()

        # Search with lowercase pattern - should match uppercase in comment
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/regex",
            params={"q": f"{prefix.lower()}.*uppercase"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1

    def test_search_logs_regex_special_characters(
        self, client: TestClient, db: Session, test_user, test_trig
    ):
        """Test regex search with special regex characters."""
        prefix = f"API_REGEX_SPECIAL_{uuid.uuid4().hex[:8]}"

        # Create log
        log = TLog(
            trig_id=test_trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 1),
            time=time(12, 0, 0),
            fb_number="S1234",
            condition="G",
            comment=f"{prefix} Email: test@example.com (contact)",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        db.commit()

        # Search using regex with escaped special chars
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/regex",
            params={"q": f"{prefix}.*@.*\\.com"},
        )

        assert response.status_code == 200
        body = response.json()
        assert body["total"] >= 1

    def test_search_logs_regex_invalid_pattern(self, client: TestClient, db: Session):
        """Test that invalid regex patterns are handled gracefully."""
        # Use an invalid regex pattern (unmatched bracket)
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/regex",
            params={"q": "[invalid(regex"},
        )

        # Should return 400 or 500 with error message, not crash
        assert response.status_code in [400, 500]


class TestUnifiedSearchEndpoint:
    """Test cases for GET /search/all endpoint (unified search)."""

    def test_unified_search_returns_multiple_categories(
        self, client: TestClient, db: Session, test_user, test_trig
    ):
        """Test that unified search returns results from multiple categories."""
        prefix = f"API_UNIFIED_{uuid.uuid4().hex[:8]}"

        # Create a log that will be found
        log = TLog(
            trig_id=test_trig.id,
            user_id=test_user.id,
            date=date(2024, 1, 1),
            time=time(12, 0, 0),
            fb_number="S1234",
            condition="G",
            comment=f"{prefix} Test log for unified search",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        db.commit()

        response = client.get(
            f"{settings.API_V1_STR}/locations/search/all",
            params={"q": prefix},
        )

        assert response.status_code == 200
        body = response.json()

        # Unified search should have multiple category results
        assert "trigpoints" in body
        assert "postcodes" in body
        assert "users" in body
        assert "log_substring" in body
        assert "query" in body
        assert body["query"] == prefix

    def test_unified_search_minimum_query_length(self, client: TestClient, db: Session):
        """Test that short queries are rejected."""
        response = client.get(
            f"{settings.API_V1_STR}/locations/search/all",
            params={"q": "a"},  # Too short
        )
        assert response.status_code == 422  # Validation error
