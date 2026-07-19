"""
Tests for the @cached() endpoint decorator in api.utils.cache_decorator.

The decorator wraps endpoint functions with Redis caching. These tests mock the
underlying cache_service functions (cache_get / cache_set / generate_cache_key)
so the decorator's own branching logic can be exercised without Redis.
"""

import json
from unittest.mock import patch

import pytest
from fastapi import Response
from fastapi.responses import JSONResponse, StreamingResponse
from starlette.datastructures import Headers

from api.utils.cache_decorator import cached


class _FakeRequest:
    """Minimal stand-in for fastapi.Request exposing only .headers."""

    def __init__(self, headers: dict | None = None):
        self.headers = Headers(headers or {})


@pytest.fixture
def cache_mocks():
    """Patch the cache_service functions imported into the decorator module."""
    with patch("api.utils.cache_decorator.cache_get") as m_get, patch(
        "api.utils.cache_decorator.cache_set"
    ) as m_set, patch(
        "api.utils.cache_decorator.generate_cache_key", return_value="cache:key"
    ) as m_key:
        # Default: cache miss
        m_get.return_value = (None, None)
        yield {"get": m_get, "set": m_set, "key": m_key}


class TestSyncWrapper:
    def test_cache_miss_calls_func_and_stores(self, cache_mocks):
        @cached(resource_type="trig", ttl=120, resource_id_param="trig_id")
        def endpoint(trig_id: int):
            return {"id": trig_id, "name": "Pen y Fan"}

        resp = endpoint(trig_id=42)

        assert isinstance(resp, JSONResponse)
        assert resp.headers["X-Cache-Status"] == "MISS"
        assert resp.headers["X-Cache-Key"] == "cache:key"
        assert resp.headers["X-Cache-TTL"] == "120"
        assert json.loads(resp.body) == {"id": 42, "name": "Pen y Fan"}
        # resource_id is passed through, not included in params
        _, kwargs = cache_mocks["key"].call_args
        assert kwargs["resource_id"] == "42"
        cache_mocks["set"].assert_called_once()

    def test_cache_hit_returns_cached_value(self, cache_mocks):
        cache_mocks["get"].return_value = ({"cached": True}, 30)

        @cached(resource_type="trig", ttl=120)
        def endpoint():
            raise AssertionError("endpoint should not be called on cache hit")

        resp = endpoint()

        assert isinstance(resp, JSONResponse)
        assert resp.headers["X-Cache-Status"] == "HIT"
        assert resp.headers["X-Cache-Age"] == "30"
        assert json.loads(resp.body) == {"cached": True}
        cache_mocks["set"].assert_not_called()

    def test_no_cache_header_bypasses_cache(self, cache_mocks):
        request = _FakeRequest({"cache-control": "no-cache"})

        @cached(resource_type="trig", ttl=120)
        def endpoint(request=None):
            return {"fresh": True}

        resp = endpoint(request=request)

        assert resp.headers["X-Cache-Status"] == "BYPASS"
        # Bypass means we never read or write the cache.
        cache_mocks["get"].assert_not_called()
        cache_mocks["set"].assert_not_called()

    def test_response_object_passthrough_not_cached(self, cache_mocks):
        @cached(resource_type="trig", ttl=120)
        def endpoint():
            return Response(content="raw", media_type="text/plain")

        resp = endpoint()

        assert isinstance(resp, Response)
        assert resp.headers["X-Cache-Status"] == "MISS"
        assert resp.headers["X-Cache-Key"] == "cache:key"
        # Response objects are not serialisable into the cache.
        cache_mocks["set"].assert_not_called()

    def test_streaming_response_not_cached(self, cache_mocks):
        def gen():
            yield b"chunk"

        @cached(resource_type="tile", ttl=120)
        def endpoint():
            return StreamingResponse(gen())

        resp = endpoint()

        assert isinstance(resp, StreamingResponse)
        cache_mocks["set"].assert_not_called()

    def test_cache_control_header_added(self, cache_mocks):
        @cached(resource_type="trig", ttl=120, cache_control="public, max-age=60")
        def endpoint():
            return {"ok": True}

        resp = endpoint()

        assert resp.headers["Cache-Control"] == "public, max-age=60"

    def test_cache_control_header_added_on_hit(self, cache_mocks):
        cache_mocks["get"].return_value = ({"ok": True}, 5)

        @cached(resource_type="trig", ttl=120, cache_control="public, max-age=60")
        def endpoint():
            return {"ok": True}

        resp = endpoint()

        assert resp.headers["X-Cache-Status"] == "HIT"
        assert resp.headers["Cache-Control"] == "public, max-age=60"

    def test_query_params_built_excluding_special_params(self, cache_mocks):
        @cached(resource_type="log", ttl=60, include_query_params=True)
        def endpoint(db=None, current_user=None, page=None, limit=None):
            return {"ok": True}

        endpoint(db="session", current_user="user", page=2, limit=None)

        _, kwargs = cache_mocks["key"].call_args
        # db/current_user excluded; None-valued limit excluded; page kept.
        assert kwargs["params"] == {"page": 2}

    def test_cache_set_error_is_swallowed(self, cache_mocks):
        cache_mocks["set"].side_effect = RuntimeError("redis down")

        @cached(resource_type="trig", ttl=120)
        def endpoint():
            return {"ok": True}

        # Storage failure must not propagate to the caller.
        resp = endpoint()
        assert resp.headers["X-Cache-Status"] == "MISS"


