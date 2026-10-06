"""
Tests for trig variants: generic qualifiers on a trig's type (e.g. a Buried
Block's detector material).

Covers the `variants` filter (list, points), trig responses, the admin
create/update validation against trig_type.variant_group, the variant-groups
reference endpoint, and the type admin variant_group field.

Each test seeds its own category and variant groups (unique codes) so requests
can be scoped with `categories=` and ignore other test data.
"""

import uuid
from datetime import date, time
from types import SimpleNamespace

import pytest
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.trig_type import TrigCategory, TrigType
from api.models.trig_variant import TrigVariant
from api.models.user import TLog

TRIGS_URL = f"{settings.API_V1_STR}/trigs"
ADMIN_AUTH = {"Authorization": "Bearer auth0_admin"}


@pytest.fixture
def variant_world(db: Session, make_trig):
    """
    A unique category with:

    - Buried Block and Bolt types in a "detector" variant group
    - a Pillar type in a separate "pillar" variant group
    - a Rivet type with no variants

    and trigs:

    - bb_ring / bb_plate / bb_plain: Buried Blocks (ring, plate, not recorded)
    - bolt_ring: Bolt with ring
    - rivet: Rivet
    """
    tag = uuid.uuid4().hex[:8].upper()
    detector = f"DET_{tag}"
    pillar_group = f"PIL_{tag}"
    category = TrigCategory(
        code=f"VAR_{tag}",
        name="Test Survey Mark",
        sort_order=int(tag[:4], 16) % 9000 + 1000,
    )
    db.add(category)
    db.flush()

    def make_type(code, name, sort_order, group=None):
        return TrigType(
            category_id=category.id,
            code=f"{code}_{tag}",
            name=name,
            sort_order=sort_order,
            variant_group=group,
        )

    buried = make_type("BB", "Buried Block", 1, detector)
    bolt = make_type("BOLT", "Bolt", 2, detector)
    pillar = make_type("PIL", "Pillar", 3, pillar_group)
    rivet = make_type("RIV", "Rivet", 4)

    def make_variant(group, group_name, code, name, sort_order):
        return TrigVariant(
            group_code=group,
            group_name=group_name,
            code=f"{code}_{tag}",
            name=name,
            sort_order=sort_order,
        )

    ring = make_variant(detector, "Detector material", "RING", "Concrete ring", 1)
    plate = make_variant(detector, "Detector material", "PLATE", "Detector plate", 2)
    hotine = make_variant(pillar_group, "Pillar design", "HOT", "Hotine", 1)
    db.add_all([buried, bolt, pillar, rivet, ring, plate, hotine])
    db.flush()

    w = SimpleNamespace(
        category=category.code,
        detector=detector,
        buried=buried,
        bolt=bolt,
        pillar=pillar,
        rivet=rivet,
        ring=ring,
        plate=plate,
        hotine=hotine,
        bb_ring=make_trig(type_id=buried.id, variant_id=ring.id),
        bb_plate=make_trig(type_id=buried.id, variant_id=plate.id),
        bb_plain=make_trig(type_id=buried.id),
        bolt_ring=make_trig(type_id=bolt.id, variant_id=ring.id),
        rivet_trig=make_trig(type_id=rivet.id),
    )
    db.commit()
    return w


def _list_ids(client, w, **params) -> list[int]:
    resp = client.get(
        TRIGS_URL, params={"categories": w.category, "limit": 50, **params}
    )
    assert resp.status_code == 200, resp.json()
    return sorted(item["id"] for item in resp.json()["items"])


