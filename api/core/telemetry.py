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
    service_name: Optional[str] = None,
    environment: str = "development",
    otlp_endpoint: Optional[str] = None,
    otlp_headers: Optional[str] = None,
) -> None:
    """
    Initialize OpenTelemetry instrumentation for tracing.

    This function sets up:
    - Resource attributes (service name, environment)
    - OTLP exporter for sending traces to Grafana Cloud
    - Automatic instrumentation for FastAPI and SQLAlchemy
    - Tracer provider and processor

    Args:
        enabled: Whether to enable telemetry (default: False)
        service_name: Name of the service (e.g., "trigpointing-api-production")
        environment: Environment name (development, staging, production)
        otlp_endpoint: OTLP endpoint URL (e.g., Grafana Cloud endpoint)
        otlp_headers: OTLP authentication headers (e.g., API key for Grafana Cloud)

    Example:
        initialize_telemetry(
            enabled=True,
            service_name="trigpointing-api",
            environment="production",
            otlp_endpoint="https://otlp-gateway-prod.grafana.net/otlp",
            otlp_headers="Authorization=Basic <base64-encoded-token>"
        )
    """
    if not enabled:
        logger.info("OpenTelemetry is disabled")
        return

    if not otlp_endpoint:
        logger.warning(
            "OpenTelemetry is enabled but OTEL_EXPORTER_OTLP_ENDPOINT is not set. "
            "Telemetry will not be exported."
        )
        return

    try:
        from opentelemetry import trace
        from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import (
            OTLPSpanExporter,
        )
        from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
        from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
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
        # gRPC requires headers as tuples of (key, value) pairs
        headers = None
        if otlp_headers:
            header_list = []
            for header in otlp_headers.split(","):
                if "=" in header:
                    key, value = header.split("=", 1)
                    # gRPC requires lowercase header names
                    header_list.append((key.strip().lower(), value.strip()))
            headers = tuple(header_list) if header_list else None

        # Set up OTLP exporter
        otlp_exporter = OTLPSpanExporter(
            endpoint=otlp_endpoint,
            headers=headers,
        )

        # Add span processor to send spans in batches
        tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

        # Set the global tracer provider
        trace.set_tracer_provider(tracer_provider)

        # Instrument FastAPI automatically
        # This will create spans for all HTTP requests
        FastAPIInstrumentor().instrument()

        # Instrument SQLAlchemy automatically
        # This will create spans for all database queries
        SQLAlchemyInstrumentor().instrument()

        logger.info(
            f"OpenTelemetry initialized successfully for {service_name or 'trigpointing-api'} "
            f"in {environment} environment, exporting to {otlp_endpoint}"
        )

    except ImportError as e:
        logger.error(
            f"Failed to initialize OpenTelemetry: {e}. "
            "Please ensure opentelemetry packages are installed."
        )
    except Exception as e:
        logger.error(f"Unexpected error initializing OpenTelemetry: {e}")


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
