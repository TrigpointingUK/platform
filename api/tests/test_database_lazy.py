"""
Tests for lazy database connection functionality.
"""

from unittest.mock import MagicMock, patch

from api.core.config import settings
from api.db.database import get_db, get_engine, get_session_local


class TestLazyDatabaseConnection:
    """Test lazy database connection functionality."""

    def test_get_engine_creates_engine_lazily(self):
        """Test that get_engine creates engine only when first called."""
        # Reset global state
        import api.db.database

        api.db.database._engine = None

        with patch("api.db.database.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            # First call should create engine
            engine1 = get_engine()
            assert engine1 == mock_engine
            assert mock_create_engine.call_count == 1

            # Second call should return same engine without creating new one
            engine2 = get_engine()
            assert engine2 == mock_engine
            assert mock_create_engine.call_count == 1  # Still only called once

    def test_get_engine_uses_correct_parameters(self):
        """Test that get_engine creates engine with correct parameters."""
        # Reset global state
        import api.db.database

        api.db.database._engine = None

        with patch("api.db.database.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            # Call get_engine
            get_engine()

            # Verify create_engine was called with correct parameters
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args

            # Check positional arguments (DATABASE_URL)
            assert call_args[0][0] == settings.DATABASE_URL

            # Check keyword arguments
            assert call_args[1]["pool_pre_ping"] is True
            assert call_args[1]["pool_recycle"] == 300
            # echo should always be False - we control logging via logging configuration
            assert call_args[1]["echo"] is False

    def test_get_session_local_creates_sessionmaker_lazily(self):
        """Test that get_session_local creates sessionmaker only when first called."""
        # Reset global state
        import api.db.database

        api.db.database._SessionLocal = None
        api.db.database._engine = MagicMock()

        with patch("api.db.database.sessionmaker") as mock_sessionmaker:
            mock_session_local = MagicMock()
            mock_sessionmaker.return_value = mock_session_local

            # First call should create sessionmaker
            session_local1 = get_session_local()
            assert session_local1 == mock_session_local
            assert mock_sessionmaker.call_count == 1

            # Second call should return same sessionmaker without creating new one
            session_local2 = get_session_local()
            assert session_local2 == mock_session_local
            assert mock_sessionmaker.call_count == 1  # Still only called once

    def test_get_db_uses_session_local(self):
        """Test that get_db uses the session local correctly."""
        # Reset global state
        import api.db.database

        api.db.database._SessionLocal = None
        api.db.database._engine = MagicMock()

        with patch("api.db.database.sessionmaker") as mock_sessionmaker:
            mock_session_local = MagicMock()
            mock_session = MagicMock()
            mock_session_local.return_value = mock_session
            mock_sessionmaker.return_value = mock_session_local

            # Test get_db generator
            db_gen = get_db()
            db = next(db_gen)

            # Should have called sessionmaker and created session
            assert db == mock_session
            assert mock_sessionmaker.call_count == 1
            assert mock_session_local.call_count == 1

            # Test cleanup
            try:
                next(db_gen)
            except StopIteration:
                pass  # Expected for generator

            # Session should be closed
            mock_session.close.assert_called_once()

    def test_engine_creation_with_correct_parameters(self):
        """Test that engine is created with correct parameters."""
        # Reset global state
        import api.db.database

        api.db.database._engine = None

        with patch("api.db.database.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            get_engine()

            # Verify create_engine was called with correct parameters
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args

            # Check that DATABASE_URL is passed (actual value, not variable name)
            # This test is hardcoded because test environment defaults to these values
            # and DATABASE_URL property is computed from DB_* settings
            assert (
                "postgresql+psycopg2://" in call_args[0][0]
                or "sqlite" in call_args[0][0]
            )

            # Check keyword arguments
            kwargs = call_args[1]
            assert kwargs["pool_pre_ping"] is True
            assert kwargs["pool_recycle"] == 300
            assert "echo" in kwargs  # Should be settings.DEBUG

    def test_engine_creation_with_real_settings(self):
        """Test that engine is created with real settings object."""
        # Reset global state
        import api.db.database

        api.db.database._engine = None

        with patch("api.db.database.create_engine") as mock_create_engine:
            mock_engine = MagicMock()
            mock_create_engine.return_value = mock_engine

            # This should trigger the actual engine creation code path
            engine = get_engine()

            # Verify create_engine was called
            mock_create_engine.assert_called_once()
            call_args = mock_create_engine.call_args

            # Check that it was called with settings.DATABASE_URL
            from api.core.config import settings

            expected_url = settings.DATABASE_URL
            assert call_args[0][0] == expected_url

            # Check keyword arguments
            kwargs = call_args[1]
            assert kwargs["pool_pre_ping"] is True
            assert kwargs["pool_recycle"] == 300
            # echo should always be False - we control logging via logging configuration
            assert kwargs["echo"] is False

            # Verify the engine is returned
            assert engine == mock_engine
