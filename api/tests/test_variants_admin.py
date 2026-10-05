"""
Tests for the trig variant admin endpoints (/v1/admin/variants).

Covers listing groups with trig counts and the types offering them, creating
variants in existing and new groups, renaming variants and groups, and the
rules that stop a variant being deleted while trigs record it or while it's
the last of a group that types still offer.

Each test seeds its own groups with unique codes and names, as other tests
(and the seeded Detector material group) share the database.
"""

import uuid
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.trig_type import TrigCategory, TrigType
from api.models.trig_variant import TrigVariant

ADMIN_URL = f"{settings.API_V1_STR}/admin/variants"
REFERENCE_URL = f"{settings.API_V1_STR}/reference/variant-groups"
ADMIN_AUTH = {"Authorization": "Bearer auth0_admin"}


@pytest.fixture(autouse=True)
def _admin_user(test_user):
    """The auth0_admin token resolves to any existing user."""
    return test_user


@pytest.fixture
def world(db: Session, make_trig):
    """
    - offered: a group the Widget type offers, with "Alpha" (recorded on a
      trig) and "Beta" (unused)
    - spare: a group no type offers, with just "Gamma"
    """
    tag = uuid.uuid4().hex[:8].upper()
    category = TrigCategory(
        code=f"VAD_{tag}",
        name="Variant Admin Test",
        sort_order=int(tag[:4], 16) % 9000 + 1000,
    )
    db.add(category)
    db.flush()

    offered = f"OFF_{tag}"
    spare = f"SPR_{tag}"
    widget = TrigType(
        category_id=category.id,
        code=f"WID_{tag}",
        name=f"Widget {tag}",
        sort_order=1,
        variant_group=offered,
    )

    def variant(group, group_name, code, name, sort_order):
        return TrigVariant(
            group_code=group,
            group_name=group_name,
            code=f"{code}_{tag}",
            name=name,
            sort_order=sort_order,
        )

    alpha = variant(offered, f"Offered {tag}", "ALPHA", "Alpha", 10)
    beta = variant(offered, f"Offered {tag}", "BETA", "Beta", 20)
    gamma = variant(spare, f"Spare {tag}", "GAMMA", "Gamma", 10)
    db.add_all([widget, alpha, beta, gamma])
    db.flush()

    trig = make_trig(type_id=widget.id, variant_id=alpha.id)
    db.commit()
    return SimpleNamespace(
        tag=tag,
        offered=offered,
        spare=spare,
        widget=widget,
        alpha=alpha,
        beta=beta,
        gamma=gamma,
        trig=trig,
    )


def _group(client, code: str) -> dict:
    resp = client.get(ADMIN_URL, headers=ADMIN_AUTH)
    assert resp.status_code == 200, resp.json()
    return next(g for g in resp.json() if g["code"] == code)


class TestAuth:
    def test_requires_auth(self, client):
        assert client.get(ADMIN_URL).status_code == 401

    def test_requires_admin(self, client, test_user):
        resp = client.get(
            ADMIN_URL, headers={"Authorization": f"Bearer auth0_user_{test_user.id}"}
        )
        assert resp.status_code == 403


class TestList:
    def test_groups_with_counts_and_types(self, client, world):
        group = _group(client, world.offered)
        assert group["name"] == f"Offered {world.tag}"
        assert group["type_names"] == [world.widget.name]
        assert [(v["name"], v["trig_count"]) for v in group["variants"]] == [
            ("Alpha", 1),
            ("Beta", 0),
        ]

    def test_group_no_type_offers(self, client, world):
        group = _group(client, world.spare)
        assert group["type_names"] == []
        assert [v["code"] for v in group["variants"]] == [world.gamma.code]


