"""
Tests for the "logged by" filters, logged-date ordering, map points and the
matching download options - the features behind the Trigs v2 list page.

Each test seeds its own category so it can scope requests with `categories=`
and ignore any other trigs present in the test schema.
"""

import csv
import io
import uuid
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.trig_type import TrigCategory, TrigType
from api.models.user import TLog

TRIGS_URL = f"{settings.API_V1_STR}/trigs"
DOWNLOAD_URL = f"{settings.API_V1_STR}/downloads/trigs"


@pytest.fixture
def pillar_world(db: Session, make_user, make_trig):
    """
    Four pillars in a unique category, two users and a spread of logs:

    - logger logged p3 (2020-01-01), p1 (2021-05-05 10:00, and again 2024),
      p2 (2021-05-05 09:00) and has a draft of p4
    - other user logged p4 only
    """
    tag = uuid.uuid4().hex[:8].upper()
    category = TrigCategory(
        code=f"PIL_{tag}",
        name="Test Pillar",
        sort_order=int(tag[:4], 16) % 11000 + 21500,  # smallint, clear of other tests
    )
    db.add(category)
    db.flush()
    pillar_type = TrigType(
        category_id=category.id, code=f"HOT_{tag}", name="Test Hotine", sort_order=1
    )
    db.add(pillar_type)
    db.flush()

    trigs = [
        make_trig(name=f"Pillar {i} {tag}", type_id=pillar_type.id, wgs_lat=54 + i)
        for i in range(1, 5)
    ]
    logger = make_user()
    other = make_user()

    def log(user, trig, day, at=None, status="P", condition="G"):
        entry = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=day,
            time=at,
            osgb_eastings=0,
            osgb_northings=0,
            osgb_gridref="",
            fb_number="",
            condition=condition,
            comment="",
            score=5,
            ip_addr="127.0.0.1",
            source="W",
            status=status,
        )
        db.add(entry)
        return entry

    p1, p2, p3, p4 = trigs
    log(logger, p3, date(2020, 1, 1), time(12, 0))
    log(logger, p1, date(2021, 5, 5), time(10, 0))
    log(logger, p1, date(2024, 1, 1), time(10, 0), condition="D")
    log(logger, p2, date(2021, 5, 5), time(9, 0))
    log(logger, p4, date(2019, 1, 1), time(9, 0), status="D")  # draft only
    log(other, p4, date(2022, 2, 2), time(8, 0))
    db.commit()

    return SimpleNamespace(
        category=category.code, trigs=trigs, logger=logger, other=other
    )


def _ids(response) -> list[int]:
    return [item["id"] for item in response.json()["items"]]


def test_logged_by_filters_to_another_users_finds(client: TestClient, pillar_world):
    w = pillar_world
    resp = client.get(
        TRIGS_URL,
        params={
            "categories": w.category,
            "logged_by": w.logger.id,
            "only_found": "true",
            "order": "id",
            "limit": 50,
        },
    )
    assert resp.status_code == 200, resp.json()
    # p4 only has a draft from this user, so it isn't a find
    assert _ids(resp) == sorted(t.id for t in w.trigs[:3])
    assert resp.json()["pagination"]["total"] == 3
    assert resp.json()["context"]["logged_by"] == w.logger.id


def test_logged_by_exclude_found_counts_drafts_as_not_logged(
    client: TestClient, pillar_world
):
    w = pillar_world
    resp = client.get(
        TRIGS_URL,
        params={
            "categories": w.category,
            "logged_by": w.logger.id,
            "exclude_found": "true",
        },
    )
    assert resp.status_code == 200
    assert _ids(resp) == [w.trigs[3].id]


def test_logged_by_overrides_authenticated_user(client: TestClient, pillar_world):
    w = pillar_world
    resp = client.get(
        TRIGS_URL,
        params={
            "categories": w.category,
            "logged_by": w.other.id,
            "only_found": "true",
        },
        headers={"Authorization": f"Bearer auth0_user_{w.logger.id}"},
    )
    assert resp.status_code == 200
    assert _ids(resp) == [w.trigs[3].id]


def test_logged_by_unknown_user_is_404(client: TestClient, pillar_world):
    resp = client.get(TRIGS_URL, params={"logged_by": 999999999})
    assert resp.status_code == 404


def test_order_logged_uses_first_log_with_time_tiebreak(
    client: TestClient, pillar_world
):
    w = pillar_world
    p1, p2, p3, _ = w.trigs
    params = {
        "categories": w.category,
        "logged_by": w.logger.id,
        "only_found": "true",
        "order": "logged",
    }
    resp = client.get(TRIGS_URL, params=params)
    assert resp.status_code == 200, resp.json()
    # p3 2020; then p2 and p1 on the same day, p2 earlier in the day.
    # p1's later 2024 log doesn't move it - it's the first log that counts.
    assert _ids(resp) == [p3.id, p2.id, p1.id]
    items = {item["id"]: item for item in resp.json()["items"]}
    assert items[p1.id]["first_logged_date"] == "2021-05-05"
    assert items[p1.id]["first_logged_time"] == "10:00:00"

    resp = client.get(TRIGS_URL, params={**params, "order": "-logged"})
    assert _ids(resp) == [p1.id, p2.id, p3.id]


