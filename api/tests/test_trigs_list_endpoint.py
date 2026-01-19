"""
Tests for /v1/trigs endpoint with categories parameter and type information.

Tests the categories filtering, type info in response, and authenticated
exclude_found/only_found filters.
"""

from datetime import date, time
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from api.core.config import settings
from api.models.trig import Trig
from api.models.trig_type import TrigCategory, TrigType
from api.models.user import TLog, User


@pytest.fixture
def seed_categories_types_trigs(db: Session):
    """Seed complete test data with categories, types, and trigs.

    Creates:
    - 2 categories (PILLAR_TEST, FBM_TEST)
    - 2 types per category
    - 2 trigs per type
    """
    import uuid

    base_tag = uuid.uuid4().hex[:8].upper()
    short_tag = base_tag[:6]
    base_sort = int(base_tag[:4], 16) % 20000 + 1000

    # Create categories
    pillar_category = TrigCategory(
        code=f"PILLAR_T{base_tag}",
        name="Test Pillar",
        description="Test pillar category",
        sort_order=base_sort,
    )
    fbm_category = TrigCategory(
        code=f"FBM_T{base_tag}",
        name="Test FBM",
        description="Test FBM category",
        sort_order=base_sort + 1,
    )
    db.add_all([pillar_category, fbm_category])
    db.flush()

    # Create types
    hotine_type = TrigType(
        category_id=pillar_category.id,
        code=f"HOTINE_T{base_tag}",
        name="Test Hotine",
        sort_order=1,
    )
    vanessa_type = TrigType(
        category_id=pillar_category.id,
        code=f"VANESSA_T{base_tag}",
        name="Test Vanessa",
        sort_order=2,
    )
    fbm_type = TrigType(
        category_id=fbm_category.id,
        code=f"FBM_MK_T{base_tag}",
        name="Test FBM Mark",
        sort_order=1,
    )
    db.add_all([hotine_type, vanessa_type, fbm_type])
    db.flush()

    # Create trigs with different types
    trigs = []
    for i, type_obj in enumerate([hotine_type, hotine_type, vanessa_type, fbm_type]):
        trig = Trig(
            waypoint=f"E{short_tag}{i}",
            name=f"Endpoint Test Trig {i}",
            fb_number=f"FB{short_tag}{i}",
            stn_number=f"STN{short_tag}{i}",
            status_id=10,
            user_added=0,
            type_id=type_obj.id,
            current_use="Passive station",
            historic_use="Primary",
            physical_type="Pillar" if "Pillar" in type_obj.name else "FBM",
            wgs_lat=Decimal("51.5") + Decimal(str(i * 0.01)),
            wgs_long=Decimal("-0.1"),
            wgs_height=100,
            osgb_eastings=530000 + i * 1000,
            osgb_northings=180000 + i * 1000,
            osgb_gridref=f"TQ {30000 + i * 1000} 80000",
            osgb_height=95,
            condition="G",
            county="London",
            town="Westminster",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2023, 1, 1),
            crt_time=time(12, 0, 0),
            crt_ip_addr="127.0.0.1",
        )
        trigs.append(trig)

    db.add_all(trigs)
    db.commit()

    try:
        yield {
            "pillar_category": pillar_category,
            "fbm_category": fbm_category,
            "hotine_type": hotine_type,
            "vanessa_type": vanessa_type,
            "fbm_type": fbm_type,
            "trigs": trigs,
            "base_id": base_tag,
        }
    finally:
        trig_ids = [t.id for t in trigs]
        type_ids = [hotine_type.id, vanessa_type.id, fbm_type.id]
        category_ids = [pillar_category.id, fbm_category.id]

        db.query(Trig).filter(Trig.id.in_(trig_ids)).delete(synchronize_session=False)
        db.query(TrigType).filter(TrigType.id.in_(type_ids)).delete(
            synchronize_session=False
        )
        db.query(TrigCategory).filter(TrigCategory.id.in_(category_ids)).delete(
            synchronize_session=False
        )
        db.commit()


