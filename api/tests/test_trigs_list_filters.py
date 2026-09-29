"""
Tests for the trig list membership filters (in_lists / not_in_lists) on the
trig list, map points and download endpoints.

Each test seeds its own category so it can scope requests with `categories=`
and ignore any other trigs present in the test schema.
"""

import uuid
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud.trig_list import add_item, create_list
from api.models.trig_type import TrigCategory, TrigType

TRIGS_URL = f"{settings.API_V1_STR}/trigs"
DOWNLOAD_URL = f"{settings.API_V1_STR}/downloads/trigs"


@pytest.fixture
def list_world(db: Session, make_user, make_trig):
    """
    Four pillars in a unique category and three lists:

    - owner's private "Marked" list: p1, p2
    - other user's public list: p2, p3
    - other user's private list: p4
    """
    tag = uuid.uuid4().hex[:8].upper()
    category = TrigCategory(
        code=f"LST_{tag}",
        name="Test List Pillar",
        sort_order=int(tag[:4], 16) % 11000 + 21500,  # smallint, clear of other tests
    )
    db.add(category)
    db.flush()
    pillar_type = TrigType(
        category_id=category.id, code=f"LSH_{tag}", name="Test Hotine", sort_order=1
    )
    db.add(pillar_type)
    db.flush()

    trigs = [
        make_trig(name=f"Listed {i} {tag}", type_id=pillar_type.id, wgs_lat=54 + i)
        for i in range(1, 5)
    ]
    p1, p2, p3, p4 = trigs
    owner = make_user()
    other = make_user()

    def make_list(user, name, members, visibility="private"):
        trig_list = create_list(db, user.id, name=name, visibility=visibility)
        for trig in members:
            add_item(db, trig_list.id, trig.id, user.id)
        return trig_list

    marked = make_list(owner, "Marked", [p1, p2])
    public = make_list(other, "Public", [p2, p3], visibility="public")
    private = make_list(other, "Private", [p4])
    db.commit()

    return SimpleNamespace(
        category=category.code,
        trigs=trigs,
        owner=owner,
        other=other,
        marked=marked,
        public=public,
        private=private,
        auth={"Authorization": f"Bearer auth0_user_{owner.id}"},
    )


def _ids(response) -> list[int]:
    return sorted(item["id"] for item in response.json()["items"])


def _get(client, w, headers=None, **params):
    return client.get(
        TRIGS_URL,
        params={"categories": w.category, "limit": 50, **params},
        headers=headers,
    )


def test_in_lists_includes_only_list_members(client: TestClient, list_world):
    w = list_world
    p1, p2, _, _ = w.trigs
    resp = _get(client, w, w.auth, in_lists=w.marked.id)
    assert resp.status_code == 200, resp.json()
    assert _ids(resp) == sorted([p1.id, p2.id])
    assert resp.json()["pagination"]["total"] == 2


def test_not_in_lists_excludes_list_members(client: TestClient, list_world):
    w = list_world
    _, _, p3, p4 = w.trigs
    resp = _get(client, w, w.auth, not_in_lists=w.marked.id)
    assert resp.status_code == 200, resp.json()
    assert _ids(resp) == sorted([p3.id, p4.id])


def test_in_lists_matches_any_of_several(client: TestClient, list_world):
    w = list_world
    p1, p2, p3, _ = w.trigs
    resp = _get(client, w, w.auth, in_lists=f"{w.marked.id},{w.public.id}")
    assert resp.status_code == 200, resp.json()
    assert _ids(resp) == sorted([p1.id, p2.id, p3.id])


def test_in_and_not_in_lists_combine(client: TestClient, list_world):
    """Marked, but not in the public list: p1 only."""
    w = list_world
    resp = _get(client, w, w.auth, in_lists=w.marked.id, not_in_lists=w.public.id)
    assert resp.status_code == 200, resp.json()
    assert _ids(resp) == [w.trigs[0].id]