class TestVariantFilter:
    def test_filters_by_single_variant_across_types(self, client, variant_world):
        w = variant_world
        ids = _list_ids(client, w, variants=w.ring.code)
        assert ids == sorted([w.bb_ring.id, w.bolt_ring.id])

    def test_filters_by_several_variants(self, client, variant_world):
        w = variant_world
        ids = _list_ids(client, w, variants=f"{w.ring.code},{w.plate.code.lower()}")
        assert ids == sorted([w.bb_ring.id, w.bb_plate.id, w.bolt_ring.id])

    def test_combines_with_type_filter(self, client, variant_world):
        w = variant_world
        ids = _list_ids(client, w, types=w.buried.code, variants=w.ring.code)
        assert ids == [w.bb_ring.id]

    def test_unknown_variant_matches_nothing(self, client, variant_world):
        assert _list_ids(client, variant_world, variants="NO_SUCH_VARIANT") == []

    def test_not_recorded_matches_trigs_without_variant(self, client, variant_world):
        w = variant_world
        ids = _list_ids(client, w, variants="NOT_RECORDED")
        assert ids == sorted([w.bb_plain.id, w.rivet_trig.id])

    def test_not_recorded_combines_with_variants(self, client, variant_world):
        w = variant_world
        ids = _list_ids(client, w, variants=f"{w.ring.code},not_recorded")
        assert ids == sorted(
            [w.bb_ring.id, w.bolt_ring.id, w.bb_plain.id, w.rivet_trig.id]
        )

    def test_no_filter_includes_unrecorded(self, client, variant_world):
        w = variant_world
        assert w.bb_plain.id in _list_ids(client, w)

    def test_points_carry_variant_name(self, client, variant_world):
        w = variant_world
        resp = client.get(
            f"{TRIGS_URL}/points",
            params={"categories": w.category, "variants": w.plate.code},
        )
        assert resp.status_code == 200, resp.json()
        body = resp.json()
        col = body["fields"].index("variant_name")
        assert [row[col] for row in body["rows"]] == ["Detector plate"]

    def test_trig_detail_exposes_variant(self, client, variant_world):
        w = variant_world
        resp = client.get(f"{TRIGS_URL}/{w.bb_ring.id}")
        assert resp.status_code == 200, resp.json()
        body = resp.json()
        assert body["variant_code"] == w.ring.code
        assert body["variant_name"] == "Concrete ring"
        assert body["variant_group_name"] == "Detector material"

        resp = client.get(f"{TRIGS_URL}/{w.bb_plain.id}")
        assert resp.json()["variant_name"] is None


def _admin_payload(trig, **overrides) -> dict:
    payload = {
        "name": trig.name,
        "status_id": 1,
        "type_id": trig.type_id,
        "variant_code": None,
        "current_use": "none",
        "historic_use": "none",
        "condition": "G",
        "wgs_lat": "51.5",
        "wgs_long": "-0.12",
        "osgb_eastings": 530000,
        "osgb_northings": 180000,
        "osgb_gridref": "TQ 30000 80000",
        "action": "revisit",
        "admin_comment": "Variant test",
    }
    payload.update(overrides)
    return payload


def _patch_trig(client, trig, **overrides):
    return client.patch(
        f"{settings.API_V1_STR}/admin/trigs/{trig.id}",
        json=_admin_payload(trig, **overrides),
        headers=ADMIN_AUTH,
    )


@pytest.fixture
def variant_logs(db: Session, test_user, variant_world):
    """A log on the ringed Buried Block and one on the unrecorded one."""
    tag = uuid.uuid4().hex[:8]

    def make_log(trig):
        log = TLog(
            trig_id=trig.id,
            user_id=test_user.id,
            date=date(2024, 5, 1),
            time=time(10, 0, 0),
            osgb_eastings=100000,
            osgb_northings=200000,
            osgb_gridref="TQ 00000 00000",
            fb_number="",
            condition="G",
            comment=f"VariantLogComment_{tag}",
            score=7,
            ip_addr="127.0.0.1",
            source="W",
        )
        db.add(log)
        return log

    logs = SimpleNamespace(
        tag=tag,
        ring=make_log(variant_world.bb_ring),
        plain=make_log(variant_world.bb_plain),
    )
    db.commit()
    return logs


class TestLogsCarryVariant:
    def test_trig_logs(self, client, variant_world, variant_logs):
        resp = client.get(f"{TRIGS_URL}/{variant_world.bb_ring.id}/logs")
        assert resp.status_code == 200
        [item] = resp.json()["items"]
        assert item["trig_type_name"] == "Buried Block"
        assert item["trig_variant_name"] == "Concrete ring"

    def test_log_detail_without_variant(self, client, variant_logs):
        resp = client.get(f"{settings.API_V1_STR}/logs/{variant_logs.plain.id}")
        assert resp.status_code == 200
        assert resp.json()["trig_type_name"] == "Buried Block"
        assert resp.json()["trig_variant_name"] is None

    def test_log_search(self, client, variant_logs):
        resp = client.get(
            f"{settings.API_V1_STR}/locations/search/logs/substring",
            params={"q": f"VariantLogComment_{variant_logs.tag}"},
        )
        assert resp.status_code == 200
        variants = {i["id"]: i["trig_variant_name"] for i in resp.json()["items"]}
        assert variants == {
            variant_logs.ring.id: "Concrete ring",
            variant_logs.plain.id: None,
        }


