"""
Comprehensive tests for enhanced user statistics functionality.
"""

from datetime import date, time

import pytest

from api.models.trig import Trig
from api.models.user import TLog, User
from api.utils.condition_mapping import (
    get_condition_counts_by_description,
    get_condition_description,
)


class TestConditionMapping:
    """Test condition code to description mapping."""

    def test_get_condition_description(self):
        """Test individual condition code mappings."""
        assert get_condition_description("G") == "Good"
        assert get_condition_description("N") == "Couldn't find it"
        assert get_condition_description("S") == "Slightly damaged"
        assert get_condition_description("X") == "Destroyed"
        assert get_condition_description("Z") == "Not Logged"
        assert get_condition_description("INVALID") == "Unknown"
        assert get_condition_description("") == "Unknown"

    def test_get_condition_counts_by_description(self):
        """Test conversion of condition code counts to description counts."""
        condition_counts = {"G": 10, "S": 5, "N": 3, "X": 1}

        expected = {
            "Good": 10,
            "Slightly damaged": 5,
            "Couldn't find it": 3,
            "Destroyed": 1,
        }

        result = get_condition_counts_by_description(condition_counts)
        assert result == expected

    def test_get_condition_counts_with_duplicate_descriptions(self):
        """Test handling of multiple codes mapping to same description."""
        # This test ensures robustness when codes map to same description
        condition_counts = {
            "G": 10,
            "g": 5,  # lowercase - should be combined with uppercase
        }

        result = get_condition_counts_by_description(condition_counts)
        # Should have combined count since function uses .upper()
        assert "Good" in result
        assert result["Good"] == 15  # 10 + 5 combined


class TestUserStatsIntegration:
    """Integration tests for user stats calculation."""

    def test_user_stats_schema_fields(self):
        """Test that UserStats schema has basic fields only."""
        from api.schemas.user import UserStats

        stats = UserStats(total_logs=100, total_trigs_logged=50, total_photos=25)

        assert stats.total_logs == 100
        assert stats.total_trigs_logged == 50
        assert stats.total_photos == 25

    def test_user_breakdown_schema_fields(self):
        """Test that UserBreakdown schema has all breakdown fields."""
        from api.schemas.user import UserBreakdown

        breakdown = UserBreakdown(
            by_current_use={"Passive station": 30, "Active station": 20},
            by_historic_use={"Primary": 25, "Secondary": 25},
            by_physical_type={"Pillar": 40, "Bolt": 10},
            by_condition={"Good": 80, "Damaged": 20},
        )

        assert breakdown.by_current_use == {"Passive station": 30, "Active station": 20}
        assert breakdown.by_historic_use == {"Primary": 25, "Secondary": 25}
        assert breakdown.by_physical_type == {"Pillar": 40, "Bolt": 10}
        assert breakdown.by_condition == {"Good": 80, "Damaged": 20}

    def test_user_response_with_member_since(self):
        """Test that UserResponse includes member_since field."""
        from api.schemas.user import UserResponse

        user_data = {
            "id": 1,
            "name": "testuser",
            "firstname": "Test",
            "surname": "User",
            "homepage": "http://example.com",
            "about": "Test user",
            "member_since": date(2020, 1, 1),
        }

        response = UserResponse(**user_data)
        assert response.member_since == date(2020, 1, 1)


