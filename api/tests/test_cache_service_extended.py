"""
Tests for services/cache_service.py — Redis cache operations.
"""

import json
from unittest.mock import MagicMock, patch

from redis.exceptions import RedisError

from api.services.cache_service import (
    cache_delete,
    cache_delete_pattern,
    cache_delete_patterns_batched,
    cache_flush_all,
    cache_get,
    cache_get_stats,
    cache_set,
    generate_cache_key,
)


class TestGenerateCacheKey:
    def test_basic_key(self):
        key = generate_cache_key("trig")
        assert "trig" in key
        assert key.endswith(":v1")

    def test_key_with_resource_id(self):
        key = generate_cache_key("trig", resource_id="123")
        assert ":123:" in key

    def test_key_with_subresource(self):
        key = generate_cache_key("trig", resource_id="123", subresource="logs")
        assert ":logs:" in key

    def test_key_with_params(self):
        key = generate_cache_key("trig", params={"skip": 0, "limit": 10})
        assert "params_" in key

    def test_params_order_independent(self):
        k1 = generate_cache_key("trig", params={"a": 1, "b": 2})
        k2 = generate_cache_key("trig", params={"b": 2, "a": 1})
        assert k1 == k2

    def test_custom_version(self):
        key = generate_cache_key("trig", version="v2")
        assert key.endswith(":v2")


class TestCacheGetNoRedis:
    @patch("api.services.cache_service.get_redis_client", return_value=None)
    def test_returns_none_tuple(self, mock_client):
        val, age = cache_get("key")
        assert val is None
        assert age is None


class TestCacheGetWithRedis:
    def test_returns_value_and_age(self):
        mock_client = MagicMock()
        mock_pipe = MagicMock()
        cached_data = json.dumps(
            {"value": {"name": "Test"}, "ttl": 300, "cached_at": 1000}
        )
        mock_pipe.execute.return_value = [cached_data, 200]
        mock_client.pipeline.return_value = mock_pipe

        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            val, age = cache_get("key")
            assert val == {"name": "Test"}
            assert age == 100  # 300 - 200

    def test_returns_none_for_cache_miss(self):
        mock_client = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = [None, -2]
        mock_client.pipeline.return_value = mock_pipe

        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            val, age = cache_get("key")
            assert val is None

    def test_returns_none_on_json_decode_error(self):
        mock_client = MagicMock()
        mock_pipe = MagicMock()
        mock_pipe.execute.return_value = ["not-json", 100]
        mock_client.pipeline.return_value = mock_pipe

        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            val, age = cache_get("key")
            assert val is None

    def test_returns_none_on_redis_error(self):
        mock_client = MagicMock()
        mock_client.pipeline.side_effect = RedisError("fail")

        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            val, age = cache_get("key")
            assert val is None


class TestCacheSet:
    @patch("api.services.cache_service.get_redis_client", return_value=None)
    def test_returns_false_without_redis(self, mock_client):
        assert cache_set("key", "value") is False

    def test_sets_with_ttl(self):
        mock_client = MagicMock()
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            result = cache_set("key", {"data": 1}, ttl=300)
            assert result is True
            mock_client.setex.assert_called_once()

    def test_sets_without_ttl(self):
        mock_client = MagicMock()
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            result = cache_set("key", {"data": 1}, ttl=None)
            assert result is True
            mock_client.set.assert_called_once()

    def test_returns_false_on_redis_error(self):
        mock_client = MagicMock()
        mock_client.setex.side_effect = RedisError("fail")
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_set("key", "val", ttl=100) is False


class TestCacheDelete:
    @patch("api.services.cache_service.get_redis_client", return_value=None)
    def test_returns_false_without_redis(self, _):
        assert cache_delete("key") is False

    def test_returns_true_on_delete(self):
        mock_client = MagicMock()
        mock_client.delete.return_value = 1
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_delete("key") is True

    def test_returns_false_when_key_missing(self):
        mock_client = MagicMock()
        mock_client.delete.return_value = 0
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_delete("key") is False

    def test_returns_false_on_redis_error(self):
        mock_client = MagicMock()
        mock_client.delete.side_effect = RedisError("fail")
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_delete("key") is False


