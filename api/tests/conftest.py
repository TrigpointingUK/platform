"""
Test configuration and fixtures.
"""

import warnings

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

# from api.core.security import get_password_hash  # No longer needed - using Unix crypt
from api.db.database import Base, get_db
from api.db.user_activity_summary_view import (
    CREATE_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS,
    DROP_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS,
)
from api.main import app
from api.models.status import Status
from api.models.trig import Trig
from api.models.user import TLog, User

# Legacy JWT tokens removed - Auth0 only


# Filter out deprecation warnings that are not actionable
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.*")
warnings.filterwarnings(
    "ignore", category=PendingDeprecationWarning, module="starlette.*"
)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib.*")


def get_test_database_url():
    """Get PostgreSQL database URL for testing."""
    import os

    # Use environment variable if set (for CI), otherwise use default test DB
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        return db_url

    # Default local PostgreSQL for tests - use single database with schema isolation
    # PostgreSQL handles parallel access better than separate databases
    # Use TEST_DB_PORT env var or default to 5434 for local dev (avoids conflict with system PostgreSQL on 5432 and staging tunnel on 5433)
    port = os.environ.get("TEST_DB_PORT", "5434")
    return f"postgresql+psycopg2://test_user:test_password@localhost:{port}/test_db"


def setup_test_database():
    """Create test database and schema if needed."""
    import os

    from sqlalchemy import create_engine

    # Only run setup for parallel workers or when DATABASE_URL not set
    db_url = os.environ.get("DATABASE_URL")
    if db_url:
        # In CI, database already exists
        return

    # For local development, ensure test database exists
    # Use TEST_DB_PORT env var or default to 5434 for local dev
    port = os.environ.get("TEST_DB_PORT", "5434")
    admin_url = (
        f"postgresql+psycopg2://test_user:test_password@localhost:{port}/postgres"
    )
    try:
        admin_engine = create_engine(admin_url, isolation_level="AUTOCOMMIT")
        with admin_engine.connect() as conn:
            # Check if test_db exists
            result = conn.execute(
                text("SELECT 1 FROM pg_database WHERE datname='test_db'")
            )
            if not result.scalar():
                conn.execute(text("CREATE DATABASE test_db"))
        admin_engine.dispose()
    except Exception:
        # Database likely already exists or we don't have permissions
        # Tests will fail if it's a real issue
        pass


# Setup database before creating engine
setup_test_database()