class TestAdminVariant:
    def test_set_variant_in_types_group(self, client, db, variant_world):
        w = variant_world
        resp = _patch_trig(client, w.bb_plain, variant_code=w.plate.code)
        assert resp.status_code == 200, resp.json()
        assert resp.json()["variant_code"] == w.plate.code
        db.refresh(w.bb_plain)
        assert w.bb_plain.variant_id == w.plate.id

    def test_variant_rejected_for_type_without_variants(self, client, variant_world):
        w = variant_world
        resp = _patch_trig(client, w.rivet_trig, variant_code=w.ring.code)
        assert resp.status_code == 400

    def test_variant_from_another_group_rejected(self, client, variant_world):
        """A Pillar-design variant can't go on a Buried Block."""
        w = variant_world
        resp = _patch_trig(client, w.bb_plain, variant_code=w.hotine.code)
        assert resp.status_code == 400

    def test_unknown_variant_rejected(self, client, variant_world):
        w = variant_world
        resp = _patch_trig(client, w.bb_plain, variant_code="NOPE")
        assert resp.status_code == 400

    def test_omitting_variant_clears_it(self, client, db, variant_world):
        """Changing a ringed Buried Block to a Rivet drops the variant."""
        w = variant_world
        resp = _patch_trig(client, w.bb_ring, type_id=w.rivet.id)
        assert resp.status_code == 200, resp.json()
        db.refresh(w.bb_ring)
        assert w.bb_ring.variant_id is None

    def test_create_with_variant(self, client, variant_world):
        w = variant_world
        payload = _admin_payload(
            w.bb_plain,
            name="New ringed bolt",
            type_id=w.bolt.id,
            variant_code=w.ring.code,
        )
        del payload["action"]
        resp = client.post(
            f"{settings.API_V1_STR}/admin/trigs", json=payload, headers=ADMIN_AUTH
        )
        assert resp.status_code == 201, resp.json()
        assert resp.json()["variant_code"] == w.ring.code


class TestVariantGroupsReference:
    def test_lists_groups_with_values_in_order(self, client, variant_world):
        w = variant_world
        resp = client.get(f"{settings.API_V1_STR}/reference/variant-groups")
        assert resp.status_code == 200, resp.json()
        groups = {g["code"]: g for g in resp.json()}
        detector = groups[w.detector]
        assert detector["name"] == "Detector material"
        assert [v["value"] for v in detector["values"]] == [
            w.ring.code,
            w.plate.code,
        ]
        assert detector["values"][0]["label"] == "Concrete ring"


class TestTypeAdminVariantGroup:
    def _url(self, trig_type):
        return f"{settings.API_V1_STR}/admin/types/types/{trig_type.id}"

    def test_set_and_clear_group(self, client, variant_world):
        w = variant_world
        url = self._url(w.rivet)
        resp = client.patch(url, json={"variant_group": w.detector}, headers=ADMIN_AUTH)
        assert resp.status_code == 200, resp.json()
        assert resp.json()["variant_group"] == w.detector

        # Untouched by an unrelated update
        resp = client.patch(url, json={"name": "Rivet renamed"}, headers=ADMIN_AUTH)
        assert resp.json()["variant_group"] == w.detector

        resp = client.patch(url, json={"variant_group": ""}, headers=ADMIN_AUTH)
        assert resp.json()["variant_group"] is None

    def test_unknown_group_rejected(self, client, variant_world):
        resp = client.patch(
            self._url(variant_world.rivet),
            json={"variant_group": "NO_SUCH_GROUP"},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400

    def test_public_types_expose_group(self, client, variant_world):
        w = variant_world
        resp = client.get(f"{settings.API_V1_STR}/types/categories")
        assert resp.status_code == 200, resp.json()
        types = {
            t["code"]: t
            for cat in resp.json()
            if cat["code"] == w.category
            for t in cat["types"]
        }
        assert types[w.buried.code]["variant_group"] == w.detector
        assert types[w.rivet.code]["variant_group"] is None
