"""
Tests for photo rating endpoints.

Tests GET/PUT/DELETE /v1/photos/{photo_id}/rating and POST /v1/photos/ratings.
"""

import uuid
from datetime import date, time

import pytest
from fastapi.testclient import TestClient

from api.models.server import Server
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, TPhotoVote, User


@pytest.fixture
def rating_test_data(db):
    """Create test data for photo rating tests."""
    unique = uuid.uuid4().hex[:6]

    user_a = User(
        name=f"RaterA_{unique}",
        firstname="Rater",
        surname="A",
        email=f"ratera_{unique}@example.invalid",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
    )
    user_b = User(
        name=f"RaterB_{unique}",
        firstname="Rater",
        surname="B",
        email=f"raterb_{unique}@example.invalid",
        cryptpw="",
        email_valid="Y",
        public_ind="Y",
    )
    db.add_all([user_a, user_b])
    db.flush()

    trig = Trig(
        waypoint=f"RT{unique[:4]}",
        name=f"RatingTrig_{unique}",
        fb_number=f"RTFB{unique[:3]}",
        stn_number="STN001",
        status_id=1,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        condition="G",
        wgs_lat=51.5,
        wgs_long=-0.1,
        wgs_height=100,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=100,
        town="TestTown",
        permission_ind="Y",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 1),
        crt_time=time(0, 0, 0),
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.flush()

    log = TLog(
        trig_id=trig.id,
        user_id=user_a.id,
        date=date(2024, 6, 1),
        time=time(10, 0, 0),
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        fb_number="",
        condition="G",
        comment=f"Log for rating tests {unique}",
        score=7,
        ip_addr="127.0.0.1",
        source="W",
    )
    db.add(log)
    db.flush()

    server = db.query(Server).filter(Server.id == 1).first()
    if not server:
        server = Server(
            id=1,
            url="https://example.invalid/photos/",
            path="/photos/",
            name="Test Server",
        )
        db.add(server)
        db.flush()

    photo = TPhoto(
        tlog_id=log.id,
        server_id=1,
        type="T",
        filename=f"rating_{unique}.jpg",
        filesize=5000,
        height=400,
        width=600,
        icon_filename=f"rating_{unique}_thumb.jpg",
        icon_filesize=500,
        icon_height=75,
        icon_width=100,
        name=f"Rating Photo {unique}",
        text_desc="Photo for rating tests",
        ip_addr="127.0.0.1",
        public_ind="Y",
        deleted_ind="N",
        source="W",
    )
    db.add(photo)
    db.commit()

    return {
        "user_a": user_a,
        "user_b": user_b,
        "photo": photo,
    }


