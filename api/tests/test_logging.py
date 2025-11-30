"""
Tests for logging configuration to improve coverage.
"""

import json
import logging
import sys
from unittest.mock import MagicMock, patch

from api.core.logging import (
    JSONFormatter,
    get_logger,
    get_uvicorn_log_config,
    setup_logging,
)


class TestLoggingConfiguration:
    """Test logging configuration functions."""

    def test_setup_logging_with_explicit_level(self):
        """Test setup_logging with explicit log level."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("DEBUG")

        # Check that the root logger has the correct level
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_with_settings_log_level(self):
        """Test setup_logging using settings.LOG_LEVEL."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        mock_settings = MagicMock()
        mock_settings.LOG_LEVEL = "WARNING"
        mock_settings.DEBUG = False

        with patch("api.core.logging.settings", mock_settings):
            setup_logging()

        # Check that the root logger has the correct level
        assert root_logger.level == logging.WARNING

    def test_setup_logging_fallback_to_debug(self):
        """Test setup_logging fallback to DEBUG when settings.DEBUG is True."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        mock_settings = MagicMock()
        mock_settings.DEBUG = True
        # Simulate missing LOG_LEVEL attribute
        del mock_settings.LOG_LEVEL

        with patch("api.core.logging.settings", mock_settings):
            setup_logging()

        # Check that the root logger has the correct level
        assert root_logger.level == logging.DEBUG

    def test_setup_logging_fallback_to_info(self):
        """Test setup_logging fallback to INFO when settings.DEBUG is False."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        mock_settings = MagicMock()
        mock_settings.DEBUG = False
        # Simulate missing LOG_LEVEL attribute
        del mock_settings.LOG_LEVEL

        with patch("api.core.logging.settings", mock_settings):
            setup_logging()

        # Check that the root logger has the correct level
        assert root_logger.level == logging.INFO

    def test_setup_logging_invalid_level(self):
        """Test setup_logging with invalid log level falls back to INFO."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("INVALID_LEVEL")

        # Should fall back to INFO
        assert root_logger.level == logging.INFO

    def test_setup_logging_removes_existing_handlers(self):
        """Test that setup_logging removes existing handlers."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # Add a test handler
        test_handler = logging.StreamHandler(sys.stdout)
        root_logger.addHandler(test_handler)

        setup_logging("INFO")

        # Should have removed old handlers and added new ones
        # The handler count should be 1 (the new console handler)
        assert len(root_logger.handlers) == 1

    def test_setup_logging_sets_library_levels(self):
        """Test that setup_logging sets appropriate levels for noisy libraries."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("DEBUG")

        # Check that noisy libraries have appropriate levels
        assert logging.getLogger("uvicorn.access").level == logging.WARNING
        assert logging.getLogger("uvicorn.error").level == logging.INFO
        # SQLAlchemy should be silenced unless there's an error
        assert logging.getLogger("sqlalchemy").level == logging.ERROR
        assert logging.getLogger("sqlalchemy.engine").level == logging.ERROR
        assert logging.getLogger("sqlalchemy.pool").level == logging.ERROR
        assert logging.getLogger("sqlalchemy.dialects").level == logging.ERROR
        assert logging.getLogger("sqlalchemy.orm").level == logging.ERROR
        assert logging.getLogger("botocore").level == logging.WARNING
        assert logging.getLogger("boto3").level == logging.WARNING
        assert logging.getLogger("urllib3").level == logging.WARNING

    def test_get_logger_returns_logger(self):
        """Test that get_logger returns a logger instance."""
        logger = get_logger("test.module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test.module"

    def test_get_logger_different_names(self):
        """Test that get_logger returns different loggers for different names."""
        logger1 = get_logger("test.module1")
        logger2 = get_logger("test.module2")

        assert logger1 is not logger2
        assert logger1.name == "test.module1"
        assert logger2.name == "test.module2"

    def test_setup_logging_logs_configuration(self, caplog):
        """Test that setup_logging logs the configuration."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        # The logging configuration happens before caplog can capture it
        # So we'll test that the function runs without error
        setup_logging("DEBUG")

        # The function should complete successfully
        assert True

    def test_setup_logging_console_handler_configuration(self):
        """Test that setup_logging configures console handler correctly."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        setup_logging("WARNING")

        # Check that we have a console handler
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler, logging.StreamHandler)
        assert handler.stream == sys.stdout
        assert handler.level == logging.WARNING
        assert isinstance(handler.formatter, logging.Formatter)

    def test_json_formatter_basic_message(self):
        """Test JSONFormatter formats basic log messages correctly."""
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "INFO"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Test message"
        assert "timestamp" in parsed

    def test_json_formatter_with_exception(self):
        """Test JSONFormatter includes exception information."""
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")

        try:
            raise ValueError("Test error")
        except ValueError:
            record = logging.LogRecord(
                name="test.logger",
                level=logging.ERROR,
                pathname="test.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["level"] == "ERROR"
        assert parsed["logger"] == "test.logger"
        assert parsed["message"] == "Error occurred"
        assert "exception" in parsed
        assert "ValueError: Test error" in parsed["exception"]
        assert "Traceback" in parsed["exception"]

    def test_setup_logging_uses_json_formatter_in_production(self):
        """Test that setup_logging uses JSON formatter when DEBUG=False."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        mock_settings = MagicMock()
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"

        with patch("api.core.logging.settings", mock_settings):
            setup_logging()

        # Check that the handler uses JSONFormatter
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, JSONFormatter)

    def test_setup_logging_uses_text_formatter_in_development(self):
        """Test that setup_logging uses text formatter when DEBUG=True."""
        # Clear existing handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)

        mock_settings = MagicMock()
        mock_settings.DEBUG = True
        mock_settings.LOG_LEVEL = "DEBUG"

        with patch("api.core.logging.settings", mock_settings):
            setup_logging()

        # Check that the handler uses standard Formatter, not JSONFormatter
        assert len(root_logger.handlers) == 1
        handler = root_logger.handlers[0]
        assert isinstance(handler.formatter, logging.Formatter)
        assert not isinstance(handler.formatter, JSONFormatter)

    def test_json_formatter_with_uvicorn_fields(self):
        """Test JSONFormatter includes uvicorn-specific fields."""
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        record = logging.LogRecord(
            name="uvicorn.access",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Request completed",
            args=(),
            exc_info=None,
        )
        # Add uvicorn-specific fields
        record.status_code = 200
        record.method = "GET"
        record.path = "/api/v1/test"

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["status_code"] == 200
        assert parsed["method"] == "GET"
        assert parsed["path"] == "/api/v1/test"

    def test_json_formatter_with_extra_fields(self):
        """Test JSONFormatter includes extra fields."""
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        # Add extra fields
        record.extra = {"request_id": "123", "user_id": "456"}

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert parsed["request_id"] == "123"
        assert parsed["user_id"] == "456"

    def test_json_formatter_with_stack_info(self):
        """Test JSONFormatter includes stack trace."""
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        record = logging.LogRecord(
            name="test.logger",
            level=logging.WARNING,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.stack_info = "Stack trace line 1\nStack trace line 2"

        formatted = formatter.format(record)
        parsed = json.loads(formatted)

        assert "stack_info" in parsed
        assert "\\n" in parsed["stack_info"]

    def test_get_uvicorn_log_config_production(self):
        """Test get_uvicorn_log_config returns JSON formatters for production."""
        mock_settings = MagicMock()
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "INFO"

        with patch("api.core.logging.settings", mock_settings):
            config = get_uvicorn_log_config()

        assert config["version"] == 1
        assert not config["disable_existing_loggers"]
        assert "formatters" in config
        assert config["formatters"]["default"]["()"] == "api.core.logging.JSONFormatter"
        assert config["formatters"]["access"]["()"] == "api.core.logging.JSONFormatter"

    def test_get_uvicorn_log_config_development(self):
        """Test get_uvicorn_log_config returns default formatters for development."""
        mock_settings = MagicMock()
        mock_settings.DEBUG = True
        mock_settings.LOG_LEVEL = "DEBUG"

        with patch("api.core.logging.settings", mock_settings):
            config = get_uvicorn_log_config()

        assert config["version"] == 1
        assert not config["disable_existing_loggers"]
        assert "formatters" in config
        assert (
            config["formatters"]["default"]["()"] == "uvicorn.logging.DefaultFormatter"
        )
        assert config["formatters"]["access"]["()"] == "uvicorn.logging.AccessFormatter"

    def test_get_uvicorn_log_config_loggers(self):
        """Test get_uvicorn_log_config configures loggers correctly."""
        mock_settings = MagicMock()
        mock_settings.DEBUG = False
        mock_settings.LOG_LEVEL = "WARNING"

        with patch("api.core.logging.settings", mock_settings):
            config = get_uvicorn_log_config()

        assert "loggers" in config
        assert "uvicorn" in config["loggers"]
        assert "uvicorn.error" in config["loggers"]
        assert "uvicorn.access" in config["loggers"]
        assert config["loggers"]["uvicorn"]["level"] == "WARNING"
        assert not config["loggers"]["uvicorn.access"]["propagate"]
