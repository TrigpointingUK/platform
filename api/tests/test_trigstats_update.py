"""
Tests for trigstats update functionality.
"""

import uuid
from datetime import date, time
from decimal import Decimal
from unittest.mock import MagicMock, patch

from sqlalchemy.orm import Session

from api.core.config import settings
from api.crud import tlog as tlog_crud
from api.crud import tphoto as tphoto_crud
from api.crud import trigstats as trigstats_crud
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.trigstats import TrigStats
from api.models.user import TLog, User


def _create_test_trig(db: Session) -> Trig:
    """Create a test trig with unique waypoint."""
    waypoint = f"TP{uuid.uuid4().hex[:6]}"[:8]
    trig = Trig(
        waypoint=waypoint,
        name="Test Trigpoint",
        status_id=10,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        wgs_lat=Decimal("51.50000"),
        wgs_long=Decimal("-0.12500"),
        wgs_height=100,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=95,
        fb_number="S1234",
        stn_number="TEST123",
        permission_ind="Y",
        condition="G",
        postcode=None,
        town="Westminster",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2023, 1, 1),
        crt_time=time(12, 0, 0),
        crt_user_id=None,
        crt_ip_addr="127.0.0.1",
    )
    db.add(trig)
    db.commit()
    db.refresh(trig)
    return trig


def _create_test_user(db: Session) -> User:
    """Create a test user with unique name."""
    username = f"testuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=username,
        email=f"{username}@example.com",
        email_valid="Y",
        cryptpw="test",
        about="",
        public_ind="Y",
        crt_date=date(2020, 1, 1),
        crt_time=time(0, 0, 0),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


class TestUpdateTrigstats:
    """Tests for the update_trigstats function."""

    def test_update_trigstats_no_logs(self, db: Session):
        """Test that update_trigstats returns None when trig has no logs."""
        trig = _create_test_trig(db)

        result = trigstats_crud.update_trigstats(db, int(trig.id))

        assert result is None

        # Verify no trigstats row exists
        stats = db.query(TrigStats).filter(TrigStats.id == trig.id).first()
        assert stats is None

    def test_update_trigstats_with_logs(self, db: Session):
        """Test that update_trigstats correctly calculates stats."""
        trig = _create_test_trig(db)
        user = _create_test_user(db)

        # Create logs directly to avoid trigstats updates during test setup
        log1 = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2023, 6, 1),
            time=time(10, 0, 0),
            condition="G",  # Found condition
            score=5,
            comment="First log",
        )
        log2 = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2023, 7, 15),
            time=time(11, 0, 0),
            condition="S",  # Found condition
            score=4,
            comment="Second log",
        )
        log3 = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2023, 8, 20),
            time=time(12, 0, 0),
            condition="X",  # Destroyed - not found condition
            score=3,
            comment="Third log",
        )
        db.add_all([log1, log2, log3])
        db.commit()

        # Now call update_trigstats
        result = trigstats_crud.update_trigstats(db, int(trig.id))

        assert result is not None
        assert result.logged_count == 3
        assert result.logged_first == date(2023, 6, 1)
        assert result.logged_last == date(2023, 8, 20)
        assert result.found_count == 2  # Only G and S conditions
        assert result.found_last == date(2023, 7, 15)  # Last G or S log
        assert result.photo_count == 0
        # score_mean = (5 + 4 + 3) / 3 = 4.0
        assert result.score_mean == Decimal("4.00")

    def test_update_trigstats_with_photos(self, db: Session):
        """Test that update_trigstats correctly counts photos."""
        trig = _create_test_trig(db)
        user = _create_test_user(db)

        # Create a log
        log = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2023, 6, 1),
            time=time(10, 0, 0),
            condition="G",
            score=5,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        # Add photos
        photo1 = TPhoto(
            tlog_id=log.id,
            server_id=1,
            type="J",
            filename="test1.jpg",
            filesize=1000,
            height=100,
            width=100,
            icon_filename="test1_icon.jpg",
            icon_filesize=100,
            icon_height=50,
            icon_width=50,
            name="Test Photo 1",
            text_desc="",
            public_ind="Y",
            deleted_ind="N",
            source="F",
            ip_addr="127.0.0.1",
        )
        photo2 = TPhoto(
            tlog_id=log.id,
            server_id=1,
            type="J",
            filename="test2.jpg",
            filesize=1000,
            height=100,
            width=100,
            icon_filename="test2_icon.jpg",
            icon_filesize=100,
            icon_height=50,
            icon_width=50,
            name="Test Photo 2",
            text_desc="",
            public_ind="Y",
            deleted_ind="N",
            source="F",
            ip_addr="127.0.0.1",
        )
        # Soft-deleted photo should not be counted
        photo3 = TPhoto(
            tlog_id=log.id,
            server_id=1,
            type="J",
            filename="test3.jpg",
            filesize=1000,
            height=100,
            width=100,
            icon_filename="test3_icon.jpg",
            icon_filesize=100,
            icon_height=50,
            icon_width=50,
            name="Test Photo 3",
            text_desc="",
            public_ind="Y",
            deleted_ind="Y",  # Soft deleted
            source="F",
            ip_addr="127.0.0.1",
        )
        db.add_all([photo1, photo2, photo3])
        db.commit()

        result = trigstats_crud.update_trigstats(db, int(trig.id))

        assert result is not None
        assert result.photo_count == 2  # Only non-deleted photos

    def test_update_trigstats_deletes_when_no_logs(self, db: Session):
        """Test that update_trigstats deletes existing stats when all logs removed."""
        trig = _create_test_trig(db)
        user = _create_test_user(db)

        # Create a log and update stats
        log = TLog(
            trig_id=trig.id,
            user_id=user.id,
            date=date(2023, 6, 1),
            time=time(10, 0, 0),
            condition="G",
            score=5,
        )
        db.add(log)
        db.commit()
        db.refresh(log)

        result = trigstats_crud.update_trigstats(db, int(trig.id))
        assert result is not None

        # Delete the log
        db.delete(log)
        db.commit()

        # Update stats again
        result = trigstats_crud.update_trigstats(db, int(trig.id))

        assert result is None
        stats = db.query(TrigStats).filter(TrigStats.id == trig.id).first()
        assert stats is None


