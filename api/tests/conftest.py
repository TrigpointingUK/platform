"""
Test configuration and fixtures.
"""

import os
import uuid
import warnings
from contextvars import ContextVar
from typing import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

# from api.core.security import get_password_hash  # No longer needed - using Unix crypt
from api.db.database import Base, get_db
from api.db.user_activity_summary_view import (
    CREATE_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS,
    DROP_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS,
)
from api.main import app

# Import all models to ensure they're registered with Base.metadata for create_all()
from api.models import (  # noqa: F401
    Area,
    AreaType,
    Attr,
    AttrSet,
    AttrSetAttrVal,
    AttrSource,
    AttrVal,
    Postcode,
    Server,
    Status,
    TLog,
    Town,
    TPhoto,
    TPhotoVote,
    Trig,
    TrigCategory,
    TrigType,
    User,
)

# Legacy JWT tokens removed - Auth0 only


# Filter out deprecation warnings that are not actionable
warnings.filterwarnings("ignore", category=DeprecationWarning, module="pydantic.*")
warnings.filterwarnings(
    "ignore", category=PendingDeprecationWarning, module="starlette.*"
)
warnings.filterwarnings("ignore", category=DeprecationWarning, module="passlib.*")


def get_test_database_url():
    """Get PostgreSQL database URL for testing."""
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


def get_test_schema_name() -> str:
    """Return per-worker schema name for xdist isolation."""
    worker_id = os.environ.get("PYTEST_XDIST_WORKER", "gw0")
    return f"test_{worker_id}"


TEST_SCHEMA = os.environ.get("TEST_DB_SCHEMA", get_test_schema_name())

# Test database URL
SQLALCHEMY_DATABASE_URL = get_test_database_url()

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    poolclass=NullPool,
    connect_args={"options": f"-c search_path={TEST_SCHEMA},public"},
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

_TEST_SESSION: ContextVar[Session | None] = ContextVar("_TEST_SESSION", default=None)


def override_get_db():
    """Override get_db dependency for testing."""
    session = _TEST_SESSION.get()
    if session is not None:
        yield session
        return

    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session", autouse=True)
def setup_worker_schema() -> Generator[None, None, None]:
    """Create a dedicated schema per xdist worker for isolation."""
    schema_name = TEST_SCHEMA
    with engine.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA IF NOT EXISTS "{schema_name}"'))

    yield