class TestListTrigsWithCategoriesParam:
    """Tests for /v1/trigs?categories= parameter."""

    def test_categories_param_filters_results(
        self, client: TestClient, db: Session, seed_categories_types_trigs
    ):
        """?categories=PILLAR filters to only pillar trigs."""
        data = seed_categories_types_trigs
        pillar_code = data["pillar_category"].code

        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "categories": pillar_code,
                "lat": "51.5",
                "lon": "-0.1",
                "limit": 100,
            },
        )

        assert response.status_code == 200
        result = response.json()

        # Should return items
        assert "items" in result
        items = result["items"]

        # Filter to our seeded trigs
        seeded_ids = [t.id for t in data["trigs"]]
        our_items = [item for item in items if item["id"] in seeded_ids]

        # Should only include pillar trigs (hotine and vanessa types)
        pillar_type_ids = [data["hotine_type"].id, data["vanessa_type"].id]
        for item in our_items:
            trig = next(t for t in data["trigs"] if t.id == item["id"])
            assert trig.type_id in pillar_type_ids

    def test_multiple_categories_param(
        self, client: TestClient, db: Session, seed_categories_types_trigs
    ):
        """?categories=PILLAR,FBM returns trigs from both categories."""
        data = seed_categories_types_trigs
        codes = f"{data['pillar_category'].code},{data['fbm_category'].code}"

        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "categories": codes,
                "lat": "51.5",
                "lon": "-0.1",
                "limit": 100,
            },
        )

        assert response.status_code == 200
        result = response.json()

        # Filter to our seeded trigs
        seeded_ids = [t.id for t in data["trigs"]]
        our_items = [item for item in result["items"] if item["id"] in seeded_ids]

        # Should include all 4 seeded trigs
        assert len(our_items) == 4

    def test_invalid_category_returns_empty(
        self, client: TestClient, db: Session, seed_categories_types_trigs
    ):
        """Invalid category code returns empty results."""
        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "categories": "NONEXISTENT_CATEGORY_XYZ",
                "lat": "51.5",
                "lon": "-0.1",
                "limit": 100,
            },
        )

        assert response.status_code == 200
        result = response.json()

        # Should return empty items
        assert result["items"] == []
        assert result["pagination"]["total"] == 0


class TestListTrigsTypeInfoInResponse:
    """Tests for type info (category_code, category_name) in response."""

    def test_response_includes_category_code(
        self, client: TestClient, db: Session, seed_categories_types_trigs
    ):
        """Response includes category_code for each trig."""
        data = seed_categories_types_trigs
        pillar_code = data["pillar_category"].code

        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "categories": pillar_code,
                "lat": "51.5",
                "lon": "-0.1",
                "limit": 100,
            },
        )

        assert response.status_code == 200
        result = response.json()

        seeded_ids = [t.id for t in data["trigs"]]
        our_items = [item for item in result["items"] if item["id"] in seeded_ids]

        # Each item should have category_code
        for item in our_items:
            assert "category_code" in item
            assert item["category_code"] == pillar_code

    def test_response_includes_category_name(
        self, client: TestClient, db: Session, seed_categories_types_trigs
    ):
        """Response includes category_name for each trig."""
        data = seed_categories_types_trigs
        pillar_code = data["pillar_category"].code

        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "categories": pillar_code,
                "lat": "51.5",
                "lon": "-0.1",
                "limit": 100,
            },
        )

        assert response.status_code == 200
        result = response.json()

        seeded_ids = [t.id for t in data["trigs"]]
        our_items = [item for item in result["items"] if item["id"] in seeded_ids]

        # Each item should have category_name
        for item in our_items:
            assert "category_name" in item
            assert item["category_name"] == data["pillar_category"].name

    def test_response_includes_type_info(
        self, client: TestClient, db: Session, seed_categories_types_trigs
    ):
        """Response includes type_code and type_name for each trig."""
        data = seed_categories_types_trigs
        pillar_code = data["pillar_category"].code

        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "categories": pillar_code,
                "lat": "51.5",
                "lon": "-0.1",
                "limit": 100,
            },
        )

        assert response.status_code == 200
        result = response.json()

        seeded_ids = [t.id for t in data["trigs"]]
        our_items = [item for item in result["items"] if item["id"] in seeded_ids]

        # Each item should have type_code and type_name
        for item in our_items:
            assert "type_code" in item
            assert "type_name" in item
            assert item["type_code"] is not None
            assert item["type_name"] is not None