class TestAsyncWrapper:
    @pytest.mark.asyncio
    async def test_async_cache_miss_calls_func_and_stores(self, cache_mocks):
        @cached(resource_type="trig", ttl=120, resource_id_param="trig_id")
        async def endpoint(trig_id: int):
            return {"id": trig_id}

        resp = await endpoint(trig_id=7)

        assert isinstance(resp, JSONResponse)
        assert resp.headers["X-Cache-Status"] == "MISS"
        assert json.loads(resp.body) == {"id": 7}
        cache_mocks["set"].assert_called_once()

    @pytest.mark.asyncio
    async def test_async_cache_hit_returns_cached_value(self, cache_mocks):
        cache_mocks["get"].return_value = ({"cached": 1}, 12)

        @cached(resource_type="trig", ttl=120)
        async def endpoint():
            raise AssertionError("should not be called on hit")

        resp = await endpoint()

        assert resp.headers["X-Cache-Status"] == "HIT"
        assert resp.headers["X-Cache-Age"] == "12"
        assert json.loads(resp.body) == {"cached": 1}

    @pytest.mark.asyncio
    async def test_async_no_cache_header_bypasses(self, cache_mocks):
        request = _FakeRequest({"cache-control": "no-cache"})

        @cached(resource_type="trig", ttl=120)
        async def endpoint(request=None):
            return {"fresh": True}

        resp = await endpoint(request=request)

        assert resp.headers["X-Cache-Status"] == "BYPASS"
        cache_mocks["get"].assert_not_called()

    @pytest.mark.asyncio
    async def test_async_response_passthrough(self, cache_mocks):
        @cached(resource_type="trig", ttl=120)
        async def endpoint():
            return Response(content="raw")

        resp = await endpoint()

        assert isinstance(resp, Response)
        assert resp.headers["X-Cache-Status"] == "MISS"
        cache_mocks["set"].assert_not_called()

    @pytest.mark.asyncio
    async def test_async_cache_set_error_is_swallowed(self, cache_mocks):
        cache_mocks["set"].side_effect = RuntimeError("redis down")

        @cached(resource_type="trig", ttl=120)
        async def endpoint():
            return {"ok": True}

        resp = await endpoint()
        assert resp.headers["X-Cache-Status"] == "MISS"

    @pytest.mark.asyncio
    async def test_async_cache_control_header_on_miss(self, cache_mocks):
        @cached(resource_type="trig", ttl=120, cache_control="public, max-age=60")
        async def endpoint():
            return {"ok": True}

        resp = await endpoint()
        assert resp.headers["Cache-Control"] == "public, max-age=60"

    @pytest.mark.asyncio
    async def test_async_cache_control_header_on_hit(self, cache_mocks):
        cache_mocks["get"].return_value = ({"ok": True}, 9)

        @cached(resource_type="trig", ttl=120, cache_control="public, max-age=60")
        async def endpoint():
            return {"ok": True}

        resp = await endpoint()
        assert resp.headers["X-Cache-Status"] == "HIT"
        assert resp.headers["Cache-Control"] == "public, max-age=60"
