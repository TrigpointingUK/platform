"""
Request timing middleware for FastAPI using Server-Timing standard.

Adds Server-Timing header to all responses showing request processing time.
This header is natively supported by browser developer tools.
"""

import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware to add request duration using Server-Timing header."""

    async def dispatch(self, request: Request, call_next):
        """
        Process request and add timing header to response.

        Args:
            request: The incoming request
            call_next: The next middleware or route handler

        Returns:
            Response with Server-Timing header added
        """
        start_time = time.perf_counter()

        # Process the request
        response = await call_next(request)

        # Calculate duration in milliseconds
        duration_ms = (time.perf_counter() - start_time) * 1000

        # Add Server-Timing header (standard format)
        # Format: Server-Timing: total;dur=123.45;desc="Total"
        response.headers["Server-Timing"] = (
            f'total;dur={duration_ms:.2f};desc="Total Request Time"'
        )

        # Also add simple X-Request-Duration for backwards compatibility
        response.headers["X-Request-Duration"] = f"{duration_ms:.2f}ms"

        return response