class TestListTrigsExcludeFoundAuthenticated:
    """Tests for exclude_found parameter with authentication."""

    @pytest.fixture
    def seed_user_with_log(self, db: Session, seed_categories_types_trigs):
        """Create user with a log entry for one trig."""
        data = seed_categories_types_trigs

        user = User(
            name=f"api_test_user_{data['base_id']}",
            email=f"apitest_{data['base_id']}@example.com",
            cryptpw="",
            email_valid="Y",
            public_ind="Y",
        )
        db.add(user)
        db.flush()
        # Set auth0_user_id after flush to get the user ID
        user.auth0_user_id = f"auth0|{user.id}"  # type: ignore[assignment]

        # Log the first trig
        logged_trig = data["trigs"][0]
        log = TLog(
            trig_id=logged_trig.id,
            user_id=user.id,
            date=date(2024, 1, 1),
            time=time(12, 0, 0),
            comment="Test log",
            condition="G",
            score=5,
        )
        db.add(log)
        db.commit()

        try:
            yield {
                **data,
                "user": user,
                "logged_trig": logged_trig,
                "unlogged_trigs": data["trigs"][1:],
            }
        finally:
            db.query(TLog).filter(TLog.user_id == user.id).delete(
                synchronize_session=False
            )
            db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
            db.commit()

    def test_exclude_found_requires_auth(
        self, client: TestClient, db: Session, seed_user_with_log
    ):
        """exclude_found without auth doesn't filter (no user to check)."""
        # Just need to ensure the fixture runs to seed data
        _ = seed_user_with_log

        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "lat": "51.5",
                "lon": "-0.1",
                "exclude_found": "true",
                "limit": 100,
            },
        )

        assert response.status_code == 200
        # Without auth, exclude_found has no effect (no user ID)

    def test_exclude_found_with_auth(
        self, client: TestClient, db: Session, seed_user_with_log
    ):
        """exclude_found with auth excludes user's logged trigs."""
        data = seed_user_with_log
        user = data["user"]
        pillar_category_code = data["pillar_category"].code

        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "lat": "51.5",
                "lon": "-0.1",
                "exclude_found": "true",
                "categories": pillar_category_code,  # Filter to our test category
                "limit": 100,
            },
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        result = response.json()

        # Get IDs from response
        item_ids = [item["id"] for item in result["items"]]

        # Logged trig should NOT be in results
        assert data["logged_trig"].id not in item_ids

        # At least some of the unlogged trigs should be in results
        unlogged_ids = [t.id for t in data["unlogged_trigs"]]
        found_unlogged = [tid for tid in unlogged_ids if tid in item_ids]
        assert len(found_unlogged) > 0, "No unlogged trigs found in filtered results"


class TestListTrigsOnlyFoundAuthenticated:
    """Tests for only_found parameter with authentication."""

    @pytest.fixture
    def seed_user_with_multiple_logs(self, db: Session, seed_categories_types_trigs):
        """Create user with logs for some trigs."""
        data = seed_categories_types_trigs

        user = User(
            name=f"only_test_user_{data['base_id']}",
            email=f"onlytest_{data['base_id']}@example.com",
            cryptpw="",
            email_valid="Y",
            public_ind="Y",
        )
        db.add(user)
        db.flush()
        # Set auth0_user_id after flush to get the user ID
        user.auth0_user_id = f"auth0|{user.id}"  # type: ignore[assignment]

        # Log first 2 trigs
        logged_trigs = data["trigs"][:2]
        for i, trig in enumerate(logged_trigs):
            log = TLog(
                trig_id=trig.id,
                user_id=user.id,
                date=date(2024, 1, i + 1),
                time=time(12, 0, 0),
                comment=f"Test log {i}",
                condition="G",
                score=5,
            )
            db.add(log)

        db.commit()

        try:
            yield {
                **data,
                "user": user,
                "logged_trigs": logged_trigs,
                "unlogged_trigs": data["trigs"][2:],
            }
        finally:
            db.query(TLog).filter(TLog.user_id == user.id).delete(
                synchronize_session=False
            )
            db.query(User).filter(User.id == user.id).delete(synchronize_session=False)
            db.commit()

    def test_only_found_with_auth(
        self, client: TestClient, db: Session, seed_user_with_multiple_logs
    ):
        """only_found with auth returns only user's logged trigs."""
        data = seed_user_with_multiple_logs
        user = data["user"]

        response = client.get(
            f"{settings.API_V1_STR}/trigs",
            params={
                "lat": "51.5",
                "lon": "-0.1",
                "only_found": "true",
                "limit": 100,
            },
            headers={"Authorization": f"Bearer auth0_user_{user.id}"},
        )

        assert response.status_code == 200
        result = response.json()

        # Check our seeded trigs
        seeded_ids = [t.id for t in data["trigs"]]
        our_items = [item for item in result["items"] if item["id"] in seeded_ids]
        our_item_ids = [item["id"] for item in our_items]

        # Logged trigs should be in results
        for trig in data["logged_trigs"]:
            assert trig.id in our_item_ids

        # Unlogged trigs should NOT be in results
        for trig in data["unlogged_trigs"]:
            assert trig.id not in our_item_ids