def test_order_logged_puts_unlogged_trigs_last(client: TestClient, pillar_world):
    w = pillar_world
    resp = client.get(
        TRIGS_URL,
        params={
            "categories": w.category,
            "logged_by": w.logger.id,
            "order": "logged",
        },
    )
    assert resp.status_code == 200
    ids = _ids(resp)
    assert ids[-1] == w.trigs[3].id
    assert resp.json()["items"][-1]["first_logged_date"] is None


def test_order_logged_without_a_log_user_is_rejected(client: TestClient):
    resp = client.get(TRIGS_URL, params={"order": "logged"})
    assert resp.status_code == 422


def test_unknown_order_is_rejected(client: TestClient):
    resp = client.get(TRIGS_URL, params={"order": "banana"})
    assert resp.status_code == 422


def test_logged_conditions_apply_to_logged_by_user(client: TestClient, pillar_world):
    w = pillar_world
    resp = client.get(
        TRIGS_URL,
        params={
            "categories": w.category,
            "logged_by": w.logger.id,
            "only_found": "true",
            "logged_conditions": "D",
        },
    )
    assert resp.status_code == 200
    assert _ids(resp) == [w.trigs[0].id]


def test_points_returns_every_match_with_type_and_category(
    client: TestClient, pillar_world
):
    w = pillar_world
    resp = client.get(
        f"{TRIGS_URL}/points",
        params={
            "categories": w.category,
            "logged_by": w.logger.id,
            "only_found": "true",
        },
    )
    assert resp.status_code == 200, resp.json()
    body = resp.json()
    assert body["total"] == 3
    assert body["truncated"] is False
    rows = [dict(zip(body["fields"], row)) for row in body["rows"]]
    assert [r["id"] for r in rows] == sorted(t.id for t in w.trigs[:3])
    assert all(r["category_code"] == w.category for r in rows)
    assert all(r["type_name"] == "Test Hotine" for r in rows)
    assert rows[0]["lat"] == pytest.approx(55.0)


def test_points_without_filters_is_not_capped_by_pagination(
    client: TestClient, pillar_world
):
    resp = client.get(
        f"{TRIGS_URL}/points", params={"categories": pillar_world.category}
    )
    assert resp.status_code == 200
    assert resp.json()["total"] == 4


def test_download_csv_numbers_rows_by_first_log(client: TestClient, pillar_world):
    w = pillar_world
    p1, p2, p3, _ = w.trigs
    resp = client.get(
        DOWNLOAD_URL,
        params={
            "format": "csv",
            "categories": w.category,
            "logged_by": w.logger.id,
            "only_found": "true",
            "order": "logged",
        },
        headers={"Authorization": f"Bearer auth0_user_{w.other.id}"},
    )
    assert resp.status_code == 200, resp.text
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert [int(r["id"]) for r in rows] == [p3.id, p2.id, p1.id]
    assert [r["sequence"] for r in rows] == ["1", "2", "3"]
    assert rows[2]["first_log_date"] == "2021-05-05"
    assert rows[2]["first_log_time"] == "10:00:00"


def test_download_accepts_v2_filters(client: TestClient, pillar_world):
    w = pillar_world
    headers = {"Authorization": f"Bearer auth0_user_{w.logger.id}"}
    params = {
        "categories": w.category,
        "conditions": "G",
        "historic_use": "Primary",
        "exclude_found": "true",
    }
    count = client.get(f"{DOWNLOAD_URL}/count", params=params, headers=headers)
    assert count.status_code == 200
    assert count.json()["count"] == 1

    resp = client.get(DOWNLOAD_URL, params={**params, "format": "csv"}, headers=headers)
    assert resp.status_code == 200
    rows = list(csv.DictReader(io.StringIO(resp.text)))
    assert [int(r["id"]) for r in rows] == [w.trigs[3].id]
    assert "sequence" not in rows[0]


def test_list_cache_key_varies_by_user():
    """A personalised list must never be served from another user's cache entry."""
    from api.utils.cache_decorator import cached

    keys: list[str] = []

    def fake_get(key):
        keys.append(key)
        return None, None

    @cached(resource_type="trigs", ttl=60, subresource="list", vary_on_user=True)
    def endpoint(only_found: bool = False, current_user=None):
        return {"ok": True}

    with (
        patch("api.utils.cache_decorator.cache_get", side_effect=fake_get),
        patch("api.utils.cache_decorator.cache_set"),
    ):
        endpoint(only_found=True, current_user=SimpleNamespace(id=1))
        endpoint(only_found=True, current_user=SimpleNamespace(id=2))
        endpoint(only_found=True, current_user=None)
        endpoint(only_found=True, current_user=SimpleNamespace(id=1))

    assert len(set(keys)) == 3
    assert keys[0] == keys[3]


def test_trig_invalidation_matches_real_list_keys():
    """Regression: the old 'trigs:list:v1:*' pattern never matched a real key."""
    from fnmatch import fnmatch

    from api.services.cache_invalidator import invalidate_trig_caches
    from api.services.cache_service import generate_cache_key

    list_key = generate_cache_key("trigs", subresource="list", params={"limit": 10})
    points_key = generate_cache_key("trigs", subresource="points", params={"a": 1})

    with patch("api.services.cache_invalidator.invalidate_patterns") as invalidate:
        invalidate_trig_caches(123)
    patterns = invalidate.call_args.args[0]

    prefix = list_key.split(":trigs:")[0] + ":"
    for key in (list_key, points_key):
        assert any(fnmatch(key, prefix + p) for p in patterns), key
