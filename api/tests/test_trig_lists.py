"""
Integration tests for trig list endpoints.
"""

import pytest
from fastapi.testclient import TestClient

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def auth_header(user_id: int) -> dict:
    return {"Authorization": f"Bearer auth0_user_{user_id}"}


ADMIN_HEADER = {"Authorization": "Bearer auth0_admin"}


# ---------------------------------------------------------------------------
# List CRUD
# ---------------------------------------------------------------------------


class TestListCrud:
    def test_create_list(self, client: TestClient, test_user):
        resp = client.post(
            "/v1/lists",
            json={"name": "My List"},
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["name"] == "My List"
        assert data["visibility"] == "private"
        assert data["editability"] == "private"
        assert data["item_count"] == 0

    def test_get_my_lists(self, client: TestClient, test_user):
        client.post(
            "/v1/lists",
            json={"name": "List A"},
            headers=auth_header(test_user.id),
        )
        client.post(
            "/v1/lists",
            json={"name": "List B"},
            headers=auth_header(test_user.id),
        )
        resp = client.get("/v1/lists", headers=auth_header(test_user.id))
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2
        names = [d["name"] for d in data]
        assert "List A" in names
        assert "List B" in names

    def test_update_list_owner_only(self, client: TestClient, make_user):
        owner = make_user(auth0_user_id="auth0|owner_upd")
        other = make_user(auth0_user_id="auth0|other_upd")
        resp = client.post(
            "/v1/lists",
            json={"name": "OwnedList"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        # Owner can update
        resp = client.patch(
            f"/v1/lists/{list_id}",
            json={"name": "Renamed"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Renamed"

        # Other user cannot update
        resp = client.patch(
            f"/v1/lists/{list_id}",
            json={"name": "Hijacked"},
            headers={"Authorization": f"Bearer auth0_user_{other.id}"},
        )
        assert resp.status_code == 403

    def test_delete_list(self, client: TestClient, test_user):
        resp = client.post(
            "/v1/lists",
            json={"name": "ToDelete"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp = client.delete(
            f"/v1/lists/{list_id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 204

        # Verify deleted
        resp = client.get(
            f"/v1/lists/{list_id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 404

    def test_max_lists_enforced(self, client: TestClient, test_user):
        for i in range(10):
            resp = client.post(
                "/v1/lists",
                json={"name": f"List {i}"},
                headers=auth_header(test_user.id),
            )
            assert resp.status_code == 201

        # 11th should fail
        resp = client.post(
            "/v1/lists",
            json={"name": "Overflow"},
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 400
        assert "Maximum" in resp.json()["detail"]

    def test_reorder_lists(self, client: TestClient, test_user):
        ids = []
        for name in ["First", "Second", "Third"]:
            resp = client.post(
                "/v1/lists",
                json={"name": name},
                headers=auth_header(test_user.id),
            )
            ids.append(resp.json()["id"])

        resp = client.post(
            "/v1/lists/reorder",
            json={
                "ordering": [
                    {"list_id": ids[2], "position": 1000},
                    {"list_id": ids[0], "position": 2000},
                    {"list_id": ids[1], "position": 3000},
                ]
            },
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 204


# ---------------------------------------------------------------------------
# Visibility
# ---------------------------------------------------------------------------


class TestListVisibility:
    def test_private_list_hidden_from_others(self, client: TestClient, make_user):
        owner = make_user(auth0_user_id="auth0|vis_owner")
        other = make_user(auth0_user_id="auth0|vis_other")

        resp = client.post(
            "/v1/lists",
            json={"name": "Secret", "visibility": "private"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        # Other user cannot see it
        resp = client.get(
            f"/v1/lists/{list_id}",
            headers={"Authorization": f"Bearer auth0_user_{other.id}"},
        )
        assert resp.status_code == 404

    def test_public_list_visible_to_anonymous(self, client: TestClient, make_user):
        owner = make_user(auth0_user_id="auth0|pub_owner")
        resp = client.post(
            "/v1/lists",
            json={"name": "Public", "visibility": "public"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        # No auth header
        resp = client.get(f"/v1/lists/{list_id}")
        assert resp.status_code == 200
        assert resp.json()["name"] == "Public"

    def test_non_admin_cannot_set_admins_visibility(
        self, client: TestClient, test_user
    ):
        resp = client.post(
            "/v1/lists",
            json={"name": "Nope", "visibility": "admins"},
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Item CRUD
# ---------------------------------------------------------------------------


class TestItemCrud:
    def test_add_and_list_items(self, client: TestClient, test_user, make_trig):
        trig = make_trig()

        # Create a list
        resp = client.post(
            "/v1/lists",
            json={"name": "Favourites"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        # Add item
        resp = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 201
        item = resp.json()
        assert item["trig_id"] == trig.id
        assert item["created_by"] == test_user.id
        assert item["trig"]["waypoint"] == trig.waypoint

        # List items
        resp = client.get(
            f"/v1/lists/{list_id}/items",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1

    def test_duplicate_item_idempotent(self, client: TestClient, test_user, make_trig):
        trig = make_trig()
        resp = client.post(
            "/v1/lists",
            json={"name": "Dupes"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp1 = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers=auth_header(test_user.id),
        )
        assert resp1.status_code == 201

        resp2 = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers=auth_header(test_user.id),
        )
        assert resp2.status_code == 201
        assert resp1.json()["id"] == resp2.json()["id"]

    def test_remove_item(self, client: TestClient, test_user, make_trig):
        trig = make_trig()
        resp = client.post(
            "/v1/lists",
            json={"name": "Remove"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers=auth_header(test_user.id),
        )
        item_id = resp.json()["id"]

        resp = client.delete(
            f"/v1/lists/{list_id}/items/{item_id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 204

        resp = client.get(
            f"/v1/lists/{list_id}/items",
            headers=auth_header(test_user.id),
        )
        assert resp.json()["total"] == 0

    def test_update_item_sets_updated_by(
        self, client: TestClient, test_user, make_trig
    ):
        trig = make_trig()
        resp = client.post(
            "/v1/lists",
            json={"name": "Update"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers=auth_header(test_user.id),
        )
        item_id = resp.json()["id"]
        assert resp.json()["updated_by"] is None

        resp = client.patch(
            f"/v1/lists/{list_id}/items/{item_id}",
            json={"name": "Noted"},
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Noted"
        assert resp.json()["updated_by"] == test_user.id
        assert resp.json()["updated_at"] is not None

    def test_max_items_limit_unit(self, db, test_user, make_trig):
        """Unit test: verify the CRUD layer rejects items beyond the limit."""
        from unittest.mock import patch

        from api.crud.trig_list import add_item, create_list

        trig_list = create_list(db, test_user.id, name="Big")
        trig = make_trig()
        db.flush()

        with patch("api.crud.trig_list.get_list_item_count", return_value=1000):
            with pytest.raises(ValueError, match="Maximum"):
                add_item(db, trig_list.id, trig.id, test_user.id)


# ---------------------------------------------------------------------------
# Editability
# ---------------------------------------------------------------------------


class TestEditability:
    def test_public_editability_allows_other_users(
        self, client: TestClient, make_user, make_trig
    ):
        owner = make_user(auth0_user_id="auth0|edit_owner")
        other = make_user(auth0_user_id="auth0|edit_other")
        trig = make_trig()

        resp = client.post(
            "/v1/lists",
            json={"name": "Open", "visibility": "public", "editability": "public"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        # Other user can add items
        resp = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers={"Authorization": f"Bearer auth0_user_{other.id}"},
        )
        assert resp.status_code == 201
        assert resp.json()["created_by"] == other.id

    def test_private_editability_blocks_other_users(
        self, client: TestClient, make_user, make_trig
    ):
        owner = make_user(auth0_user_id="auth0|priv_edit_owner")
        other = make_user(auth0_user_id="auth0|priv_edit_other")
        trig = make_trig()

        resp = client.post(
            "/v1/lists",
            json={"name": "Closed", "visibility": "public", "editability": "private"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers={"Authorization": f"Bearer auth0_user_{other.id}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Default list / toggle
# ---------------------------------------------------------------------------


class TestDefaultList:
    def test_toggle_creates_default_list(
        self, client: TestClient, test_user, make_trig
    ):
        trig = make_trig()

        resp = client.post(
            f"/v1/lists/default/toggle/{trig.id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["action"] == "added"

        # Should have created a default list named "Marked"
        resp = client.get("/v1/lists", headers=auth_header(test_user.id))
        lists = resp.json()
        assert any(entry["name"] == "Marked" and entry["is_default"] for entry in lists)

    def test_toggle_removes_on_second_call(
        self, client: TestClient, test_user, make_trig
    ):
        trig = make_trig()

        client.post(
            f"/v1/lists/default/toggle/{trig.id}",
            headers=auth_header(test_user.id),
        )
        resp = client.post(
            f"/v1/lists/default/toggle/{trig.id}",
            headers=auth_header(test_user.id),
        )
        assert resp.json()["action"] == "removed"


# ---------------------------------------------------------------------------
# Generic list toggle
# ---------------------------------------------------------------------------


class TestListToggle:
    def test_toggle_adds_and_removes(self, client: TestClient, test_user, make_trig):
        trig = make_trig()
        resp = client.post(
            "/v1/lists",
            json={"name": "Toggleable"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/toggle/{trig.id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "added"
        assert resp.json()["list_id"] == list_id

        resp = client.post(
            f"/v1/lists/{list_id}/toggle/{trig.id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["action"] == "removed"

    def test_toggle_respects_editability(
        self, client: TestClient, make_user, make_trig
    ):
        owner = make_user(auth0_user_id="auth0|toggle_owner")
        other = make_user(auth0_user_id="auth0|toggle_other")
        trig = make_trig()

        resp = client.post(
            "/v1/lists",
            json={"name": "Private", "visibility": "public", "editability": "private"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/toggle/{trig.id}",
            headers={"Authorization": f"Bearer auth0_user_{other.id}"},
        )
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Batch membership
# ---------------------------------------------------------------------------


class TestBatchMembership:
    def test_membership_query(self, client: TestClient, test_user, make_trig):
        trig1 = make_trig()
        trig2 = make_trig()

        resp = client.post(
            "/v1/lists",
            json={"name": "Batch"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig1.id},
            headers=auth_header(test_user.id),
        )

        resp = client.get(
            f"/v1/lists/membership?trig_ids={trig1.id},{trig2.id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        items = resp.json()["items"]
        trig1_entry = next(i for i in items if i["trig_id"] == trig1.id)
        trig2_entry = next(i for i in items if i["trig_id"] == trig2.id)
        assert list_id in trig1_entry["list_ids"]
        assert trig2_entry["list_ids"] == []


# ---------------------------------------------------------------------------
# Cascade delete
# ---------------------------------------------------------------------------


class TestSetDefault:
    def test_set_default_list(self, client: TestClient, test_user):
        resp = client.post(
            "/v1/lists",
            json={"name": "First"},
            headers=auth_header(test_user.id),
        )
        list_a = resp.json()["id"]

        resp = client.post(
            "/v1/lists",
            json={"name": "Second"},
            headers=auth_header(test_user.id),
        )
        list_b = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_b}/set-default",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["default_list_id"] == list_b

        # Verify via list endpoint
        resp = client.get("/v1/lists", headers=auth_header(test_user.id))
        lists = resp.json()
        for entry in lists:
            if entry["id"] == list_b:
                assert entry["is_default"] is True
            elif entry["id"] == list_a:
                assert entry["is_default"] is False

    def test_set_default_other_user_forbidden(self, client: TestClient, make_user):
        owner = make_user(auth0_user_id="auth0|def_owner")
        other = make_user(auth0_user_id="auth0|def_other")

        resp = client.post(
            "/v1/lists",
            json={"name": "Owned"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/set-default",
            headers={"Authorization": f"Bearer auth0_user_{other.id}"},
        )
        assert resp.status_code == 403


class TestGetListDetail:
    def test_get_own_private_list(self, client: TestClient, test_user):
        resp = client.post(
            "/v1/lists",
            json={"name": "Mine"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp = client.get(
            f"/v1/lists/{list_id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["name"] == "Mine"

    def test_get_nonexistent_list_returns_404(self, client: TestClient, test_user):
        resp = client.get(
            "/v1/lists/999999",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 404


class TestItemReorder:
    def test_reorder_items(self, client: TestClient, test_user, make_trig):
        resp = client.post(
            "/v1/lists",
            json={"name": "Reorder"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        item_ids = []
        for _ in range(3):
            trig = make_trig()
            resp = client.post(
                f"/v1/lists/{list_id}/items",
                json={"trig_id": trig.id},
                headers=auth_header(test_user.id),
            )
            item_ids.append(resp.json()["id"])

        resp = client.post(
            f"/v1/lists/{list_id}/items/reorder",
            json={
                "ordering": [
                    {"item_id": item_ids[2], "position": 1000},
                    {"item_id": item_ids[0], "position": 2000},
                    {"item_id": item_ids[1], "position": 3000},
                ]
            },
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 204

        # Verify new ordering
        resp = client.get(
            f"/v1/lists/{list_id}/items",
            headers=auth_header(test_user.id),
        )
        items = resp.json()["items"]
        assert items[0]["id"] == item_ids[2]
        assert items[1]["id"] == item_ids[0]
        assert items[2]["id"] == item_ids[1]

    def test_reorder_items_respects_editability(
        self, client: TestClient, make_user, make_trig
    ):
        owner = make_user(auth0_user_id="auth0|ro_owner")
        other = make_user(auth0_user_id="auth0|ro_other")

        resp = client.post(
            "/v1/lists",
            json={"name": "Locked", "visibility": "public", "editability": "private"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/items/reorder",
            json={"ordering": []},
            headers={"Authorization": f"Bearer auth0_user_{other.id}"},
        )
        assert resp.status_code == 403


class TestItemDescription:
    def test_update_item_description(self, client: TestClient, test_user, make_trig):
        trig = make_trig()
        resp = client.post(
            "/v1/lists",
            json={"name": "Notes"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers=auth_header(test_user.id),
        )
        item_id = resp.json()["id"]
        assert resp.json()["description"] is None

        resp = client.patch(
            f"/v1/lists/{list_id}/items/{item_id}",
            json={"description": "A great trig to visit in summer"},
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200
        assert resp.json()["description"] == "A great trig to visit in summer"
        assert resp.json()["updated_by"] == test_user.id

    def test_clear_item_description(self, client: TestClient, test_user, make_trig):
        trig = make_trig()
        resp = client.post(
            "/v1/lists",
            json={"name": "ClearDesc"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id, "description": "Initial note"},
            headers=auth_header(test_user.id),
        )
        item_id = resp.json()["id"]

        resp = client.patch(
            f"/v1/lists/{list_id}/items/{item_id}",
            json={"description": None},
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 200

    def test_add_item_with_description(self, client: TestClient, test_user, make_trig):
        trig = make_trig()
        resp = client.post(
            "/v1/lists",
            json={"name": "WithDesc"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        resp = client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id, "description": "Planning a visit next week"},
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 201
        assert resp.json()["description"] == "Planning a visit next week"


class TestPublicListItems:
    def test_public_list_items_visible_without_auth(
        self, client: TestClient, make_user, make_trig
    ):
        owner = make_user(auth0_user_id="auth0|pubitem_owner")
        trig = make_trig()

        resp = client.post(
            "/v1/lists",
            json={"name": "Public Favs", "visibility": "public"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )

        # Anonymous access
        resp = client.get(f"/v1/lists/{list_id}/items")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["items"][0]["trig"]["waypoint"] == trig.waypoint

    def test_private_list_items_hidden_without_auth(
        self, client: TestClient, make_user, make_trig
    ):
        owner = make_user(auth0_user_id="auth0|privitem_owner")
        trig = make_trig()

        resp = client.post(
            "/v1/lists",
            json={"name": "Private Favs", "visibility": "private"},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )
        list_id = resp.json()["id"]

        client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers={"Authorization": f"Bearer auth0_user_{owner.id}"},
        )

        # Anonymous access should return 404
        resp = client.get(f"/v1/lists/{list_id}/items")
        assert resp.status_code == 404


class TestCascadeDelete:
    def test_deleting_list_removes_items(
        self, client: TestClient, test_user, make_trig
    ):
        trig = make_trig()
        resp = client.post(
            "/v1/lists",
            json={"name": "Cascade"},
            headers=auth_header(test_user.id),
        )
        list_id = resp.json()["id"]

        client.post(
            f"/v1/lists/{list_id}/items",
            json={"trig_id": trig.id},
            headers=auth_header(test_user.id),
        )

        resp = client.delete(
            f"/v1/lists/{list_id}",
            headers=auth_header(test_user.id),
        )
        assert resp.status_code == 204

        # Membership should be gone
        resp = client.get(
            f"/v1/lists/membership?trig_ids={trig.id}",
            headers=auth_header(test_user.id),
        )
        entry = resp.json()["items"][0]
        assert entry["list_ids"] == []