class TestCacheDeletePattern:
    @patch("api.services.cache_service.get_redis_client", return_value=None)
    def test_returns_neg_one_without_redis(self, _):
        assert cache_delete_pattern("*") == -1

    def test_deletes_matching_keys(self):
        mock_client = MagicMock()
        mock_client.scan.return_value = (0, ["key1", "key2"])
        mock_client.delete.return_value = 2
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_delete_pattern("key*") == 2

    def test_returns_neg_one_on_error(self):
        mock_client = MagicMock()
        mock_client.scan.side_effect = RedisError("fail")
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_delete_pattern("*") == -1


class TestCacheDeletePatternsBatched:
    @patch("api.services.cache_service.get_redis_client", return_value=None)
    def test_returns_neg_one_without_redis(self, _):
        assert cache_delete_patterns_batched(["*"]) == -1

    def test_returns_zero_for_empty_patterns(self):
        mock_client = MagicMock()
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_delete_patterns_batched([]) == 0

    def test_deletes_matching_patterns(self):
        mock_client = MagicMock()
        mock_client.scan.return_value = (
            0,
            ["fastapi:dev:trig:1", "fastapi:dev:user:1"],
        )
        mock_client.delete.return_value = 1
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            result = cache_delete_patterns_batched(["fastapi:dev:trig:*"])
            assert result >= 0

    def test_returns_neg_one_on_error(self):
        mock_client = MagicMock()
        mock_client.scan.side_effect = RedisError("fail")
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_delete_patterns_batched(["*"]) == -1


class TestCacheFlushAll:
    @patch("api.services.cache_service.get_redis_client", return_value=None)
    def test_returns_false_without_redis(self, _):
        assert cache_flush_all() is False

    def test_flushes_successfully(self):
        mock_client = MagicMock()
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_flush_all() is True
            mock_client.flushdb.assert_called_once()

    def test_returns_false_on_error(self):
        mock_client = MagicMock()
        mock_client.flushdb.side_effect = RedisError("fail")
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_flush_all() is False


class TestCacheGetStats:
    @patch("api.services.cache_service.get_redis_client", return_value=None)
    def test_returns_none_without_redis(self, _):
        assert cache_get_stats() is None

    def test_returns_stats(self):
        mock_client = MagicMock()
        mock_client.info.side_effect = [
            {"keyspace_hits": 100, "keyspace_misses": 20, "connected_clients": 3},
            {"used_memory": 1024, "used_memory_human": "1K"},
            {"db0": {"keys": 50}},
        ]
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            stats = cache_get_stats()
            assert stats is not None
            assert stats["total_keys"] == 50
            assert stats["keyspace_hits"] == 100
            assert stats["hit_rate_percent"] > 0

    def test_returns_none_on_error(self):
        mock_client = MagicMock()
        mock_client.info.side_effect = RedisError("fail")
        with patch(
            "api.services.cache_service.get_redis_client", return_value=mock_client
        ):
            assert cache_get_stats() is None


class TestGetRedisClient:
    @patch("api.services.cache_service._redis_client", None)
    @patch("api.services.cache_service._redis_available", True)
    @patch("api.services.cache_service.settings")
    def test_returns_none_when_cache_disabled(self, mock_settings):
        mock_settings.CACHE_ENABLED = False
        from api.services.cache_service import get_redis_client

        assert get_redis_client() is None

    @patch("api.services.cache_service._redis_client", None)
    @patch("api.services.cache_service._redis_available", True)
    @patch("api.services.cache_service.settings")
    def test_returns_none_when_no_redis_url(self, mock_settings):
        mock_settings.CACHE_ENABLED = True
        mock_settings.REDIS_URL = None
        from api.services.cache_service import get_redis_client

        assert get_redis_client() is None
