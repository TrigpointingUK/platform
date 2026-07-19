"""
Tests for the connected applications endpoints
(GET /v1/users/me/connected-apps, DELETE /v1/users/me/connected-apps/{grant_id}).
"""

from unittest.mock import patch

from api.models.user import User


def _create_user(db, auth0_user_id="auth0|9002"):
    from passlib.hash import des_crypt

    user = User(
        name="connectedappstest",
        firstname="Connected",
        surname="Apps",
        email="connectedapps@example.com",
        cryptpw=des_crypt.hash("testpassword"),
        email_valid="Y",
        public_ind="Y",
        auth0_user_id=auth0_user_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


SAMPLE_GRANTS = [
    {
        "id": "gnt_pillarpoint",
        "clientID": "client_abc",
        "user_id": "auth0|9002",
        "audience": "https://api.trigpointing.me/",
        "scope": ["openid", "profile", "offline_access"],
    },
    {
        "id": "gnt_web_stepup",
        "clientID": "client_web",
        "user_id": "auth0|9002",
        "audience": "https://api.trigpointing.me/",
        "scope": ["api:admin"],
    },
]


class TestListConnectedApps:
    """Tests for GET /v1/users/me/connected-apps."""

    def test_requires_authentication(self, client):
        response = client.get("/v1/users/me/connected-apps")
        assert response.status_code == 401

    @patch("api.services.auth0_service.auth0_service.get_client_names")
    @patch("api.services.auth0_service.auth0_service.list_user_grants")
    def test_lists_grants_with_client_names(self, mock_grants, mock_names, client, db):
        user = _create_user(db)
        mock_grants.return_value = SAMPLE_GRANTS
        mock_names.return_value = {"client_abc": "tuk-pillarpoint"}

        response = client.get(
            "/v1/users/me/connected-apps",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        apps = response.json()["apps"]
        assert len(apps) == 2
        assert apps[0] == {
            "grant_id": "gnt_pillarpoint",
            "client_id": "client_abc",
            "client_name": "tuk-pillarpoint",
            "audience": "https://api.trigpointing.me/",
            "scopes": ["openid", "profile", "offline_access"],
        }
        # Unknown client id has no name
        assert apps[1]["client_name"] is None
        mock_grants.assert_called_once_with(str(user.auth0_user_id))

    @patch("api.services.auth0_service.auth0_service.list_user_grants")
    def test_upstream_failure_returns_502(self, mock_grants, client, db):
        user = _create_user(db)
        mock_grants.return_value = None

        response = client.get(
            "/v1/users/me/connected-apps",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 502

    @patch("api.services.auth0_service.auth0_service.list_user_grants")
    def test_user_without_auth0_id_gets_empty_list(self, mock_grants, client, db):
        user = _create_user(db, auth0_user_id=None)

        response = client.get(
            "/v1/users/me/connected-apps",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        assert response.json() == {"apps": []}
        mock_grants.assert_not_called()


class TestRevokeConnectedApp:
    """Tests for DELETE /v1/users/me/connected-apps/{grant_id}."""

    def test_requires_authentication(self, client):
        response = client.delete("/v1/users/me/connected-apps/gnt_pillarpoint")
        assert response.status_code == 401

    @patch("api.services.auth0_service.auth0_service.delete_user_grant")
    @patch("api.services.auth0_service.auth0_service.list_user_grants")
    def test_revokes_own_grant(self, mock_grants, mock_delete, client, db):
        user = _create_user(db)
        mock_grants.return_value = SAMPLE_GRANTS
        mock_delete.return_value = True

        response = client.delete(
            "/v1/users/me/connected-apps/gnt_pillarpoint",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 204
        mock_delete.assert_called_once_with("gnt_pillarpoint")

    @patch("api.services.auth0_service.auth0_service.delete_user_grant")
    @patch("api.services.auth0_service.auth0_service.list_user_grants")
    def test_cannot_revoke_grant_not_owned(self, mock_grants, mock_delete, client, db):
        user = _create_user(db)
        mock_grants.return_value = SAMPLE_GRANTS

        response = client.delete(
            "/v1/users/me/connected-apps/gnt_someone_elses",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 404
        mock_delete.assert_not_called()

    @patch("api.services.auth0_service.auth0_service.delete_user_grant")
    @patch("api.services.auth0_service.auth0_service.list_user_grants")
    def test_delete_failure_returns_502(self, mock_grants, mock_delete, client, db):
        user = _create_user(db)
        mock_grants.return_value = SAMPLE_GRANTS
        mock_delete.return_value = False

        response = client.delete(
            "/v1/users/me/connected-apps/gnt_pillarpoint",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 502
