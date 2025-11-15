"""
Logging configuration for the FastAPI application.

This module sets up structured logging with appropriate levels and formats
for both development and production environments.
"""

import json
import logging
import sys
from typing import Optional

from api.core.config import settings


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging in production."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON with single-line exception traces."""
        log_data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }

        # Add exception info if present - format as single line with \n preserved in string
        if record.exc_info:
            exception_text = self.formatException(record.exc_info)
            # Replace actual newlines with \n escape sequence for single-line JSON
            log_data["exception"] = exception_text.replace("\n", "\\n")
            exc_type_name: str | None = (
                record.exc_info[0].__name__ if record.exc_info[0] else None
            )
            if exc_type_name:
                log_data["exc_type"] = exc_type_name

        # Add stack trace if present (for logger.exception() calls)
        if record.stack_info:
            log_data["stack_info"] = record.stack_info.replace("\n", "\\n")

        # Add extra fields if present
        if hasattr(record, "extra"):
            log_data.update(record.extra)

        return json.dumps(log_data)


def setup_logging(log_level: Optional[str] = None) -> None:
    """
    Configure logging for the application.

    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
                  If None, uses settings.LOG_LEVEL or DEBUG in development mode, INFO in production
    """
    # Determine log level
    if log_level is None:
        log_level = (
            settings.LOG_LEVEL
            if hasattr(settings, "LOG_LEVEL")
            else ("DEBUG" if settings.DEBUG else "INFO")
        )

    # Convert string to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Choose formatter based on environment
    if settings.DEBUG:
        # Use human-readable format for development
        formatter = logging.Formatter(
            fmt="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    else:
        # Use JSON format for production/staging
        formatter = JSONFormatter(datefmt="%Y-%m-%d %H:%M:%S")

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Remove existing handlers to avoid duplicates
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(numeric_level)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Set specific logger levels for noisy libraries
    # Completely silence SQLAlchemy unless there's an error
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("uvicorn.error").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.engine").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.pool").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.dialects").setLevel(logging.ERROR)
    logging.getLogger("sqlalchemy.orm").setLevel(logging.ERROR)
    logging.getLogger("botocore").setLevel(logging.WARNING)
    logging.getLogger("boto3").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)

    # Log the configuration
    logging.info(f"Logging configured with level: {log_level.upper()}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured logger instance
    """
    return logging.getLogger(name)
