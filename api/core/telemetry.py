"""
OpenTelemetry instrumentation for distributed tracing and performance monitoring.

This module sets up OpenTelemetry tracing for the FastAPI application, sending
traces to Grafana Cloud (or any OTLP-compatible endpoint) for visualization
of latency heatmaps, percentiles, and distributed traces.
"""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


def initialize_telemetry(
    enabled: bool = False,
    metrics_enabled: bool = False,
    service_name: Optional[str] = None,
    environment: str = "development",
    otlp_endpoint: Optional[str] = None,
    otlp_headers: Optional[str] = None,
    pyroscope_enabled: bool = False,
    pyroscope_server_address: Optional[str] = None,
    pyroscope_auth_token: Optional[str] = None,
    pyroscope_application_name: Optional[str] = None,
    app_instance=None,  # FastAPI app instance for instrumentation
) -> None:
    """
    Initialize OpenTelemetry instrumentation for tracing and metrics, and Pyroscope for profiling.

    This function sets up:
    - Resource attributes (service name, environment)
    - OTLP exporter for sending traces and metrics to Grafana Cloud
    - Automatic instrumentation for FastAPI and SQLAlchemy
    - Tracer provider and metrics provider
    - Pyroscope continuous profiling

    Args:
        enabled: Whether to enable tracing (default: False)
        metrics_enabled: Whether to enable metrics collection (default: False)
        service_name: Name of the service (e.g., "trigpointing-api-production")
        environment: Environment name (development, staging, production)
        otlp_endpoint: OTLP endpoint URL (e.g., Grafana Cloud endpoint)
        otlp_headers: OTLP authentication headers (e.g., API key for Grafana Cloud)
        pyroscope_enabled: Whether to enable Pyroscope profiling (default: False)
        pyroscope_server_address: Pyroscope server URL
        pyroscope_auth_token: Pyroscope authentication token
        pyroscope_application_name: Application name for Pyroscope
        app_instance: FastAPI app instance to instrument (optional)

    Example:
        initialize_telemetry(
            enabled=True,
            metrics_enabled=True,
            service_name="trigpointing-api",
            environment="production",
            otlp_endpoint="https://otlp-gateway-prod.grafana.net/otlp",
            otlp_headers="Authorization=Basic <base64-encoded-token>",
            pyroscope_enabled=True,
            pyroscope_server_address="https://profiles-prod-001.grafana.net",
            pyroscope_auth_token="<token>"
        )
    """
    if not enabled and not metrics_enabled:
        logger.info("OpenTelemetry is disabled")
        return

    if not otlp_endpoint:
        logger.warning(
            "OpenTelemetry is enabled but OTEL_EXPORTER_OTLP_ENDPOINT is not set. "
            "Telemetry will not be exported."
        )
        return

    try:
        from opentelemetry import metrics as otel_metrics
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.http.metric_exporter import (
            OTLPMetricExporter,
        )
        from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
        from opentelemetry.sdk.metrics import MeterProvider
        from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
        from opentelemetry.sdk.resources import Resource
        from opentelemetry.sdk.trace import TracerProvider
        from opentelemetry.sdk.trace.export import BatchSpanProcessor

        # Set up resource attributes
        resource = Resource.create(
            {
                "service.name": service_name or f"trigpointing-api-{environment}",
                "service.version": "1.0.0",  # Could be populated from __version__.py
                "deployment.environment": environment,
            }
        )

        # Create tracer provider with resource
        tracer_provider = TracerProvider(resource=resource)

        # Parse OTLP headers if provided
        # Expected format: "key1=value1,key2=value2" or just "Authorization=Basic ..."
        # The HTTP exporter expects a dictionary of header name to value
        headers = None
        if otlp_headers:
            headers_dict = {}
            for header in otlp_headers.split(","):
                if "=" in header:
                    key, value = header.split("=", 1)
                    headers_dict[key.strip()] = value.strip()
            headers = headers_dict if headers_dict else None

        # Initialize tracing if enabled
        if enabled:
            # Set up OTLP trace exporter (HTTP version accepts full URLs)
            # The endpoint should NOT include /v1/traces - the exporter adds it automatically
            # Use the base OTLP endpoint like: https://otlp-gateway-prod-gb-south-1.grafana.net/otlp
            trace_endpoint = otlp_endpoint
            if trace_endpoint.endswith("/v1/traces"):
                trace_endpoint = trace_endpoint.replace("/v1/traces", "")

            otlp_trace_exporter = OTLPSpanExporter(
                endpoint=f"{trace_endpoint}/v1/traces",
                headers=headers,
                timeout=10,  # 10 second timeout for exports
            )

            # Add span processor to send spans in batches
            tracer_provider.add_span_processor(BatchSpanProcessor(otlp_trace_exporter))

            # Set the global tracer provider
            trace.set_tracer_provider(tracer_provider)

            logger.info("OpenTelemetry tracing initialized successfully")

        # Initialize metrics if enabled
        if metrics_enabled:
            # Set up OTLP metrics exporter
            # Use the correct endpoint for metrics: /v1/metrics instead of /v1/traces
            metrics_endpoint = otlp_endpoint
            if metrics_endpoint.endswith("/v1/traces"):
                metrics_endpoint = metrics_endpoint.replace("/v1/traces", "")

            otlp_metric_exporter = OTLPMetricExporter(
                endpoint=f"{metrics_endpoint}/v1/metrics",
                headers=headers,
                timeout=10,
            )

            # Create metric reader that exports every 60 seconds
            metric_reader = PeriodicExportingMetricReader(
                exporter=otlp_metric_exporter,
                export_interval_millis=60000,  # Export every 60 seconds
            )

            # Create and set meter provider
            meter_provider = MeterProvider(
                resource=resource,
                metric_readers=[metric_reader],
            )
            otel_metrics.set_meter_provider(meter_provider)

            # Initialize the metrics collector
            from api.core.metrics import initialize_metrics

            initialize_metrics()

            logger.info("OpenTelemetry metrics initialized successfully")

        # Instrument FastAPI and SQLAlchemy if tracing is enabled
        if enabled:
            # Note: FastAPI instrumentation should be done AFTER routes are added
            # If app_instance is provided, we skip instrumentation here and let
            # the caller do it at the right time (after routes are added)
            if app_instance is None:
                # Global instrumentation fallback (not recommended)
                FastAPIInstrumentor().instrument(
                    excluded_urls="/health,/metrics",
                )
                logger.warning(
                    "FastAPI instrumented globally - consider instrumenting after routes are added"
                )

            # Instrument SQLAlchemy automatically
            # This will create spans for all database queries with query text and parameters
            # Adds semantic conventions: db.system, db.name, db.statement, db.operation
            SQLAlchemyInstrumentor().instrument(
                # Enable commenter to add traceparent to SQL queries for correlation
                enable_commenter=True,
                # Capture statement parameters (be careful with sensitive data)
                commenter_options={},
            )

        logger.info(
            f"OpenTelemetry initialized successfully for {service_name or 'trigpointing-api'} "
            f"in {environment} environment, exporting to {otlp_endpoint}"
            f" (tracing: {enabled}, metrics: {metrics_enabled})"
        )

    except ImportError as e:
        logger.error(
            f"Failed to initialize OpenTelemetry: {e}. "
            "Please ensure opentelemetry packages are installed."
        )
    except Exception as e:
        logger.error(f"Unexpected error initializing OpenTelemetry: {e}")

    # Initialize Pyroscope continuous profiling
    if pyroscope_enabled and pyroscope_server_address:
        try:
            import pyroscope

            app_name = (
                pyroscope_application_name
                or service_name
                or f"trigpointing-api-{environment}"
            )

            # Configure Pyroscope profiler
            pyroscope.configure(
                application_name=app_name,
                server_address=pyroscope_server_address,
                auth_token=pyroscope_auth_token,
                # Tags for filtering in Pyroscope UI
                tags={
                    "environment": environment,
                    "service": app_name,
                },
                # Sample rate (10ms intervals is the default, very low overhead)
                sample_rate=100,  # Sample every 100Hz (10ms)
                # Enable profiling for CPU
                detect_subprocesses=False,  # Disable subprocess profiling for FastAPI
                oncpu=True,  # Enable CPU profiling (default, very low overhead)
            )

            logger.info(
                f"Pyroscope initialized and started profiling for {app_name} "
                f"in {environment} environment, exporting to {pyroscope_server_address}"
            )

        except ImportError as e:
            logger.error(
                f"Failed to initialize Pyroscope: {e}. "
                "Please ensure pyroscope-io package is installed."
            )
        except Exception as e:
            logger.error(f"Unexpected error initializing Pyroscope: {e}")
    elif pyroscope_enabled and not pyroscope_server_address:
        logger.warning(
            "Pyroscope is enabled but PYROSCOPE_SERVER_ADDRESS is not set. "
            "Profiling will not be exported."
        )


def shutdown_telemetry() -> None:
    """
    Shutdown OpenTelemetry gracefully, flushing any remaining spans.

    This should be called on application shutdown to ensure all traces
    are exported before the application exits.
    """
    try:
        from opentelemetry import trace

        tracer_provider = trace.get_tracer_provider()
        if hasattr(tracer_provider, "shutdown"):
            tracer_provider.shutdown()
            logger.info("OpenTelemetry shutdown successfully")
    except Exception as e:
        logger.error(f"Error shutting down OpenTelemetry: {e}")