# Test database URL
SQLALCHEMY_DATABASE_URL = get_test_database_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    """Override get_db dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


def _install_upd_timestamp_triggers(connection) -> None:
    """
    Install `upd_timestamp` triggers + defaults in the test database.

    Tests build the schema via Base.metadata.create_all(), so Alembic migrations
    (which create these triggers in real environments) are not applied here.
    """
    connection.execute(
        text(
            """
            CREATE OR REPLACE FUNCTION public.set_upd_timestamp_utc()
            RETURNS trigger
            LANGUAGE plpgsql
            AS $$
            BEGIN
                IF TG_OP = 'INSERT' THEN
                    IF NEW.upd_timestamp IS NULL THEN
                        NEW.upd_timestamp := timezone('utc', clock_timestamp());
                    END IF;
                    RETURN NEW;
                END IF;

                -- TG_OP = 'UPDATE'
                IF NEW.upd_timestamp IS DISTINCT FROM OLD.upd_timestamp THEN
                    RETURN NEW;
                END IF;

                NEW.upd_timestamp := timezone('utc', clock_timestamp());
                RETURN NEW;
            END;
            $$;
            """
        )
    )

    connection.execute(
        text(
            """
            DO $$
            DECLARE
                r RECORD;
            BEGIN
                FOR r IN
                    SELECT c.table_schema, c.table_name
                    FROM information_schema.columns c
                    JOIN information_schema.tables t
                      ON t.table_schema = c.table_schema
                     AND t.table_name = c.table_name
                    WHERE c.column_name = 'upd_timestamp'
                      AND c.table_schema = 'public'
                      AND t.table_type = 'BASE TABLE'
                LOOP
                    EXECUTE format(
                        'ALTER TABLE %I.%I ALTER COLUMN upd_timestamp SET DEFAULT (timezone(''utc'', clock_timestamp()))',
                        r.table_schema,
                        r.table_name
                    );

                    EXECUTE format(
                        'DROP TRIGGER IF EXISTS set_upd_timestamp_utc ON %I.%I',
                        r.table_schema,
                        r.table_name
                    );

                    EXECUTE format(
                        'CREATE TRIGGER set_upd_timestamp_utc '
                        'BEFORE INSERT OR UPDATE ON %I.%I '
                        'FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc()',
                        r.table_schema,
                        r.table_name
                    );
                END LOOP;
            END
            $$;
            """
        )
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_tables(request):
    """Create all tables once at the session start for each worker."""
    # Create tables (will only succeed for the first worker due to PostgreSQL's transactional DDL)
    try:
        # Drop and recreate postcodes table to ensure schema is up to date
        # (create_all doesn't add new columns to existing tables)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS postcodes CASCADE"))

        Base.metadata.create_all(bind=engine)
        with engine.begin() as connection:
            _install_upd_timestamp_triggers(connection)
            for statement in DROP_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS:
                connection.execute(text(statement))
            for statement in CREATE_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS:
                connection.execute(text(statement))
    except Exception:
        # Tables likely already exist from another worker
        pass

    # Seed minimal reference rows used by many tests (FK constraints are now enforced).
    try:
        with engine.begin() as connection:
            connection.execute(
                text(
                    """
                    INSERT INTO status (id, name, descr, limit_descr)
                    VALUES (1, 'ACTIVE', 'Active', 'Active')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO status (id, name, descr, limit_descr)
                    VALUES (0, 'UNKNOWN', 'Unknown', 'Unknown')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )
            connection.execute(
                text(
                    """
                    INSERT INTO status (id, name, descr, limit_descr)
                    VALUES (10, 'TEST', 'Test', 'Test')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )

            connection.execute(
                text(
                    """
                    INSERT INTO server (id, url, path, name)
                    VALUES
                        (1, 'https://example.invalid/1/', '/', 'Test Server 1'),
                        (3, 'https://example.invalid/3/', '/', 'Test Server 3'),
                        (999, 'https://example.invalid/999/', '/', 'Test Server 999')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )

            # Seed a couple of users with well-known IDs for tests that still use user_id=1/2.
            connection.execute(
                text(
                    """
                    INSERT INTO "user" (id, name, email, cryptpw, email_valid, public_ind)
                    VALUES
                        (1, 'seed_user_1', 'seed1@example.invalid', '', 'Y', 'Y'),
                        (2, 'seed_user_2', 'seed2@example.invalid', '', 'Y', 'Y')
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )
            # Ensure the sequence is at least MAX(id) so future inserts don't collide.
            connection.execute(
                text(
                    """
                    SELECT setval(
                        pg_get_serial_sequence('"user"', 'id'),
                        GREATEST((SELECT COALESCE(MAX(id), 1) FROM "user"), 1)
                    )
                    """
                )
            )

            connection.execute(
                text(
                    """
                    INSERT INTO trig (
                        id, waypoint, name, fb_number, stn_number,
                        status_id, user_added, current_use, historic_use,
                        physical_type, condition,
                        location, wgs_lat, wgs_long, wgs_height,
                        osgb_eastings, osgb_northings, osgb_gridref, osgb_height,
                        postcode, county, town,
                        permission_ind, needs_attention, attention_comment,
                        crt_date, crt_time, crt_user_id, crt_ip_addr
                    )
                    VALUES (
                        1, 'TP0001', 'Test Trig 1', 'FB1', 'STN1',
                        1, 0, 'Passive station', 'Primary',
                        'Pillar', 'G',
                        NULL, 0.0, 0.0, 0,
                        100000, 200000, 'TQ 00000 00000', 0,
                        NULL, 'Testshire', 'Testtown',
                        'Y', 0, '',
                        '2023-01-01', '00:00:00', NULL, '127.0.0.1'
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )

            connection.execute(
                text(
                    """
                    INSERT INTO trig (
                        id, waypoint, name, fb_number, stn_number,
                        status_id, user_added, current_use, historic_use,
                        physical_type, condition,
                        location, wgs_lat, wgs_long, wgs_height,
                        osgb_eastings, osgb_northings, osgb_gridref, osgb_height,
                        postcode, county, town,
                        permission_ind, needs_attention, attention_comment,
                        crt_date, crt_time, crt_user_id, crt_ip_addr
                    )
                    VALUES (
                        2, 'TP0002', 'Test Trig 2', 'FB2', 'STN2',
                        1, 0, 'Passive station', 'Primary',
                        'Pillar', 'G',
                        NULL, 0.0, 0.0, 0,
                        150000, 250000, 'TQ 50000 50000', 0,
                        NULL, 'Testshire', 'Testtown',
                        'Y', 0, '',
                        '2023-01-01', '00:00:00', NULL, '127.0.0.1'
                    )
                    ON CONFLICT (id) DO NOTHING
                    """
                )
            )

            # Ensure trig.id sequence is at least MAX(id) so inserts without explicit IDs
            # don't collide with the seeded rows (id=1, id=2).
            connection.execute(
                text(
                    """
                    DO $$
                    DECLARE
                        seq_name text;
                        next_val bigint;
                    BEGIN
                        seq_name := pg_get_serial_sequence('trig', 'id');
                        IF seq_name IS NOT NULL THEN
                            SELECT GREATEST(COALESCE(MAX(id), 1), 1) INTO next_val FROM trig;
                            EXECUTE format('SELECT setval(%L, %s)', seq_name, next_val);
                        END IF;
                    END $$;
                    """
                )
            )
    except Exception:
        # Best-effort seeding; tests can still create their own reference data.
        pass

    yield

    # Don't drop tables - let the test database cleanup handle it


@pytest.fixture(scope="function")
def db():
    """Create test database session.

    Note: Tests share the same database, so use unique IDs/names to avoid conflicts.
    The session-scoped setup creates tables once, and they persist across tests.
    """
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.rollback()  # Rollback any uncommitted changes
        session.close()


@pytest.fixture(scope="function")
def client(monkeypatch):
    """Create test client with token validator patched for Auth0 tokens only."""

    def _validate(token: str):
        # Auth0 test tokens only - no legacy tokens supported
        if token.startswith("auth0_user_"):
            try:
                user_id = int(token.split("_", 2)[2])
                return {"token_type": "auth0", "auth0_user_id": f"auth0|{user_id}"}
            except Exception:
                return None
        # Admin token
        if token == "auth0_admin":
            return {
                "token_type": "auth0",
                "auth0_user_id": "auth0|admin",
                "scope": "api:admin",
            }
        return None

    # Mock both token validation and Auth0 API calls
    monkeypatch.setattr(
        "api.core.security.auth0_validator.validate_auth0_token", _validate
    )

    # Mock the Auth0 service to prevent real API calls during tests
    def mock_find_user_by_auth0_id(auth0_user_id: str):
        # Return None to prevent Auth0 sync - we'll use existing database users
        return None

    monkeypatch.setattr(
        "api.services.auth0_service.auth0_service.find_user_by_auth0_id",
        mock_find_user_by_auth0_id,
    )

    # Also mock get_user_by_auth0_id to directly map auth0_user_id to database user_id
    def mock_get_user_by_auth0_id(db, auth0_user_id: str):
        # Prefer an explicit auth0_user_id mapping if present in the database
        from api.models.user import User as UserModel

        user = (
            db.query(UserModel).filter(UserModel.auth0_user_id == auth0_user_id).first()
        )
        if user:
            return user

        # Convenience mapping used by many tests: auth0|{user_id} -> user.id
        if auth0_user_id.startswith("auth0|"):
            try:
                user_id = int(auth0_user_id.split("|")[1])
            except ValueError:
                return None

            from api.crud.user import get_user_by_id

            return get_user_by_id(db, user_id=user_id)

        return None

    monkeypatch.setattr("api.crud.user.get_user_by_auth0_id", mock_get_user_by_auth0_id)
    # api.api.deps imports get_user_by_auth0_id at module import time, so patch it too.
    monkeypatch.setattr("api.api.deps.get_user_by_auth0_id", mock_get_user_by_auth0_id)

    with TestClient(app) as c:
        yield c


@pytest.fixture
def test_user(db):
    """Create a test user."""
    import uuid

    from passlib.hash import des_crypt

    # Create Unix crypt hash for testing
    test_password = "testpassword123"
    cryptpw = des_crypt.hash(test_password)

    unique_name = f"testuser_{uuid.uuid4().hex[:8]}"
    user = User(
        name=unique_name,
        firstname="Test",
        surname="User",
        email=f"{unique_name}@example.com",
        cryptpw=cryptpw,
        about="Test user for unit tests",
        email_valid="Y",
        public_ind="Y",
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@pytest.fixture
def test_tlog_entries(db, test_user):
    """Create test tlog entries."""
    from datetime import date, datetime, time

    # Ensure referenced rows exist (FK constraints are now enforced in tests).
    if db.query(Status).filter(Status.id == 1).first() is None:
        db.add(Status(id=1, name="ACTIVE", descr="Active", limit_descr="Active"))
        db.flush()

    def _ensure_trig(trig_id: int, waypoint: str, name: str, e: int, n: int, grid: str):
        if db.query(Trig).filter(Trig.id == trig_id).first() is not None:
            return

        db.add(
            Trig(
                id=trig_id,
                waypoint=waypoint,
                name=name,
                fb_number=f"FB{trig_id}",
                stn_number=f"STN{trig_id}",
                stn_number_active=None,
                stn_number_passive=None,
                stn_number_osgb36=None,
                status_id=1,
                user_added=0,
                current_use="Passive station",
                historic_use="Primary",
                physical_type="Pillar",
                condition="G",
                location=None,
                wgs_lat=0.0,
                wgs_long=0.0,
                wgs_height=0,
                osgb_eastings=e,
                osgb_northings=n,
                osgb_gridref=grid,
                osgb_height=0,
                postcode=None,
                county="Testshire",
                town="Testtown",
                permission_ind="Y",
                needs_attention=0,
                attention_comment="",
                crt_date=date(2023, 1, 1),
                crt_time=time(0, 0, 0),
                crt_user_id=test_user.id,
                crt_ip_addr="127.0.0.1",
                admin_user_id=None,
                admin_timestamp=None,
                admin_ip_addr=None,
                upd_timestamp=None,
            )
        )
        db.flush()

    _ensure_trig(1, "TP0001", "Test Trig 1", 100000, 200000, "TQ 00000 00000")
    _ensure_trig(2, "TP0002", "Test Trig 2", 150000, 250000, "TQ 50000 50000")

    entries = [
        TLog(
            trig_id=1,
            user_id=test_user.id,
            date=date(2023, 12, 15),
            time=time(14, 30, 0),
            osgb_eastings=100000,
            osgb_northings=200000,
            osgb_gridref="TQ 00000 00000",
            fb_number="",
            condition="G",
            comment="Test log entry 1",
            score=7,
            ip_addr="127.0.0.1",
            source="W",
            upd_timestamp=datetime(2023, 12, 15, 14, 30, 0),
        ),
        TLog(
            trig_id=1,
            user_id=test_user.id,
            date=date(2023, 12, 10),
            time=time(10, 15, 0),
            osgb_eastings=100000,
            osgb_northings=200000,
            osgb_gridref="TQ 00000 00000",
            fb_number="",
            condition="G",
            comment="Test log entry 2",
            score=8,
            ip_addr="127.0.0.1",
            source="W",
            upd_timestamp=datetime(2023, 12, 10, 10, 15, 0),
        ),
        TLog(
            trig_id=1,
            user_id=test_user.id,
            date=date(2023, 12, 5),
            time=time(16, 45, 0),
            osgb_eastings=100000,
            osgb_northings=200000,
            osgb_gridref="TQ 00000 00000",
            fb_number="",
            condition="G",
            comment="Test log entry 3",
            score=9,
            ip_addr="127.0.0.1",
            source="W",
            upd_timestamp=datetime(2023, 12, 5, 16, 45, 0),
        ),
        TLog(
            trig_id=2,
            user_id=None,
            date=date(2023, 11, 20),
            time=time(9, 15, 0),
            osgb_eastings=150000,
            osgb_northings=250000,
            osgb_gridref="TQ 50000 50000",
            fb_number="",
            condition="G",
            comment="Test log entry 4",
            score=6,
            ip_addr="127.0.0.1",
            source="W",
            upd_timestamp=datetime(2023, 11, 20, 9, 15, 0),
        ),
        TLog(
            trig_id=2,
            user_id=None,
            date=date(2023, 11, 15),
            time=time(11, 30, 0),
            osgb_eastings=150000,
            osgb_northings=250000,
            osgb_gridref="TQ 50000 50000",
            fb_number="",
            condition="G",
            comment="Test log entry 5",
            score=7,
            ip_addr="127.0.0.1",
            source="W",
            upd_timestamp=datetime(2023, 11, 15, 11, 30, 0),
        ),
    ]
    for entry in entries:
        db.add(entry)
    db.commit()
    return entries