def _install_upd_timestamp_triggers(connection, schema_name: str) -> None:
    """
    Install `upd_timestamp` triggers + defaults in the test database.

    Tests build the schema via Base.metadata.create_all(), so Alembic migrations
    (which create these triggers in real environments) are not applied here.
    """
    connection.execute(text(f"""
            CREATE OR REPLACE FUNCTION "{schema_name}".set_upd_timestamp_utc()
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
            """))

    connection.execute(
        text("""
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
                      AND c.table_schema = :schema_name
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
                        'FOR EACH ROW EXECUTE FUNCTION %I.set_upd_timestamp_utc()',
                        r.table_schema,
                        r.table_name,
                        r.table_schema
                    );
                END LOOP;
            END
            $$;
            """),
        {"schema_name": schema_name},
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_tables(setup_worker_schema):
    """Create all tables once at the session start for each worker."""
    # Create tables within the per-worker schema.
    _ = setup_worker_schema
    try:
        # Ensure PostGIS extension is available
        with engine.begin() as connection:
            connection.execute(
                text("CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA public")
            )

        # Drop and recreate tables to ensure schema is up to date
        # (create_all doesn't add new columns to existing tables)
        with engine.begin() as connection:
            connection.execute(text("DROP TABLE IF EXISTS postcodes CASCADE"))
            # Drop tphotovote, tphoto and tlog to pick up status column added for draft logs
            # and ensure foreign key constraints are current
            connection.execute(text("DROP TABLE IF EXISTS tphotovote CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS tphoto CASCADE"))
            connection.execute(text("DROP TABLE IF EXISTS tlog CASCADE"))

        Base.metadata.create_all(bind=engine)
        with engine.begin() as connection:
            _install_upd_timestamp_triggers(connection, TEST_SCHEMA)
            for statement in DROP_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS:
                connection.execute(text(statement))
            for statement in CREATE_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS:
                connection.execute(text(statement))
    except Exception as e:
        # Tables likely already exist from another worker
        # Log the error for debugging if it's not a duplicate table error
        import sys

        if "already exists" not in str(e):
            print(f"Warning: setup_test_tables failed: {e}", file=sys.stderr)
        pass

    # Seed minimal reference rows used by many tests (FK constraints are now enforced).
    try:
        with engine.begin() as connection:
            connection.execute(text("""
                    INSERT INTO status (id, name, descr, limit_descr)
                    VALUES (1, 'ACTIVE', 'Active', 'Active')
                    ON CONFLICT (id) DO NOTHING
                    """))
            connection.execute(text("""
                    INSERT INTO status (id, name, descr, limit_descr)
                    VALUES (0, 'UNKNOWN', 'Unknown', 'Unknown')
                    ON CONFLICT (id) DO NOTHING
                    """))
            connection.execute(text("""
                    INSERT INTO status (id, name, descr, limit_descr)
                    VALUES (10, 'TEST', 'Test', 'Test')
                    ON CONFLICT (id) DO NOTHING
                    """))

            connection.execute(text("""
                    INSERT INTO server (id, url, path, name)
                    VALUES
                        (1, 'https://example.invalid/1/', '/', 'Test Server 1'),
                        (3, 'https://example.invalid/3/', '/', 'Test Server 3'),
                        (999, 'https://example.invalid/999/', '/', 'Test Server 999')
                    ON CONFLICT (id) DO NOTHING
                    """))

    except Exception:
        # Best-effort seeding; tests can still create their own reference data.
        pass

    yield

    # Don't drop tables - let the test database cleanup handle it


@pytest.fixture(scope="function", autouse=True)
def _db_session():
    """Provide a per-test session wrapped in a rollback-only transaction."""
    connection = engine.connect()
    transaction = connection.begin()
    session = TestingSessionLocal(bind=connection)
    session.begin_nested()

    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(sess, trans):
        if trans.nested and not sess.in_nested_transaction():
            sess.begin_nested()

    original_rollback = session.rollback

    def _rollback_to_savepoint():
        current = session.get_transaction()
        if current is not None and current.nested:
            current.rollback()
            return

        original_rollback()

    session.rollback = _rollback_to_savepoint  # type: ignore[method-assign]

    token = _TEST_SESSION.set(session)
    try:
        yield session
    finally:
        _TEST_SESSION.reset(token)
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture(scope="function")
def db(_db_session):
    """Expose the per-test session for direct DB usage."""
    return _db_session


@pytest.fixture(scope="function")
def client(monkeypatch, db):
    """Create test client with token validator patched for Auth0 tokens only."""
    _ = db

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
                # Special case for auth0|admin - return any existing user
                # (scope check handles admin authorization separately)
                if auth0_user_id == "auth0|admin":
                    return db.query(UserModel).first()
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
def make_user(db):
    """Factory for creating users with unique fields by default."""

    def _make_user(**overrides):
        from passlib.hash import des_crypt

        unique_suffix = overrides.pop("unique_suffix", uuid.uuid4().hex[:8])
        test_password = overrides.pop("test_password", "testpassword123")
        cryptpw = overrides.pop("cryptpw", des_crypt.hash(test_password))

        user = User(
            name=overrides.pop("name", f"testuser_{unique_suffix}"),
            firstname=overrides.pop("firstname", "Test"),
            surname=overrides.pop("surname", "User"),
            email=overrides.pop("email", f"{unique_suffix}@example.com"),
            cryptpw=cryptpw,
            about=overrides.pop("about", "Test user for unit tests"),
            email_valid=overrides.pop("email_valid", "Y"),
            public_ind=overrides.pop("public_ind", "Y"),
            auth0_user_id=overrides.pop("auth0_user_id", None),
        )

        for key, value in overrides.items():
            setattr(user, key, value)

        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    return _make_user


@pytest.fixture
def test_user(make_user):
    """Create a test user with unique identifiers."""
    return make_user()


@pytest.fixture
def make_trig(db, test_user):
    """Factory for creating trigs with unique identifiers by default."""

    def _make_trig(**overrides):
        from datetime import date, time

        unique_suffix = overrides.pop("unique_suffix", uuid.uuid4().hex[:8])
        waypoint = overrides.pop("waypoint", f"TP{unique_suffix[:6]}".upper())

        trig = Trig(
            waypoint=waypoint,
            name=overrides.pop("name", f"Test Trig {unique_suffix}"),
            fb_number=overrides.pop("fb_number", f"FB{unique_suffix[:4]}"),
            stn_number=overrides.pop("stn_number", f"STN{unique_suffix[:4]}"),
            status_id=overrides.pop("status_id", 1),
            user_added=overrides.pop("user_added", 0),
            current_use=overrides.pop("current_use", "Passive station"),
            historic_use=overrides.pop("historic_use", "Primary"),
            condition=overrides.pop("condition", "G"),
            location=overrides.pop("location", None),
            wgs_lat=overrides.pop("wgs_lat", 0.0),
            wgs_long=overrides.pop("wgs_long", 0.0),
            wgs_height=overrides.pop("wgs_height", 0),
            osgb_eastings=overrides.pop("osgb_eastings", 100000),
            osgb_northings=overrides.pop("osgb_northings", 200000),
            osgb_gridref=overrides.pop("osgb_gridref", "TQ 00000 00000"),
            osgb_height=overrides.pop("osgb_height", 0),
            postcode=overrides.pop("postcode", None),
            # Note: county is now derived from trig_area table
            town=overrides.pop("town", "Testtown"),
            permission_ind=overrides.pop("permission_ind", "Y"),
            needs_attention=overrides.pop("needs_attention", 0),
            attention_comment=overrides.pop("attention_comment", ""),
            crt_date=overrides.pop("crt_date", date(2023, 1, 1)),
            crt_time=overrides.pop("crt_time", time(0, 0, 0)),
            crt_user_id=overrides.pop("crt_user_id", test_user.id),
            crt_ip_addr=overrides.pop("crt_ip_addr", "127.0.0.1"),
        )

        for key, value in overrides.items():
            setattr(trig, key, value)

        db.add(trig)
        db.commit()
        db.refresh(trig)
        return trig

    return _make_trig


@pytest.fixture
def test_trig(make_trig):
    return make_trig()


@pytest.fixture
def test_trig_two(make_trig):
    return make_trig(
        osgb_eastings=150000,
        osgb_northings=250000,
        osgb_gridref="TQ 50000 50000",
    )


@pytest.fixture
def test_tlog_entries(db, test_user, make_trig):
    """Create test tlog entries."""
    from datetime import date, datetime, time

    trig_one = make_trig(
        osgb_eastings=100000,
        osgb_northings=200000,
        osgb_gridref="TQ 00000 00000",
    )
    trig_two = make_trig(
        osgb_eastings=150000,
        osgb_northings=250000,
        osgb_gridref="TQ 50000 50000",
    )

    entries = [
        TLog(
            trig_id=trig_one.id,
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
            trig_id=trig_one.id,
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
            trig_id=trig_one.id,
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
            trig_id=trig_two.id,
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
            trig_id=trig_two.id,
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
