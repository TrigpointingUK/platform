"""
Tests for the status admin endpoints.
"""

import pytest

from api.models.status import Status


@pytest.fixture
def admin_status_seed(db):
    """Seed a few statuses for admin endpoint tests."""
    for s_id, name, descr in [
        (800, "ADMT1", "Admin Test 1"),
        (801, "ADMT2", "Admin Test 2"),
    ]:
        status = Status(id=s_id, name=name, descr=descr, limit_descr=f"Limit {name}")
        db.add(status)
    db.commit()


class TestGetAllStatusesAdmin:
    def test_returns_statuses(self, client, admin_status_seed, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.get(
            "/v1/admin/status/statuses",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 2

    def test_requires_auth(self, client):
        resp = client.get("/v1/admin/status/statuses")
        assert resp.status_code in (401, 403)


class TestCreateStatusAdmin:
    def test_creates_status(self, client, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.post(
            "/v1/admin/status/statuses",
            json={
                "id": 810,
                "name": "CREAT",
                "descr": "Created",
                "limit_descr": "Limit",
            },
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 201
        assert resp.json()["name"].strip() == "CREAT"

    def test_rejects_duplicate_id(self, client, admin_status_seed, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.post(
            "/v1/admin/status/statuses",
            json={"id": 800, "name": "DUP", "descr": "Dup", "limit_descr": "Lim"},
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 400


class TestUpdateStatusAdmin:
    def test_updates_status(self, client, admin_status_seed, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.patch(
            "/v1/admin/status/statuses/800",
            json={"name": "UPDAT"},
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"].strip() == "UPDAT"

    def test_returns_404_for_nonexistent(self, client, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.patch(
            "/v1/admin/status/statuses/999999",
            json={"name": "X"},
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 404


class TestDeleteStatusAdmin:
    def test_deletes_status(self, client, admin_status_seed, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.delete(
            "/v1/admin/status/statuses/801",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 204

    def test_returns_404_for_nonexistent(self, client, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.delete(
            "/v1/admin/status/statuses/999999",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 404

    def test_rejects_delete_when_in_use(self, client, make_user, make_trig):
        make_user(auth0_user_id="auth0|admin")
        make_trig(status_id=1)
        resp = client.delete(
            "/v1/admin/status/statuses/1",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 400
        assert "used by" in resp.json()["detail"]


class TestGetStatusUsageAdmin:
    def test_returns_usage(self, client, admin_status_seed, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.get(
            "/v1/admin/status/statuses/800/usage",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 200
        assert resp.json()["usage_count"] == 0

    def test_returns_404_for_nonexistent(self, client, make_user):
        make_user(auth0_user_id="auth0|admin")
        resp = client.get(
            "/v1/admin/status/statuses/999999/usage",
            headers={"Authorization": "Bearer auth0_admin"},
        )
        assert resp.status_code == 404