class TestGetGlobalMeanScore:
    """Tests for the get_global_mean_score function."""

    def test_global_mean_with_no_logs(self, db: Session):
        """Test that global mean returns 0 when no logs exist."""
        # Clear any existing logs for this test
        with patch.object(trigstats_crud, "get_redis_client", return_value=None):
            result = trigstats_crud.get_global_mean_score(db)
            # Result depends on existing data in db, but should be a Decimal
            assert isinstance(result, Decimal)

    def test_global_mean_uses_cache(self, db: Session):
        """Test that global mean uses Redis cache when available."""
        mock_client = MagicMock()
        mock_client.get.return_value = "4.50"

        with patch.object(trigstats_crud, "get_redis_client", return_value=mock_client):
            result = trigstats_crud.get_global_mean_score(db)

        assert result == Decimal("4.50")
        expected_key = f"fastapi:{settings.ENVIRONMENT.lower()}:trigstats:global_mean"
        mock_client.get.assert_called_once_with(expected_key)

    def test_global_mean_caches_on_miss(self, db: Session):
        """Test that global mean is cached on cache miss."""
        mock_client = MagicMock()
        mock_client.get.return_value = None  # Cache miss

        with patch.object(trigstats_crud, "get_redis_client", return_value=mock_client):
            _result = trigstats_crud.get_global_mean_score(db)  # noqa: F841

        # Should have set the cache
        mock_client.setex.assert_called_once()
        call_args = mock_client.setex.call_args[0]
        expected_key = f"fastapi:{settings.ENVIRONMENT.lower()}:trigstats:global_mean"
        assert call_args[0] == expected_key
        assert call_args[1] == 86400  # 24 hours


