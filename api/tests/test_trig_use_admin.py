"""
Tests for the historic use / recent use lookups.

Covers the admin CRUD endpoints (/v1/admin/trig-use/{kind}), renames being
applied to trigs, deletion being blocked while a value is in use, the public
reference endpoints reading from the lookups, and admin trig create/update
rejecting values that aren't listed.

The standard values ("none", "Primary", "Passive station", ...) are seeded by
conftest; tests add their own uniquely named values.
"""

import uuid

import pytest
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.trig_use import CurrentUse, HistoricUse

ADMIN_URL = f"{settings.API_V1_STR}/admin/trig-use"
REFERENCE_URL = f"{settings.API_V1_STR}/reference"
ADMIN_AUTH = {"Authorization": "Bearer auth0_admin"}


@pytest.fixture(autouse=True)
def _admin_user(test_user):
    """The auth0_admin token resolves to any existing user."""
    return test_user


@pytest.fixture
def tag() -> str:
    return uuid.uuid4().hex[:6]


@pytest.fixture
def historic_value(db: Session, tag: str) -> HistoricUse:
    value = HistoricUse(name=f"Test use {tag}", sort_order=30000)
    db.add(value)
    db.commit()
    return value


class TestAuth:
    def test_requires_auth(self, client):
        assert client.get(f"{ADMIN_URL}/historic").status_code == 401

    def test_requires_admin(self, client, test_user):
        resp = client.get(
            f"{ADMIN_URL}/historic",
            headers={"Authorization": f"Bearer auth0_user_{test_user.id}"},
        )
        assert resp.status_code == 403

    def test_unknown_kind(self, client):
        resp = client.get(f"{ADMIN_URL}/future", headers=ADMIN_AUTH)
        assert resp.status_code == 422


class TestList:
    def test_lists_in_sort_order(self, client):
        resp = client.get(f"{ADMIN_URL}/historic", headers=ADMIN_AUTH)
        assert resp.status_code == 200, resp.json()
        names = [v["name"] for v in resp.json()]
        assert names.index("none") < names.index("Primary") < names.index("Secondary")

    def test_kinds_are_separate(self, client):
        historic = client.get(f"{ADMIN_URL}/historic", headers=ADMIN_AUTH).json()
        current = client.get(f"{ADMIN_URL}/current", headers=ADMIN_AUTH).json()
        assert "Primary" in [v["name"] for v in historic]
        assert "Primary" not in [v["name"] for v in current]
        assert "Passive station" in [v["name"] for v in current]


