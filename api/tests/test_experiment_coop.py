"""Tests for the co-op trigpointing experiment endpoint."""

from datetime import date, datetime, time

import pytest

from api.api.v1.endpoints.experiment import CoopFilterMode
from api.models.user import TLog
from api.schemas.coop import CoopResponse, CoopTrigItem, CoopUser, CoopVisit


@pytest.fixture
def user_a(make_user):
    return make_user(name="Alice")


@pytest.fixture
def user_b(make_user):
    return make_user(name="Bob")


@pytest.fixture
def user_c(make_user):
    return make_user(name="Charlie")


@pytest.fixture
def trigs(make_trig):
    """Create three trigs near central London for distance-based queries."""
    return [
        make_trig(
            waypoint="TP0001",
            name="Trig Alpha",
            wgs_lat=51.5074,
            wgs_long=-0.1278,
        ),
        make_trig(
            waypoint="TP0002",
            name="Trig Beta",
            wgs_lat=51.5080,
            wgs_long=-0.1290,
        ),
        make_trig(
            waypoint="TP0003",
            name="Trig Gamma",
            wgs_lat=51.5100,
            wgs_long=-0.1300,
        ),
    ]


def _make_log(db, trig, user, condition="G", log_date=None):
    log = TLog(
        trig_id=trig.id,
        user_id=user.id,
        date=log_date or date(2024, 1, 1),
        time=time(12, 0, 0),
        osgb_eastings=100000,
        osgb_northings=200000,
        osgb_gridref="TQ 00000 00000",
        fb_number="",
        condition=condition,
        comment="",
        score=5,
        ip_addr="127.0.0.1",
        source="W",
        status="P",
        upd_timestamp=datetime(2024, 1, 1, 12, 0, 0),
    )
    db.add(log)
    db.commit()
    return log


def _auth_headers(user):
    return {"Authorization": f"Bearer auth0_user_{int(user.id)}"}


