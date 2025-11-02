"""
Tests to cover require_scopes helper dependency.
"""

# from datetime import timedelta  # Legacy JWT removed

# from api.core.security import create_access_token  # Legacy JWT removed
from fastapi import APIRouter, Depends, FastAPI
from fastapi.testclient import TestClient

from api.api.deps import require_scopes


def _build_app():
    app = FastAPI()
    router = APIRouter()

    @router.get("/admin", dependencies=[Depends(require_scopes("api:admin"))])
    def admin():
        return {"ok": True}

    app.include_router(router)
    return app


def test_require_scopes_missing_auth():
    app = _build_app()
    client = TestClient(app)
    r = client.get("/admin")
    assert r.status_code == 401
    assert "Not authenticated" in r.json().get("detail", "")


# def test_require_scopes_auth0_admin_ok(monkeypatch):
#     """Legacy tokens emulate admin via admin_ind; ensure 200 with legacy token."""
#     app = _build_app()
#     client = TestClient(app)
#     # Legacy token does not carry admin flag; the dependency checks admin
#     # by fetching the user from DB. Here we only ensure a valid legacy token
#     # shape to reach the admin branch (app logic will enforce admin separately
#     # in integration tests).
#     token = create_access_token(subject=999, expires_delta=timedelta(minutes=5))

#     # Patch user lookup and admin check in dependency to simulate admin user
#     class U:
#         id = 999
#         admin_ind = "Y"

#     monkeypatch.setattr("api.api.deps.get_user_by_id", lambda db, user_id: U())
#     monkeypatch.setattr("api.api.deps.is_admin", lambda user: True)

#     r = client.get("/admin", headers={"Authorization": f"Bearer {token}"})
#     assert r.status_code == 200
