"""
OpenTelemetry metrics instrumentation for application performance monitoring.

This module provides metrics collection for:
- HTTP request metrics (RED: Rate, Errors, Duration)
- Database performance metrics
- Custom business metrics

All metrics are exported to Grafana Cloud via OTLP.
"""

import logging
import time
from contextlib import contextmanager
from typing import Optional

from opentelemetry import metrics
from opentelemetry.metrics import Counter, Histogram, UpDownCounter

logger = logging.getLogger(__name__)


class MetricsCollector:
    """
    Centralized metrics collection for the application.

    This class provides helper methods to record metrics throughout the application
    without coupling business logic to OpenTelemetry APIs directly.
    """

    def __init__(self):
        """Initialize the metrics collector with OpenTelemetry meter."""
        self.meter = metrics.get_meter(__name__)
        self._initialize_http_metrics()
        self._initialize_database_metrics()
        self._initialize_business_metrics()

    def _initialize_http_metrics(self) -> None:
        """Initialize HTTP request metrics following OpenTelemetry semantic conventions."""
        # HTTP request counter
        self.http_request_count: Counter = self.meter.create_counter(
            name="http.server.request.count",
            description="Total number of HTTP requests",
            unit="1",
        )

        # HTTP request duration histogram
        self.http_request_duration: Histogram = self.meter.create_histogram(
            name="http.server.request.duration",
            description="Duration of HTTP requests",
            unit="ms",
        )

        # Active HTTP requests gauge
        self.http_active_requests: UpDownCounter = self.meter.create_up_down_counter(
            name="http.server.active_requests",
            description="Number of active HTTP requests",
            unit="1",
        )

    def _initialize_database_metrics(self) -> None:
        """Initialize database performance metrics."""
        # Database query duration histogram
        self.db_query_duration: Histogram = self.meter.create_histogram(
            name="db.query.duration",
            description="Duration of database queries",
            unit="ms",
        )

        # Database query counter
        self.db_query_count: Counter = self.meter.create_counter(
            name="db.query.count",
            description="Total number of database queries",
            unit="1",
        )

        # Database connection pool size
        self.db_pool_size: UpDownCounter = self.meter.create_up_down_counter(
            name="db.pool.size",
            description="Current size of database connection pool",
            unit="1",
        )

        # Database connection pool idle connections
        self.db_pool_idle: UpDownCounter = self.meter.create_up_down_counter(
            name="db.pool.idle",
            description="Number of idle connections in database pool",
            unit="1",
        )

    def _initialize_business_metrics(self) -> None:
        """Initialize custom business metrics for Trigpointing UK."""
        # Trig metrics
        self.trigs_viewed: Counter = self.meter.create_counter(
            name="trigpointing.trigs.viewed",
            description="Number of trig detail views",
            unit="1",
        )

        self.trigs_searched: Counter = self.meter.create_counter(
            name="trigpointing.trigs.searched",
            description="Number of trig search operations",
            unit="1",
        )

        # Photo metrics
        self.photos_uploaded: Counter = self.meter.create_counter(
            name="trigpointing.photos.uploaded",
            description="Number of photo uploads",
            unit="1",
        )

        self.photos_processing_duration: Histogram = self.meter.create_histogram(
            name="trigpointing.photos.processing_duration",
            description="Duration of photo processing",
            unit="ms",
        )

        # Cache metrics
        self.cache_hits: Counter = self.meter.create_counter(
            name="trigpointing.cache.hits",
            description="Number of cache hits",
            unit="1",
        )

        self.cache_misses: Counter = self.meter.create_counter(
            name="trigpointing.cache.misses",
            description="Number of cache misses",
            unit="1",
        )

    # HTTP Metrics Helper Methods

    def record_http_request(
        self,
        method: str,
        route: str,
        status_code: int,
        duration_ms: float,
    ) -> None:
        """
        Record an HTTP request with all relevant metrics.

        Args:
            method: HTTP method (GET, POST, etc.)
            route: HTTP route pattern (e.g., /v1/trigs/{id})
            status_code: HTTP status code (200, 404, 500, etc.)
            duration_ms: Request duration in milliseconds
        """
        attributes = {
            "http.method": method,
            "http.route": route,
            "http.status_code": str(status_code),
        }

        self.http_request_count.add(1, attributes)
        self.http_request_duration.record(duration_ms, attributes)

    @contextmanager
    def track_active_request(self, method: str, route: str):
        """
        Context manager to track active HTTP requests.

        Usage:
            with metrics.track_active_request("GET", "/v1/trigs"):
                # process request
                pass
        """
        attributes = {
            "http.method": method,
            "http.route": route,
        }
        self.http_active_requests.add(1, attributes)
        try:
            yield
        finally:
            self.http_active_requests.add(-1, attributes)

    # Database Metrics Helper Methods

    def record_db_query(
        self,
        operation: str,
        duration_ms: float,
        table: Optional[str] = None,
    ) -> None:
        """
        Record a database query execution.

        Args:
            operation: SQL operation (SELECT, INSERT, UPDATE, DELETE)
            duration_ms: Query duration in milliseconds
            table: Optional table name
        """
        attributes = {
            "db.operation": operation,
            "db.system": "postgresql",
        }
        if table:
            attributes["db.table"] = table

        self.db_query_count.add(1, attributes)
        self.db_query_duration.record(duration_ms, attributes)

    @contextmanager
    def track_db_query(self, operation: str, table: Optional[str] = None):
        """
        Context manager to track database query execution.

        Usage:
            with metrics.track_db_query("SELECT", "trig"):
                # execute query
                pass
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.record_db_query(operation, duration_ms, table)

    def update_db_pool_metrics(self, size: int, idle: int) -> None:
        """
        Update database connection pool metrics.

        Args:
            size: Current pool size
            idle: Number of idle connections
        """
        # These are absolute values, not deltas
        # We record them directly; the up-down counter will handle the changes
        # Note: For gauges, we'd want to use an observable gauge that periodically
        # reads the pool stats. For now, we update when called.
        # This is a simplification - ideally we'd use callbacks
        pass  # Will be implemented when we integrate with the DB pool

    # Business Metrics Helper Methods

    def record_trig_view(self, trig_id: int, cache_status: str = "unknown") -> None:
        """
        Record a trig detail page view.

        Args:
            trig_id: ID of the trigpoint being viewed
            cache_status: Cache status - "hit", "miss", or "bypass"
        """
        self.trigs_viewed.add(
            1, {"trig_id": str(trig_id), "cache_status": cache_status}
        )

    def record_trig_search(self, search_type: str = "general") -> None:
        """
        Record a trig search operation.

        Args:
            search_type: Type of search (general, nearby, advanced)
        """
        self.trigs_searched.add(1, {"search_type": search_type})

    def record_photo_upload(self, status: str, trig_id: Optional[int] = None) -> None:
        """
        Record a photo upload.

        Args:
            status: Upload status (success, failure, rejected)
            trig_id: Optional trig ID the photo is associated with
        """
        attributes = {"status": status}
        if trig_id:
            attributes["trig_id"] = str(trig_id)

        self.photos_uploaded.add(1, attributes)

    @contextmanager
    def track_photo_processing(self):
        """
        Context manager to track photo processing duration.

        Usage:
            with metrics.track_photo_processing():
                # process photo
                pass
        """
        start_time = time.perf_counter()
        try:
            yield
        finally:
            duration_ms = (time.perf_counter() - start_time) * 1000
            self.photos_processing_duration.record(duration_ms)

    def record_cache_hit(self, cache_type: str) -> None:
        """
        Record a cache hit.

        Args:
            cache_type: Type of cache (auth0_token, api_response, tiles)
        """
        self.cache_hits.add(1, {"cache_type": cache_type})

    def record_cache_miss(self, cache_type: str) -> None:
        """
        Record a cache miss.

        Args:
            cache_type: Type of cache (auth0_token, api_response, tiles)
        """
        self.cache_misses.add(1, {"cache_type": cache_type})


# Global metrics collector instance
# This will be initialized when metrics are enabled
_metrics_collector: Optional[MetricsCollector] = None


def get_metrics_collector() -> Optional[MetricsCollector]:
    """
    Get the global metrics collector instance.

    Returns:
        MetricsCollector instance if metrics are enabled, None otherwise
    """
    return _metrics_collector


def initialize_metrics() -> None:
    """
    Initialize the global metrics collector.

    This should be called during application startup, after OpenTelemetry
    metrics provider has been configured.
    """
    global _metrics_collector

    try:
        _metrics_collector = MetricsCollector()
        logger.info("Metrics collector initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize metrics collector: {e}", exc_info=True)
        _metrics_collector = None


def shutdown_metrics() -> None:
    """
    Shutdown metrics collection gracefully.

    This should be called during application shutdown.
    """
    global _metrics_collector
    _metrics_collector = None
    logger.info("Metrics collector shutdown")