class TestCoopEndpointValidation:
    def test_requires_authentication(self, client, db, user_a, trigs):
        resp = client.get("/v1/experiment/coop", params={"user_ids": str(user_a.id)})
        assert resp.status_code == 401

    def test_missing_user_ids(self, client, db, user_a, trigs):
        resp = client.get(
            "/v1/experiment/coop",
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 422

    def test_invalid_user_id(self, client, db, user_a, trigs):
        resp = client.get(
            "/v1/experiment/coop",
            params={"user_ids": "abc"},
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 400
        assert "Invalid user ID" in resp.json()["detail"]

    def test_nonexistent_user(self, client, db, user_a, trigs):
        resp = client.get(
            "/v1/experiment/coop",
            params={"user_ids": f"{user_a.id},999999"},
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 404
        assert "not found" in resp.json()["detail"]

    def test_too_many_users(self, client, db, user_a, trigs):
        ids = ",".join(str(i) for i in range(1, 12))
        resp = client.get(
            "/v1/experiment/coop",
            params={"user_ids": ids},
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 400
        assert "Maximum 10" in resp.json()["detail"]


class TestCoopEndpointBasic:
    def test_returns_response_structure(self, client, db, user_a, user_b, trigs):
        resp = client.get(
            "/v1/experiment/coop",
            params={"user_ids": f"{user_a.id},{user_b.id}"},
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "users" in data
        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data
        assert "has_more" in data

    def test_current_user_auto_included(self, client, db, user_a, user_b, trigs):
        resp = client.get(
            "/v1/experiment/coop",
            params={"user_ids": str(user_b.id)},
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        user_ids = [u["id"] for u in data["users"]]
        assert user_a.id in user_ids
        assert user_b.id in user_ids

    def test_returns_trigs_with_visits(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a, "G")
        _make_log(db, trigs[0], user_b, "S")

        resp = client.get(
            "/v1/experiment/coop",
            params={"user_ids": f"{user_a.id},{user_b.id}"},
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] > 0
        trig_item = next((i for i in data["items"] if i["waypoint"] == "TP0001"), None)
        assert trig_item is not None
        assert str(user_a.id) in trig_item["visits"]
        assert str(user_b.id) in trig_item["visits"]
        assert trig_item["visits"][str(user_a.id)]["condition"] == "G"
        assert trig_item["visits"][str(user_b.id)]["condition"] == "S"

    def test_unvisited_trig_has_null_visits(self, client, db, user_a, user_b, trigs):
        resp = client.get(
            "/v1/experiment/coop",
            params={"user_ids": f"{user_a.id},{user_b.id}"},
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) > 0
        for item in data["items"]:
            assert str(user_a.id) in item["visits"]
            assert str(user_b.id) in item["visits"]

    def test_pagination(self, client, db, user_a, user_b, trigs):
        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "limit": "1",
                "skip": "0",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["items"]) <= 1
        assert data["limit"] == 1
        assert data["skip"] == 0

    def test_empty_result(self, client, db, user_a, user_b):
        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "lat": "0.0",
                "lon": "0.0",
                "max_km": "0.001",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["items"] == []
        assert data["has_more"] is False


class TestCoopFilterModes:
    def test_filter_mode_all(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a)
        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "filter_mode": "all",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        assert resp.json()["total"] >= 3

    def test_filter_unvisited_by_all(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a)
        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "filter_mode": "unvisited_by_all",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" not in waypoints

    def test_filter_visited_by_any(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a)
        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "filter_mode": "visited_by_any",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" in waypoints
        assert "TP0002" not in waypoints
        assert "TP0003" not in waypoints

    def test_filter_visited_by_all(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a)
        _make_log(db, trigs[0], user_b)
        _make_log(db, trigs[1], user_a)

        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "filter_mode": "visited_by_all",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" in waypoints
        assert "TP0002" not in waypoints

    def test_filter_unvisited_by_me(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a)
        _make_log(db, trigs[1], user_b)

        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "filter_mode": "unvisited_by_me",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" not in waypoints

    def test_filter_visited_by_me(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a)
        _make_log(db, trigs[1], user_b)

        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "filter_mode": "visited_by_me",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" in waypoints
        assert "TP0002" not in waypoints

    def test_filter_only_visited_by_me(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a)
        _make_log(db, trigs[1], user_a)
        _make_log(db, trigs[1], user_b)

        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "filter_mode": "only_visited_by_me",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" in waypoints
        assert "TP0002" not in waypoints

    def test_filter_visited_by_all_except_me(
        self, client, db, user_a, user_b, user_c, trigs
    ):
        _make_log(db, trigs[0], user_b)
        _make_log(db, trigs[0], user_c)
        _make_log(db, trigs[1], user_a)
        _make_log(db, trigs[1], user_b)
        _make_log(db, trigs[1], user_c)

        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id},{user_c.id}",
                "filter_mode": "visited_by_all_except_me",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" in waypoints
        assert "TP0002" not in waypoints

    def test_filter_visited_by_most(self, client, db, user_a, user_b, user_c, trigs):
        _make_log(db, trigs[0], user_a)
        _make_log(db, trigs[0], user_b)

        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id},{user_c.id}",
                "filter_mode": "visited_by_most",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" in waypoints

    def test_filter_not_visited_by_most(
        self, client, db, user_a, user_b, user_c, trigs
    ):
        _make_log(db, trigs[0], user_a)

        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id},{user_c.id}",
                "filter_mode": "not_visited_by_most",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        waypoints = [i["waypoint"] for i in data["items"]]
        assert "TP0001" in waypoints


class TestCoopFilterModeEnum:
    def test_all_modes(self):
        assert CoopFilterMode.all == "all"
        assert CoopFilterMode.unvisited_by_all == "unvisited_by_all"
        assert CoopFilterMode.unvisited_by_me == "unvisited_by_me"
        assert CoopFilterMode.visited_by_me == "visited_by_me"
        assert CoopFilterMode.only_visited_by_me == "only_visited_by_me"
        assert CoopFilterMode.visited_by_all == "visited_by_all"
        assert CoopFilterMode.visited_by_all_except_me == "visited_by_all_except_me"
        assert CoopFilterMode.visited_by_any == "visited_by_any"
        assert CoopFilterMode.visited_by_most == "visited_by_most"
        assert CoopFilterMode.not_visited_by_most == "not_visited_by_most"


class TestCoopPydanticModels:
    def test_coop_user(self):
        user = CoopUser(id=1, name="Alice")
        assert user.id == 1
        assert user.name == "Alice"

    def test_coop_visit(self):
        visit = CoopVisit(condition="G", date=date(2024, 1, 1))
        assert visit.condition == "G"
        assert visit.date == date(2024, 1, 1)

    def test_coop_visit_no_date(self):
        visit = CoopVisit(condition="G")
        assert visit.date is None

    def test_coop_trig_item(self):
        item = CoopTrigItem(
            id=1,
            waypoint="TP0001",
            name="Test",
            condition="G",
            wgs_lat=51.5,
            wgs_long=-0.1,
            osgb_gridref="TQ 00000 00000",
            visits={"1": CoopVisit(condition="G"), "2": None},
        )
        assert item.id == 1
        assert item.visits["1"].condition == "G"
        assert item.visits["2"] is None

    def test_coop_response(self):
        resp = CoopResponse(
            users=[CoopUser(id=1, name="Alice")],
            items=[],
            total=0,
            skip=0,
            limit=50,
            has_more=False,
        )
        assert resp.total == 0
        assert len(resp.users) == 1

    def test_coop_trig_item_serializes_coords(self):
        item = CoopTrigItem(
            id=1,
            waypoint="TP0001",
            name="Test",
            condition="G",
            wgs_lat=51.50740001,
            wgs_long=-0.12780001,
            osgb_gridref="TQ 00000 00000",
            visits={},
        )
        data = item.model_dump()
        assert isinstance(data["wgs_lat"], float)
        assert isinstance(data["wgs_long"], float)


class TestCoopDistanceAndLocation:
    def test_with_location_returns_distance(self, client, db, user_a, user_b, trigs):
        resp = client.get(
            "/v1/experiment/coop",
            params={
                "user_ids": f"{user_a.id},{user_b.id}",
                "lat": "51.5074",
                "lon": "-0.1278",
                "max_km": "100",
            },
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        for item in data["items"]:
            assert item["distance_km"] is not None

    def test_keeps_most_recent_visit(self, client, db, user_a, user_b, trigs):
        _make_log(db, trigs[0], user_a, "S", date(2023, 1, 1))
        _make_log(db, trigs[0], user_a, "G", date(2024, 6, 1))

        resp = client.get(
            "/v1/experiment/coop",
            params={"user_ids": f"{user_a.id},{user_b.id}"},
            headers=_auth_headers(user_a),
        )
        assert resp.status_code == 200
        data = resp.json()
        trig_item = next((i for i in data["items"] if i["waypoint"] == "TP0001"), None)
        assert trig_item is not None
        visit = trig_item["visits"][str(user_a.id)]
        assert visit["condition"] == "G"
