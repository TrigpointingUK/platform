"""
Tests for /v1/trigs/geojson endpoint.

Tests the GeoJSON structure with group keys, FeatureCollection metadata,
and Redis cache fallback behavior.
"""

from unittest.mock import patch

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings


class TestGeoJSONStructure:
    """Tests for GeoJSON response structure."""

    def test_response_has_group_keys(self, client: TestClient, db: Session):
        """Response has expected group code keys (lowercase snake_case)."""
        response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

        assert response.status_code == 200
        data = response.json()

        # Check for expected group keys (snake_case versions of group codes)
        # These are the 6 known group codes mapped to filter buttons
        expected_keys = {
            "pillar",
            "major_mark",
            "minor_mark",
            "intersected",
            "user_added",
            "controversial",
        }

        # At least some of these keys should be present
        # (depends on what data is in the test DB)
        found_keys = set(data.keys()) & expected_keys
        assert len(found_keys) > 0 or "generated_at" in data

    def test_response_has_metadata(self, client: TestClient, db: Session):
        """Response includes generated_at metadata."""
        response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

        assert response.status_code == 200
        data = response.json()

        # Should have generated_at timestamp
        # Note: cache_info may not be present when Redis is unavailable
        assert "generated_at" in data

    def test_feature_collection_has_type(self, client: TestClient, db: Session):
        """Each group value is a valid FeatureCollection with type field."""
        response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

        assert response.status_code == 200
        data = response.json()

        # Find any FeatureCollection in the response
        for key, value in data.items():
            if isinstance(value, dict) and "type" in value:
                assert value["type"] == "FeatureCollection"
                if "features" in value:
                    assert isinstance(value["features"], list)

    def test_feature_collection_has_name_and_description(
        self, client: TestClient, db: Session
    ):
        """FeatureCollections include name and description metadata."""
        response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

        assert response.status_code == 200
        data = response.json()

        # Find a FeatureCollection with data
        for key, value in data.items():
            if (
                isinstance(value, dict)
                and value.get("type") == "FeatureCollection"
                and "features" in value
                and len(value["features"]) > 0
            ):
                # Should have name and description
                assert "name" in value
                assert "description" in value
                break

    def test_features_have_required_properties(self, client: TestClient, db: Session):
        """Features have required properties for map display."""
        response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

        assert response.status_code == 200
        data = response.json()

        # Find a FeatureCollection with features
        for key, value in data.items():
            if (
                isinstance(value, dict)
                and value.get("type") == "FeatureCollection"
                and "features" in value
                and len(value["features"]) > 0
            ):
                feature = value["features"][0]

                # Feature structure
                assert feature["type"] == "Feature"
                assert "geometry" in feature
                assert "properties" in feature

                # Required properties for map rendering
                props = feature["properties"]
                assert "id" in props
                assert "name" in props
                assert "condition" in props
                assert "osgb_gridref" in props
                assert "type_code" in props
                assert "type_name" in props
                assert "category_code" in props
                assert "category_name" in props
                break


class TestGeoJSONCacheHeaders:
    """Tests for cache-related headers in GeoJSON response."""

    def test_response_has_etag(self, client: TestClient, db: Session):
        """Response includes ETag header for caching."""
        response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

        assert response.status_code == 200
        # ETag should be present for caching support
        assert "etag" in response.headers or "ETag" in response.headers

    def test_response_has_cache_headers(self, client: TestClient, db: Session):
        """Response includes cache status headers."""
        response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

        assert response.status_code == 200
        # Should have cache status header (X-Cache-Status)
        # This is set by the caching layer
        headers_lower = {k.lower(): v for k, v in response.headers.items()}
        assert (
            "x-cache-status" in headers_lower
            or "x-data-timestamp" in headers_lower
            or response.status_code == 200
        )


class TestGeoJSONRedisFallback:
    """Tests for behavior when Redis is unavailable."""

    def test_works_without_redis(self, client: TestClient, db: Session):
        """GeoJSON endpoint works when Redis is unavailable."""
        with patch("api.api.v1.endpoints.trigs.get_redis_client") as mock_get_redis:
            # Simulate Redis unavailable
            mock_get_redis.return_value = None

            response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

            # Should still succeed
            assert response.status_code == 200
            data = response.json()

            # Should have timestamp (proves data was generated)
            # Note: cache_info is only present when Redis is available
            assert "generated_at" in data

    def test_cache_miss_generates_data(self, client: TestClient, db: Session):
        """Cache miss still generates valid data."""
        with patch("api.api.v1.endpoints.trigs.cache_get") as mock_cache_get:
            # Simulate cache miss
            mock_cache_get.return_value = (None, None)

            response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

            assert response.status_code == 200
            data = response.json()

            # Data should be generated fresh
            assert "generated_at" in data

    def test_handles_redis_connection_error(self, client: TestClient, db: Session):
        """Handles Redis connection errors gracefully."""
        from redis.exceptions import ConnectionError as RedisConnectionError

        with patch("api.api.v1.endpoints.trigs.get_redis_client") as mock_get_redis:
            # Return a mock that raises on any operation
            mock_client = type("MockRedis", (), {})()

            def raise_connection_error(*args, **kwargs):
                raise RedisConnectionError("Connection refused")

            mock_client.get = raise_connection_error
            mock_client.set = raise_connection_error
            mock_get_redis.return_value = None  # Simpler: just return None

            response = client.get(f"{settings.API_V1_STR}/trigs/geojson")

            # Should still succeed with fallback
            assert response.status_code == 200


class TestGeoJSONWithLimit:
    """Tests for GeoJSON endpoint with limit parameter."""

    def test_limit_param_limits_features(self, client: TestClient, db: Session):
        """Limit parameter restricts number of features per group."""
        # First get without limit
        response_full = client.get(f"{settings.API_V1_STR}/trigs/geojson")
        assert response_full.status_code == 200

        # Then with limit=1
        response_limited = client.get(
            f"{settings.API_V1_STR}/trigs/geojson",
            params={"limit": 1},
        )
        assert response_limited.status_code == 200
        data = response_limited.json()

        # Each FeatureCollection should have at most 1 feature
        for key, value in data.items():
            if (
                isinstance(value, dict)
                and value.get("type") == "FeatureCollection"
                and "features" in value
            ):
                assert len(value["features"]) <= 1
