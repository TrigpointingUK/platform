"""
Tests for the archive service (zip generation).
"""

import json
import zipfile
from datetime import date, time
from io import BytesIO

from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.user import TLog, User
from api.services.archive_service import generate_archive_zip


def _make_user(db, **overrides):
    """Helper to create a user with defaults."""
    from passlib.hash import des_crypt

    user = User(
        name=overrides.get("name", "archiveuser"),
        firstname="Archive",
        surname="User",
        email=overrides.get("email", "archive@example.com"),
        cryptpw=des_crypt.hash("testpassword"),
        email_valid="Y",
        public_ind="Y",
        archive_frequency="N",
        archive_format="C",
    )
    for k, v in overrides.items():
        setattr(user, k, v)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _make_trig(db, user, **overrides):
    """Helper to create a trig."""
    trig = Trig(
        waypoint=overrides.get("waypoint", "TP0001"),
        name=overrides.get("name", "Test Trig"),
        fb_number="",
        stn_number="",
        status_id=1,
        user_added=0,
        current_use="Passive station",
        historic_use="Primary",
        condition="G",
        wgs_lat=51.5,
        wgs_long=-0.1,
        osgb_eastings=530000,
        osgb_northings=180000,
        osgb_gridref="TQ 30000 80000",
        osgb_height=100,
        town="London",
        permission_ind="Y",
        needs_attention=0,
        attention_comment="",
        crt_date=date(2020, 1, 1),
        crt_time=time(0, 0, 0),
        crt_user_id=user.id,
        crt_ip_addr="127.0.0.1",
    )
    for k, v in overrides.items():
        setattr(trig, k, v)
    db.add(trig)
    db.commit()
    db.refresh(trig)
    return trig


def _make_log(db, user, trig, **overrides):
    """Helper to create a published log."""
    log = TLog(
        trig_id=trig.id,
        user_id=user.id,
        date=overrides.get("date", date(2024, 6, 15)),
        time=overrides.get("time", time(14, 30)),
        condition=overrides.get("condition", "G"),
        comment=overrides.get("comment", "Test log"),
        score=overrides.get("score", 7),
        ip_addr="127.0.0.1",
        source="W",
        status=overrides.get("status", "P"),
    )
    for k, v in overrides.items():
        if hasattr(log, k):
            setattr(log, k, v)
    db.add(log)
    db.commit()
    db.refresh(log)
    return log


class TestGenerateArchiveZip:
    """Tests for generate_archive_zip."""

    def test_csv_only_format(self, db):
        user = _make_user(db)
        trig = _make_trig(db, user)
        _make_log(db, user, trig, comment="Found the trig!")

        zip_bytes = generate_archive_zip(db, user, archive_format="C")

        assert len(zip_bytes) > 0
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert any("logs.csv" in n for n in names)
            assert any("README.txt" in n for n in names)
            assert not any("logs.json" in n for n in names)

            csv_name = [n for n in names if "logs.csv" in n][0]
            csv_content = zf.read(csv_name).decode("utf-8")
            assert "Found the trig!" in csv_content
            assert "log_id" in csv_content

    def test_csv_json_format(self, db):
        user = _make_user(db, name="jsonuser")
        trig = _make_trig(db, user, waypoint="TP0002", name="JSON Trig")
        _make_log(db, user, trig, comment="JSON test log")

        zip_bytes = generate_archive_zip(db, user, archive_format="J")

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            names = zf.namelist()
            assert any("logs.csv" in n for n in names)
            assert any("logs.json" in n for n in names)
            assert any("README.txt" in n for n in names)

            json_name = [n for n in names if "logs.json" in n][0]
            json_content = json.loads(zf.read(json_name))
            assert json_content["user"]["username"] == "jsonuser"
            assert json_content["log_count"] == 1
            assert len(json_content["logs"]) == 1
            assert json_content["logs"][0]["comment"] == "JSON test log"

    def test_excludes_drafts(self, db):
        user = _make_user(db, name="draftuser")
        trig = _make_trig(db, user, waypoint="TP0003")
        _make_log(db, user, trig, comment="Published log", status="P")
        _make_log(db, user, trig, comment="Draft log", status="D")

        zip_bytes = generate_archive_zip(db, user, archive_format="C")

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            csv_name = [n for n in zf.namelist() if "logs.csv" in n][0]
            csv_content = zf.read(csv_name).decode("utf-8")
            assert "Published log" in csv_content
            assert "Draft log" not in csv_content

    def test_empty_logs(self, db):
        user = _make_user(db, name="emptyuser")

        zip_bytes = generate_archive_zip(db, user, archive_format="C")

        assert len(zip_bytes) > 0
        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            csv_name = [n for n in zf.namelist() if "logs.csv" in n][0]
            csv_content = zf.read(csv_name).decode("utf-8")
            lines = csv_content.strip().split("\n")
            assert len(lines) == 1  # Header only

    def test_readme_contents(self, db):
        user = _make_user(db, name="readmeuser")
        trig = _make_trig(db, user, waypoint="TP0004")
        _make_log(db, user, trig)

        zip_bytes = generate_archive_zip(db, user, archive_format="J")

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            readme_name = [n for n in zf.namelist() if "README.txt" in n][0]
            readme = zf.read(readme_name).decode("utf-8")
            assert "readmeuser" in readme
            assert "Published logs: 1" in readme
            assert "logs.json" in readme

    def test_photo_metadata_in_json(self, db):
        user = _make_user(db, name="photouser")
        trig = _make_trig(db, user, waypoint="TP0005")
        log = _make_log(db, user, trig)

        photo = TPhoto(
            tlog_id=log.id,
            server_id=1,
            type="T",
            filename="000/P00001.jpg",
            filesize=12345,
            height=600,
            width=800,
            icon_filename="000/I00001.jpg",
            icon_filesize=1234,
            icon_height=120,
            icon_width=120,
            name="Test Photo",
            text_desc="A test photo",
            ip_addr="127.0.0.1",
            public_ind="Y",
            deleted_ind="N",
            source="W",
        )
        db.add(photo)
        db.commit()

        zip_bytes = generate_archive_zip(db, user, archive_format="J")

        with zipfile.ZipFile(BytesIO(zip_bytes)) as zf:
            json_name = [n for n in zf.namelist() if "logs.json" in n][0]
            json_content = json.loads(zf.read(json_name))
            log_entry = json_content["logs"][0]
            assert len(log_entry["photos"]) == 1
            assert log_entry["photos"][0]["name"] == "Test Photo"
            assert "P00001.jpg" in log_entry["photos"][0]["photo_url"]