class TestCreate:
    def test_create(self, client, db, tag):
        resp = client.post(
            f"{ADMIN_URL}/historic",
            json={
                "name": f"  Zero order {tag} ",
                "description": "Pre-retriangulation",
                "sort_order": 70,
            },
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 201, resp.json()
        body = resp.json()
        assert body["name"] == f"Zero order {tag}"
        assert body["description"] == "Pre-retriangulation"
        assert db.query(HistoricUse).filter_by(id=body["id"]).one().sort_order == 70

    def test_duplicate_name_rejected(self, client):
        resp = client.post(
            f"{ADMIN_URL}/historic",
            json={"name": "Primary", "sort_order": 1},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400
        assert "already exists" in resp.json()["detail"]

    def test_same_name_allowed_in_other_kind(self, client):
        resp = client.post(
            f"{ADMIN_URL}/current",
            json={"name": "Primary", "sort_order": 1},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 201, resp.json()

    def test_recent_use_name_limited_to_column_length(self, client):
        """trig.current_use is VARCHAR(25); historic_use is VARCHAR(30)."""
        name = "x" * 26
        resp = client.post(
            f"{ADMIN_URL}/current",
            json={"name": name, "sort_order": 1},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400
        resp = client.post(
            f"{ADMIN_URL}/historic",
            json={"name": name, "sort_order": 1},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 201, resp.json()

    def test_blank_name_rejected(self, client):
        resp = client.post(
            f"{ADMIN_URL}/historic",
            json={"name": "   ", "sort_order": 1},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400


class TestUpdate:
    def test_update_description_and_order(self, client, historic_value):
        resp = client.patch(
            f"{ADMIN_URL}/historic/{historic_value.id}",
            json={"description": "Described", "sort_order": 5},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 200, resp.json()
        assert resp.json()["description"] == "Described"
        assert resp.json()["sort_order"] == 5
        assert resp.json()["name"] == historic_value.name

    def test_rename_updates_trigs(self, client, db, make_trig, historic_value, tag):
        using = make_trig(historic_use=historic_value.name)
        other = make_trig(historic_use="Primary")
        db.commit()

        resp = client.patch(
            f"{ADMIN_URL}/historic/{historic_value.id}",
            json={"name": f"Renamed {tag}"},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 200, resp.json()
        db.refresh(using)
        db.refresh(other)
        assert using.historic_use == f"Renamed {tag}"
        assert other.historic_use == "Primary"

    def test_rename_only_touches_its_own_column(self, client, db, make_trig):
        """Renaming recent use "none" leaves historic use "none" alone."""
        trig = make_trig(historic_use="none", current_use="none")
        db.commit()
        none_id = db.query(CurrentUse).filter_by(name="none").one().id

        resp = client.patch(
            f"{ADMIN_URL}/current/{none_id}",
            json={"name": "Not in use"},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 200, resp.json()
        db.refresh(trig)
        assert trig.current_use == "Not in use"
        assert trig.historic_use == "none"

    def test_rename_to_existing_name_rejected(self, client, historic_value):
        resp = client.patch(
            f"{ADMIN_URL}/historic/{historic_value.id}",
            json={"name": "Primary"},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400

    def test_not_found(self, client):
        resp = client.patch(
            f"{ADMIN_URL}/historic/999999",
            json={"sort_order": 1},
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 404


class TestDelete:
    def test_delete_unused(self, client, db, historic_value):
        resp = client.get(
            f"{ADMIN_URL}/historic/{historic_value.id}/usage", headers=ADMIN_AUTH
        )
        assert resp.json()["usage_count"] == 0

        resp = client.delete(
            f"{ADMIN_URL}/historic/{historic_value.id}", headers=ADMIN_AUTH
        )
        assert resp.status_code == 204
        assert db.query(HistoricUse).filter_by(id=historic_value.id).first() is None

    def test_delete_in_use_blocked(self, client, db, make_trig, historic_value):
        make_trig(historic_use=historic_value.name)
        make_trig(historic_use=historic_value.name, status_id=10)
        db.commit()

        resp = client.get(
            f"{ADMIN_URL}/historic/{historic_value.id}/usage", headers=ADMIN_AUTH
        )
        assert resp.json()["usage_count"] == 2

        resp = client.delete(
            f"{ADMIN_URL}/historic/{historic_value.id}", headers=ADMIN_AUTH
        )
        assert resp.status_code == 400
        assert "2 trig(s)" in resp.json()["detail"]


class TestReference:
    def test_lists_lookup_values_in_sort_order(self, client, historic_value):
        """Values show even when no trig uses them yet."""
        resp = client.get(f"{REFERENCE_URL}/historic-use")
        assert resp.status_code == 200, resp.json()
        values = [v["value"] for v in resp.json()["values"]]
        assert values.index("none") < values.index("Primary")
        assert values[-1] == historic_value.name

    def test_current_use(self, client):
        resp = client.get(f"{REFERENCE_URL}/current-use")
        assert resp.status_code == 200, resp.json()
        values = [v["value"] for v in resp.json()["values"]]
        assert values[:3] == ["none", "Passive station", "Active station"]


def _admin_payload(trig, **overrides) -> dict:
    payload = {
        "name": trig.name,
        "status_id": 1,
        "type_id": trig.type_id,
        "current_use": "none",
        "historic_use": "none",
        "condition": "G",
        "wgs_lat": "51.5",
        "wgs_long": "-0.12",
        "osgb_eastings": 530000,
        "osgb_northings": 180000,
        "osgb_gridref": "TQ 30000 80000",
        "action": "revisit",
        "admin_comment": "Use test",
    }
    payload.update(overrides)
    return payload


class TestAdminTrigValidation:
    def test_listed_values_accepted(self, client, db, make_trig, historic_value):
        trig = make_trig()
        db.commit()
        resp = client.patch(
            f"{settings.API_V1_STR}/admin/trigs/{trig.id}",
            json=_admin_payload(
                trig,
                historic_use=historic_value.name,
                current_use="Active station",
            ),
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 200, resp.json()
        db.refresh(trig)
        assert trig.historic_use == historic_value.name
        assert trig.current_use == "Active station"

    @pytest.mark.parametrize("field", ["historic_use", "current_use"])
    def test_unlisted_value_rejected(self, client, db, make_trig, field):
        trig = make_trig()
        db.commit()
        resp = client.patch(
            f"{settings.API_V1_STR}/admin/trigs/{trig.id}",
            json=_admin_payload(trig, **{field: "Made up"}),
            headers=ADMIN_AUTH,
        )
        assert resp.status_code == 400
        assert "Made up" in resp.json()["detail"]

    def test_create_with_unlisted_value_rejected(self, client, db, make_trig):
        trig = make_trig()
        db.commit()
        payload = _admin_payload(trig, name="New trig", historic_use="Made up")
        del payload["action"]
        resp = client.post(
            f"{settings.API_V1_STR}/admin/trigs", json=payload, headers=ADMIN_AUTH
        )
        assert resp.status_code == 400
