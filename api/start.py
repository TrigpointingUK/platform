#!/usr/bin/env python
"""
Uvicorn startup script with JSON logging configuration.

This script starts the FastAPI application with proper logging configuration
to ensure all logs (including uvicorn's own logs) are formatted as JSON
in production environments.
"""

import os

import uvicorn

from api.core.logging import get_uvicorn_log_config

if __name__ == "__main__":
    # Use 0.0.0.0 for Docker, configurable via env var
    host = os.getenv("UVICORN_HOST", "0.0.0.0")  # nosec B104
    port = int(os.getenv("UVICORN_PORT", "8000"))

    # Get log configuration
    log_config = get_uvicorn_log_config()

    # Start uvicorn with JSON logging
    uvicorn.run(
        "api.main:app",
        host=host,
        port=port,
        log_config=log_config,
        # Disable uvicorn's default access log formatting (we handle it via log_config)
        access_log=True,
    )
