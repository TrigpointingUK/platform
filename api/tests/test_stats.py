"""
Tests for site statistics endpoint.
"""

from fastapi.testclient import TestClient

from api.core.config import settings


def test_site_stats_endpoint(client: TestClient, db):
    """Test /v1/stats/site endpoint returns all required statistics."""
    response = client.get(f"{settings.API_V1_STR}/stats/site")
    assert response.status_code == 200

    data = response.json()

    # Verify all required fields are present
    assert "total_trigs" in data
    assert "total_members" in data
    assert "total_logs" in data
    assert "total_photos" in data
    assert "recent_logs_7d" in data
    assert "recent_users_30d" in data

    # Verify all values are integers (pg_class may return -1 for tables with no stats)
    for key, value in data.items():
        assert isinstance(value, int), f"{key} should be an integer"


def test_site_stats_cache_headers(client: TestClient, db):
    """Test that cache headers are properly set."""
    response = client.get(f"{settings.API_V1_STR}/stats/site")
    assert response.status_code == 200

    # Check for cache-related headers
    assert "X-Cache-Status" in response.headers
    assert "X-Cache-Key" in response.headers
    assert "X-Cache-TTL" in response.headers

    # TTL should be 3600 seconds (1 hour)
    assert response.headers["X-Cache-TTL"] == "3600"

    # Second request should hit cache
    response2 = client.get(f"{settings.API_V1_STR}/stats/site")
    assert response2.status_code == 200

    # Depending on Redis availability, this might be HIT or MISS
    cache_status = response2.headers.get("X-Cache-Status")
    assert cache_status in ["HIT", "MISS"]


def test_site_stats_performance(client: TestClient, db):
    """Test that site stats endpoint responds quickly."""
    import time

    start_time = time.time()
    response = client.get(f"{settings.API_V1_STR}/stats/site")
    elapsed_time = time.time() - start_time

    assert response.status_code == 200

    # Even on first request (cache miss), should complete in under 2 seconds
    # The optimized query using pg_class should be very fast
    assert elapsed_time < 2.0, f"Endpoint took {elapsed_time:.2f}s, expected < 2.0s"