class TestGetPhotoRating:
    """Tests for GET /v1/photos/{photo_id}/rating."""

    def test_get_rating_unauthenticated_empty(
        self, client: TestClient, rating_test_data
    ):
        photo = rating_test_data["photo"]
        resp = client.get(f"/v1/photos/{photo.id}/rating")
        assert resp.status_code == 200
        data = resp.json()
        assert data["average_score"] is None
        assert data["vote_count"] == 0
        assert data["user_score"] is None

    def test_get_rating_nonexistent_photo(self, client: TestClient):
        resp = client.get("/v1/photos/999999999/rating")
        assert resp.status_code == 404

    def test_get_rating_authenticated_includes_user_score(
        self, client: TestClient, rating_test_data, db
    ):
        photo = rating_test_data["photo"]
        user = rating_test_data["user_a"]

        vote = TPhotoVote(tphoto_id=photo.id, user_id=user.id, score=7)
        db.add(vote)
        db.commit()

        resp = client.get(
            f"/v1/photos/{photo.id}/rating",
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["average_score"] == 7.0
        assert data["vote_count"] == 1
        assert data["user_score"] == 7


class TestRatePhoto:
    """Tests for PUT /v1/photos/{photo_id}/rating."""

    def test_rate_photo_unauthenticated(self, client: TestClient, rating_test_data):
        photo = rating_test_data["photo"]
        resp = client.put(f"/v1/photos/{photo.id}/rating", json={"score": 8})
        assert resp.status_code == 401

    def test_rate_photo_success(self, client: TestClient, rating_test_data):
        photo = rating_test_data["photo"]
        user = rating_test_data["user_a"]

        resp = client.put(
            f"/v1/photos/{photo.id}/rating",
            json={"score": 8},
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_score"] == 8
        assert data["average_score"] == 8.0
        assert data["vote_count"] == 1

    def test_rate_photo_upsert_updates(self, client: TestClient, rating_test_data):
        photo = rating_test_data["photo"]
        user = rating_test_data["user_a"]
        headers = {"Authorization": f"Bearer auth0_user_{user.id}"}

        client.put(f"/v1/photos/{photo.id}/rating", json={"score": 5}, headers=headers)
        resp = client.put(
            f"/v1/photos/{photo.id}/rating", json={"score": 9}, headers=headers
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_score"] == 9
        assert data["vote_count"] == 1

    def test_rate_photo_multiple_users(self, client: TestClient, rating_test_data):
        photo = rating_test_data["photo"]
        user_a = rating_test_data["user_a"]
        user_b = rating_test_data["user_b"]

        client.put(
            f"/v1/photos/{photo.id}/rating",
            json={"score": 6},
            headers={"Authorization": f"Bearer auth0_user_{user_a.id}"},
        )
        resp = client.put(
            f"/v1/photos/{photo.id}/rating",
            json={"score": 10},
            headers={"Authorization": f"Bearer auth0_user_{user_b.id}"},
        )
        data = resp.json()
        assert data["vote_count"] == 2
        assert data["average_score"] == 8.0
        assert data["user_score"] == 10

    def test_rate_photo_invalid_score_too_low(
        self, client: TestClient, rating_test_data
    ):
        photo = rating_test_data["photo"]
        user = rating_test_data["user_a"]
        resp = client.put(
            f"/v1/photos/{photo.id}/rating",
            json={"score": 0},
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert resp.status_code == 422

    def test_rate_photo_invalid_score_too_high(
        self, client: TestClient, rating_test_data
    ):
        photo = rating_test_data["photo"]
        user = rating_test_data["user_a"]
        resp = client.put(
            f"/v1/photos/{photo.id}/rating",
            json={"score": 11},
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert resp.status_code == 422

    def test_rate_nonexistent_photo(self, client: TestClient, rating_test_data):
        user = rating_test_data["user_a"]
        resp = client.put(
            "/v1/photos/999999999/rating",
            json={"score": 5},
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )
        assert resp.status_code == 404


class TestDeletePhotoRating:
    """Tests for DELETE /v1/photos/{photo_id}/rating."""

    def test_delete_rating_unauthenticated(self, client: TestClient, rating_test_data):
        photo = rating_test_data["photo"]
        resp = client.delete(f"/v1/photos/{photo.id}/rating")
        assert resp.status_code == 401

    def test_delete_rating_success(self, client: TestClient, rating_test_data):
        photo = rating_test_data["photo"]
        user = rating_test_data["user_a"]
        headers = {"Authorization": f"Bearer auth0_user_{user.id}"}

        client.put(f"/v1/photos/{photo.id}/rating", json={"score": 7}, headers=headers)
        resp = client.delete(f"/v1/photos/{photo.id}/rating", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["user_score"] is None
        assert data["vote_count"] == 0

    def test_delete_rating_preserves_other_votes(
        self, client: TestClient, rating_test_data
    ):
        photo = rating_test_data["photo"]
        user_a = rating_test_data["user_a"]
        user_b = rating_test_data["user_b"]

        client.put(
            f"/v1/photos/{photo.id}/rating",
            json={"score": 4},
            headers={"Authorization": f"Bearer auth0_user_{user_a.id}"},
        )
        client.put(
            f"/v1/photos/{photo.id}/rating",
            json={"score": 10},
            headers={"Authorization": f"Bearer auth0_user_{user_b.id}"},
        )

        resp = client.delete(
            f"/v1/photos/{photo.id}/rating",
            headers={"Authorization": f"Bearer auth0_user_{user_a.id}"},
        )
        data = resp.json()
        assert data["vote_count"] == 1
        assert data["average_score"] == 10.0
        assert data["user_score"] is None


class TestGetRatingsBatch:
    """Tests for POST /v1/photos/ratings."""

    def test_batch_ratings_empty(self, client: TestClient, rating_test_data):
        photo = rating_test_data["photo"]
        resp = client.post(
            "/v1/photos/ratings",
            json={"photo_ids": [photo.id]},
        )
        assert resp.status_code == 200
        data = resp.json()
        pid_str = str(photo.id)
        assert pid_str in data["ratings"]
        assert data["ratings"][pid_str]["vote_count"] == 0

    def test_batch_ratings_with_votes(self, client: TestClient, rating_test_data):
        photo = rating_test_data["photo"]
        user_a = rating_test_data["user_a"]

        client.put(
            f"/v1/photos/{photo.id}/rating",
            json={"score": 6},
            headers={"Authorization": f"Bearer auth0_user_{user_a.id}"},
        )

        resp = client.post(
            "/v1/photos/ratings",
            json={"photo_ids": [photo.id]},
        )
        assert resp.status_code == 200
        data = resp.json()
        pid_str = str(photo.id)
        assert data["ratings"][pid_str]["vote_count"] == 1
        assert data["ratings"][pid_str]["average_score"] == 6.0

    def test_batch_ratings_nonexistent_ids(self, client: TestClient):
        resp = client.post(
            "/v1/photos/ratings",
            json={"photo_ids": [999999998, 999999999]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["ratings"]["999999998"]["vote_count"] == 0
        assert data["ratings"]["999999999"]["vote_count"] == 0