class TestUserEndpointStats:
    """Test user endpoint statistics functionality."""

    def create_test_data(self, db, user_id=None):
        """Create test data for user stats testing."""
        import uuid

        # Create test user
        unique_name = f"testuser_{uuid.uuid4().hex[:6]}"
        user = User(
            name=unique_name,
            firstname="Test",
            surname="User",
            email=f"{unique_name}@example.com",
            cryptpw="test",
            about="Test user",
            email_valid="Y",
            public_ind="Y",
            homepage="http://example.com",
            crt_date=date(2020, 1, 1),
            crt_time=time(12, 0, 0),
        )
        db.add(user)
        db.commit()
        db.refresh(user)

        # Create test trigpoints
        waypoint1 = f"TP{uuid.uuid4().hex[:6]}"[:8]
        trig1 = Trig(
            waypoint=waypoint1,
            name="Test Trig 1",
            current_use="Passive station",
            historic_use="Primary",
            physical_type="Pillar",
            condition="G",
            wgs_lat=51.0,
            wgs_long=-1.0,
            wgs_height=100,
            osgb_eastings=400000,
            osgb_northings=100000,
            osgb_gridref="SU 00000 00000",
            osgb_height=100,
            fb_number="123",
            stn_number="TEST001",
            status_id=1,
            user_added=0,
            postcode="RG1 1A",
            county="Berkshire",
            town="Reading",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2020, 1, 1),
            crt_time=time(12, 0, 0),
            crt_user_id=1,
            crt_ip_addr="127.0.0.1",
        )

        waypoint2 = f"TP{uuid.uuid4().hex[:6]}"[:8]
        trig2 = Trig(
            waypoint=waypoint2,
            name="Test Trig 2",
            current_use="Active station",
            historic_use="Secondary",
            physical_type="Bolt",
            condition="S",
            wgs_lat=51.1,
            wgs_long=-1.1,
            wgs_height=150,
            osgb_eastings=401000,
            osgb_northings=101000,
            osgb_gridref="SU 01000 01000",
            osgb_height=150,
            fb_number="124",
            stn_number="TEST002",
            status_id=1,
            user_added=0,
            postcode="RG1 1B",
            county="Berkshire",
            town="Reading",
            permission_ind="Y",
            needs_attention=0,
            attention_comment="",
            crt_date=date(2020, 1, 1),
            crt_time=time(12, 0, 0),
            crt_user_id=1,
            crt_ip_addr="127.0.0.1",
        )

        db.add_all([trig1, trig2])
        db.commit()
        db.refresh(trig1)
        db.refresh(trig2)

        # Create test logs
        log1 = TLog(
            trig_id=trig1.id,
            user_id=user.id,
            date=date(2020, 6, 1),
            time=time(10, 0, 0),
            osgb_eastings=400000,
            osgb_northings=100000,
            osgb_gridref="SU 00000 00000",
            fb_number="123",
            condition="G",
            comment="Good condition",
            score=8,
            ip_addr="127.0.0.1",
            source="W",
        )

        log2 = TLog(
            trig_id=trig1.id,  # Same trig, different log
            user_id=user.id,
            date=date(2020, 7, 1),
            time=time(11, 0, 0),
            osgb_eastings=400000,
            osgb_northings=100000,
            osgb_gridref="SU 00000 00000",
            fb_number="123",
            condition="S",  # Different condition
            comment="Slightly damaged now",
            score=7,
            ip_addr="127.0.0.1",
            source="W",
        )

        log3 = TLog(
            trig_id=trig2.id,  # Different trig
            user_id=user.id,
            date=date(2020, 8, 1),
            time=time(12, 0, 0),
            osgb_eastings=401000,
            osgb_northings=101000,
            osgb_gridref="SU 01000 01000",
            fb_number="124",
            condition="N",
            comment="Couldn't find it",
            score=0,
            ip_addr="127.0.0.1",
            source="W",
        )

        db.add_all([log1, log2, log3])
        db.commit()
        db.refresh(log1)
        db.refresh(log2)
        db.refresh(log3)

        return user, [trig1, trig2], [log1, log2, log3]

    @pytest.fixture
    def test_data(self, db):
        """Provide test data for user stats tests."""
        return self.create_test_data(db)

    def test_user_stats_calculations_manual(self, db):
        """Test manual calculation of user stats to verify expected behaviour."""
        user, trigs, logs = self.create_test_data(db)

        # Expected results based on test data:
        # - total_logs: 3 (all logs)
        # - total_trigs_logged: 2 (distinct trig_ids: 1, 2)
        # - by_current_use: {'Passive station': 1, 'Active station': 1} (distinct trigs)
        # - by_historic_use: {'Primary': 1, 'Secondary': 1} (distinct trigs)
        # - by_physical_type: {'Pillar': 1, 'Bolt': 1} (distinct trigs)
        # - by_condition: {'Good': 1, 'Slightly damaged': 1, "Couldn't find it": 1} (all logs)

        from sqlalchemy import func

        from api.models.trig import Trig
        from api.models.user import TLog
        from api.utils.condition_mapping import get_condition_counts_by_description

        user_id = user.id

        # Calculate basic stats
        total_logs = db.query(TLog).filter(TLog.user_id == user_id).count()
        total_trigs = (
            db.query(TLog.trig_id).filter(TLog.user_id == user_id).distinct().count()
        )

        assert total_logs == 3
        assert total_trigs == 2

        # Calculate breakdowns
        by_current_use = dict(
            db.query(Trig.current_use, func.count(func.distinct(TLog.trig_id)))
            .join(TLog, TLog.trig_id == Trig.id)
            .filter(TLog.user_id == user_id)
            .group_by(Trig.current_use)
            .all()
        )

        expected_current_use = {"Passive station": 1, "Active station": 1}
        assert by_current_use == expected_current_use

        # Test condition breakdown
        condition_counts = dict(
            db.query(TLog.condition, func.count(TLog.id))
            .filter(TLog.user_id == user_id)
            .group_by(TLog.condition)
            .all()
        )
        by_condition = get_condition_counts_by_description(condition_counts)

        expected_condition = {"Good": 1, "Slightly damaged": 1, "Couldn't find it": 1}
        assert by_condition == expected_condition