class TestCreate:
    def test_create_in_existing_group(self, client, db, world):
        resp = client.post(
            ADMIN_URL,
            json={
                "group_code": world.offered,
                "group_name": "Ignored",
                "code": f" delta_{world.tag.lower()} ",
                "name": " Delta ",
                "sort_order": 30,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["code"] == f"DELTA_{world.tag}"
        assert body["name"] == "Delta"
        # An existing group keeps its own name
        assert body["group_name"] == f"Offered {world.tag}"
        assert [v["name"] for v in _group(client, world.offered)["variants"]] == [
            "Alpha",
            "Beta",
            "Delta",
        ]

    def test_create_new_group(self, client, world):
        group_code = f"NEW_{world.tag}"
        resp = client.post(
            ADMIN_URL,
            json={
                "group_code": group_code,
                "group_name": f"New group {world.tag}",
                "code": f"FIRST_{world.tag}",
                "name": "First",
                "sort_order": 10,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 201, resp.json()
        assert _group(client, group_code)["name"] == f"New group {world.tag}"

    def test_new_group_needs_a_name(self, client, world):
        resp = client.post(
            ADMIN_URL,
            json={
                "group_code": f"NEW_{world.tag}",
                "code": f"FIRST_{world.tag}",
                "name": "First",
                "sort_order": 10,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400
        assert "Group name" in resp.json()["detail"]

    def test_new_group_name_must_be_free(self, client, world):
        resp = client.post(
            ADMIN_URL,
            json={
                "group_code": f"NEW_{world.tag}",
                "group_name": f"spare {world.tag}",
                "code": f"FIRST_{world.tag}",
                "name": "First",
                "sort_order": 10,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_duplicate_code_rejected(self, client, world):
        resp = client.post(
            ADMIN_URL,
            json={
                "group_code": world.spare,
                "code": world.alpha.code,
                "name": "Another",
                "sort_order": 1,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400
        assert world.alpha.code in resp.json()["detail"]

    def test_duplicate_name_in_group_rejected(self, client, world):
        resp = client.post(
            ADMIN_URL,
            json={
                "group_code": world.offered,
                "code": f"ALPHA2_{world.tag}",
                "name": "ALPHA",
                "sort_order": 1,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400
        assert "already exists in this group" in resp.json()["detail"]

    def test_same_name_allowed_in_another_group(self, client, world):
        resp = client.post(
            ADMIN_URL,
            json={
                "group_code": world.spare,
                "code": f"ALPHA2_{world.tag}",
                "name": "Alpha",
                "sort_order": 1,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 201, resp.json()

    @pytest.mark.parametrize("code", ["NOT_RECORDED", "1ST", "TWO WORDS", "DASH-ED"])
    def test_bad_codes_rejected(self, client, world, code):
        resp = client.post(
            ADMIN_URL,
            json={
                "group_code": world.spare,
                "code": code,
                "name": f"Bad {code}",
                "sort_order": 1,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400


class TestUpdate:
    def test_rename_and_reorder(self, client, world):
        resp = client.patch(
            f"{ADMIN_URL}/{world.beta.id}",
            json={"name": "Bravo", "sort_order": 5},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json()["code"] == world.beta.code
        assert [v["name"] for v in _group(client, world.offered)["variants"]] == [
            "Bravo",
            "Alpha",
        ]

    def test_rename_shows_on_trigs(self, client, world):
        resp = client.patch(
            f"{ADMIN_URL}/{world.alpha.id}",
            json={"name": "Aleph"},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 200, resp.json()
        trig = client.get(f"{settings.API_V1_STR}/trigs/{world.trig.id}").json()
        assert trig["variant_name"] == "Aleph"

    def test_name_clash_in_group_rejected(self, client, world):
        resp = client.patch(
            f"{ADMIN_URL}/{world.beta.id}",
            json={"name": "alpha"},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400

    def test_not_found(self, client):
        resp = client.patch(
            f"{ADMIN_URL}/999999", json={"sort_order": 1}, headers=ADMIN_AUTH
        )
        assert resp.status_code == 404


class TestRenameGroup:
    def test_renames_every_variant(self, client, db, world):
        resp = client.patch(
            f"{ADMIN_URL}/groups/{world.offered}",
            json={"name": f" Renamed {world.tag} "},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json() == {"code": world.offered, "name": f"Renamed {world.tag}"}
        for variant in (world.alpha, world.beta):
            db.refresh(variant)
            assert variant.group_name == f"Renamed {world.tag}"
        db.refresh(world.gamma)
        assert world.gamma.group_name == f"Spare {world.tag}"

    def test_name_of_another_group_rejected(self, client, world):
        resp = client.patch(
            f"{ADMIN_URL}/groups/{world.offered}",
            json={"name": f"Spare {world.tag}"},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400

    def test_unknown_group(self, client):
        resp = client.patch(
            f"{ADMIN_URL}/groups/NO_SUCH_GROUP",
            json={"name": "Whatever"},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 404


class TestDelete:
    def test_delete_unused(self, client, db, world):
        resp = client.delete(f"{ADMIN_URL}/{world.beta.id}", headers=ADMIN_AUTH)
        assert resp.status_code == 204
        assert db.query(TrigVariant).filter_by(id=world.beta.id).first() is None

    def test_delete_in_use_blocked(self, client, world):
        resp = client.delete(f"{ADMIN_URL}/{world.alpha.id}", headers=ADMIN_AUTH)
        assert resp.status_code == 400
        assert "1 trig(s)" in resp.json()["detail"]

    def test_last_of_offered_group_blocked(self, client, db, world):
        world.trig.variant_id = None
        db.delete(world.beta)
        db.commit()

        resp = client.delete(f"{ADMIN_URL}/{world.alpha.id}", headers=ADMIN_AUTH)
        assert resp.status_code == 400
        assert world.widget.name in resp.json()["detail"]

    def test_last_of_unoffered_group_allowed(self, client, world):
        resp = client.delete(f"{ADMIN_URL}/{world.gamma.id}", headers=ADMIN_AUTH)
        assert resp.status_code == 204
        codes = [g["code"] for g in client.get(ADMIN_URL, headers=ADMIN_AUTH).json()]
        assert world.spare not in codes


class TestReference:
    def test_reference_reflects_changes(self, client, world):
        client.patch(
            f"{ADMIN_URL}/{world.beta.id}",
            json={"name": "Bravo", "sort_order": 5},
            headers=ADMIN_AUTH,
        )
        group = next(
            g for g in client.get(REFERENCE_URL).json() if g["code"] == world.offered
        )
        assert [v["label"] for v in group["values"]] == ["Bravo", "Alpha"]