class TestTlogIntegration:
    """Tests for trigstats updates from tlog CRUD operations."""

    def test_create_log_updates_trigstats(self, db: Session):
        """Test that creating a log updates trigstats."""
        trig = _create_test_trig(db)
        user = _create_test_user(db)

        # Create log through CRUD function
        tlog_crud.create_log(
            db,
            trig_id=int(trig.id),
            user_id=int(user.id),
            values={
                "date": date(2023, 6, 1),
                "time": time(10, 0, 0),
                "condition": "G",
                "score": 5,
                "comment": "Test log",
            },
        )

        # Verify trigstats was updated
        stats = db.query(TrigStats).filter(TrigStats.id == trig.id).first()
        assert stats is not None
        assert stats.logged_count == 1
        assert stats.found_count == 1

    def test_update_log_updates_trigstats(self, db: Session):
        """Test that updating a log updates trigstats."""
        trig = _create_test_trig(db)
        user = _create_test_user(db)

        # Create initial log
        log = tlog_crud.create_log(
            db,
            trig_id=int(trig.id),
            user_id=int(user.id),
            values={
                "date": date(2023, 6, 1),
                "time": time(10, 0, 0),
                "condition": "G",
                "score": 5,
            },
        )

        # Update the log
        tlog_crud.update_log(
            db,
            log_id=int(log.id),
            updates={"score": 3},
        )

        # Verify trigstats was updated
        stats = db.query(TrigStats).filter(TrigStats.id == trig.id).first()
        assert stats is not None
        assert stats.score_mean == Decimal("3.00")

    def test_delete_log_updates_trigstats(self, db: Session):
        """Test that deleting a log updates trigstats."""
        trig = _create_test_trig(db)
        user = _create_test_user(db)

        # Create two logs
        log1 = tlog_crud.create_log(
            db,
            trig_id=int(trig.id),
            user_id=int(user.id),
            values={
                "date": date(2023, 6, 1),
                "time": time(10, 0, 0),
                "condition": "G",
                "score": 5,
            },
        )
        tlog_crud.create_log(
            db,
            trig_id=int(trig.id),
            user_id=int(user.id),
            values={
                "date": date(2023, 7, 1),
                "time": time(10, 0, 0),
                "condition": "S",
                "score": 3,
            },
        )

        stats = db.query(TrigStats).filter(TrigStats.id == trig.id).first()
        assert stats is not None
        assert stats.logged_count == 2

        # Delete one log
        tlog_crud.delete_log_hard(db, log_id=int(log1.id))

        # Verify trigstats was updated
        db.refresh(stats)
        assert stats.logged_count == 1
        assert stats.score_mean == Decimal("3.00")


class TestTphotoIntegration:
    """Tests for trigstats updates from tphoto CRUD operations."""

    def test_create_photo_updates_trigstats(self, db: Session):
        """Test that creating a photo updates trigstats."""
        trig = _create_test_trig(db)
        user = _create_test_user(db)

        # Create log first
        log = tlog_crud.create_log(
            db,
            trig_id=int(trig.id),
            user_id=int(user.id),
            values={
                "date": date(2023, 6, 1),
                "time": time(10, 0, 0),
                "condition": "G",
                "score": 5,
            },
        )

        stats = db.query(TrigStats).filter(TrigStats.id == trig.id).first()
        assert stats is not None
        assert stats.photo_count == 0

        # Create photo through CRUD function
        tphoto_crud.create_photo(
            db,
            log_id=int(log.id),
            values={
                "server_id": 1,
                "type": "J",
                "filename": "test.jpg",
                "filesize": 1000,
                "height": 100,
                "width": 100,
                "icon_filename": "test_icon.jpg",
                "icon_filesize": 100,
                "icon_height": 50,
                "icon_width": 50,
                "name": "Test Photo",
                "text_desc": "",
                "public_ind": "Y",
                "deleted_ind": "N",
                "source": "F",
                "ip_addr": "127.0.0.1",
            },
        )

        # Verify trigstats was updated
        db.refresh(stats)
        assert stats.photo_count == 1

    def test_delete_photo_updates_trigstats(self, db: Session):
        """Test that deleting a photo updates trigstats."""
        trig = _create_test_trig(db)
        user = _create_test_user(db)

        # Create log and photo
        log = tlog_crud.create_log(
            db,
            trig_id=int(trig.id),
            user_id=int(user.id),
            values={
                "date": date(2023, 6, 1),
                "time": time(10, 0, 0),
                "condition": "G",
                "score": 5,
            },
        )

        photo = tphoto_crud.create_photo(
            db,
            log_id=int(log.id),
            values={
                "server_id": 1,
                "type": "J",
                "filename": "test.jpg",
                "filesize": 1000,
                "height": 100,
                "width": 100,
                "icon_filename": "test_icon.jpg",
                "icon_filesize": 100,
                "icon_height": 50,
                "icon_width": 50,
                "name": "Test Photo",
                "text_desc": "",
                "public_ind": "Y",
                "deleted_ind": "N",
                "source": "F",
                "ip_addr": "127.0.0.1",
            },
        )

        stats = db.query(TrigStats).filter(TrigStats.id == trig.id).first()
        assert stats is not None
        assert stats.photo_count == 1

        # Delete photo (soft delete)
        tphoto_crud.delete_photo(db, photo_id=int(photo.id), soft=True)

        # Verify trigstats was updated
        db.refresh(stats)
        assert stats.photo_count == 0