def test_public_list_works_without_signing_in(client: TestClient, list_world):
    w = list_world
    _, p2, p3, _ = w.trigs
    resp = _get(client, w, in_lists=w.public.id)
    assert resp.status_code == 200, resp.json()
    assert _ids(resp) == sorted([p2.id, p3.id])


def test_private_list_of_another_user_is_404(client: TestClient, list_world):
    w = list_world
    resp = _get(client, w, w.auth, in_lists=w.private.id)
    assert resp.status_code == 404
    resp = _get(client, w, w.auth, not_in_lists=w.private.id)
    assert resp.status_code == 404


def test_private_list_needs_its_owner(client: TestClient, list_world):
    w = list_world
    assert _get(client, w, in_lists=w.marked.id).status_code == 404


def test_unknown_list_is_404(client: TestClient, list_world):
    w = list_world
    assert _get(client, w, w.auth, in_lists=999999999).status_code == 404


def test_malformed_list_ids_are_422(client: TestClient, list_world):
    w = list_world
    assert _get(client, w, w.auth, in_lists="abc").status_code == 422


def test_points_endpoint_filters_by_list(client: TestClient, list_world):
    w = list_world
    p1, p2, _, _ = w.trigs
    resp = client.get(
        f"{TRIGS_URL}/points",
        params={"categories": w.category, "in_lists": w.marked.id},
        headers=w.auth,
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    id_col = body["fields"].index("id")
    assert sorted(row[id_col] for row in body["rows"]) == sorted([p1.id, p2.id])


def test_download_count_filters_by_list(client: TestClient, list_world):
    w = list_world
    resp = client.get(
        f"{DOWNLOAD_URL}/count",
        params={"categories": w.category, "not_in_lists": w.marked.id},
        headers=w.auth,
    )
    assert resp.status_code == 200, resp.json()
    assert resp.json()["count"] == 2


def test_list_filtered_responses_are_never_cached(client: TestClient, list_world):
    """List edits don't invalidate the trig caches, so these must skip Redis."""
    w = list_world
    with (
        patch("api.utils.cache_decorator.cache_get") as cache_get,
        patch("api.utils.cache_decorator.cache_set") as cache_set,
    ):
        resp = _get(client, w, w.auth, in_lists=w.marked.id)
        assert resp.status_code == 200, resp.json()
        assert resp.headers["X-Cache-Status"] == "BYPASS"
        cache_get.assert_not_called()
        cache_set.assert_not_called()


class _Filters(SimpleNamespace):
    """Stand-in dependency object that describes its own cache key."""

    def cache_key_params(self):
        return {}


def test_unfiltered_responses_are_still_cached():
    """Only list-filtered requests opt out; everything else still caches."""
    from api.utils.cache_decorator import cached

    @cached(resource_type="trigs", ttl=60, subresource="list")
    def endpoint(filters=None):
        return {"ok": True}

    with (
        patch(
            "api.utils.cache_decorator.cache_get", return_value=(None, None)
        ) as cache_get,
        patch("api.utils.cache_decorator.cache_set") as cache_set,
    ):
        endpoint(filters=_Filters(cacheable=True))
        assert cache_get.call_count == 1
        assert cache_set.call_count == 1

        endpoint(filters=_Filters(cacheable=False))
        assert cache_get.call_count == 1
        assert cache_set.call_count == 1


def test_async_endpoints_also_skip_the_cache_when_uncacheable():
    import asyncio

    from api.utils.cache_decorator import cached

    @cached(resource_type="trigs", ttl=60, subresource="list")
    async def endpoint(filters=None):
        return {"ok": True}

    with (
        patch("api.utils.cache_decorator.cache_get") as cache_get,
        patch("api.utils.cache_decorator.cache_set") as cache_set,
    ):
        response = asyncio.run(endpoint(filters=_Filters(cacheable=False)))
        assert response.headers["X-Cache-Status"] == "BYPASS"
        cache_get.assert_not_called()
        cache_set.assert_not_called()
