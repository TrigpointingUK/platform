"""
Main FastAPI application entry point
"""

import logging

from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer
from sqlalchemy import text
from sqlalchemy.orm import Session
from starlette.middleware.base import BaseHTTPMiddleware

from api.api.v1.api import api_router
from api.core.config import settings
from api.core.logging import setup_logging
from api.core.profiling import ProfilingMiddleware, should_enable_profiling
from api.core.telemetry import initialize_telemetry
from api.core.timing import TimingMiddleware
from api.db.database import get_db

logger = logging.getLogger(__name__)

# Configure logging first
setup_logging()

# Create FastAPI app instance
app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    debug=settings.DEBUG,
    swagger_ui_oauth2_redirect_url="/docs/oauth2-redirect",
    swagger_ui_init_oauth={
        "clientId": settings.AUTH0_SPA_CLIENT_ID or "",
        "appName": settings.PROJECT_NAME,
        # PKCE is recommended for SPA/Swagger flows
        "usePkceWithAuthorizationCodeGrant": True,
        # Pass audience so Auth0 issues an API token, not just OIDC profile
        "additionalQueryStringParams": {
            "audience": settings.AUTH0_API_AUDIENCE or "",
        },
    },
)

# Initialize OpenTelemetry (traces, metrics, Pyroscope)
# NOTE: FastAPI instrumentation happens AFTER routes are added (see end of file)
initialize_telemetry(
    enabled=settings.OTEL_ENABLED,
    metrics_enabled=settings.OTEL_METRICS_ENABLED,
    service_name=settings.OTEL_SERVICE_NAME,
    environment=settings.ENVIRONMENT,
    otlp_endpoint=settings.OTEL_EXPORTER_OTLP_ENDPOINT,
    otlp_headers=settings.OTEL_EXPORTER_OTLP_HEADERS,
    pyroscope_enabled=settings.PYROSCOPE_ENABLED,
    pyroscope_server_address=settings.PYROSCOPE_SERVER_ADDRESS,
    pyroscope_auth_token=settings.PYROSCOPE_AUTH_TOKEN,
    pyroscope_application_name=settings.PYROSCOPE_APPLICATION_NAME,
    app_instance=None,  # Don't instrument yet - routes not added
)

# Configure security scheme for Swagger UI
security_scheme = HTTPBearer()
app.openapi_schema = None  # Clear the schema cache


def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    from fastapi.openapi.utils import get_openapi

    openapi_schema = get_openapi(
        title=app.title,
        version="1.0.0",
        description="TrigpointingUK API",
        routes=app.routes,
    )

    # Add only OAuth2 security scheme (remove any Bearer schemes)
    openapi_schema.setdefault("components", {}).setdefault("securitySchemes", {})
    # Clean up any auto-added Bearer schemes from dependencies
    for k in list(openapi_schema["components"]["securitySchemes"].keys()):
        if k.lower().startswith("bearer") or k.lower() == "httpbearer":
            del openapi_schema["components"]["securitySchemes"][k]
    # OAuth2 Authorization Code (PKCE) for Auth0 login via Swagger UI
    # Always include OAuth2 scheme for docs/tests even if domain is not configured
    auth_domain = (
        f"https://{settings.AUTH0_CUSTOM_DOMAIN}"
        if getattr(settings, "AUTH0_CUSTOM_DOMAIN", None)
        else "https://example.com"
    )
    openapi_schema["components"]["securitySchemes"]["OAuth2"] = {
        "type": "oauth2",
        "flows": {
            "authorizationCode": {
                "authorizationUrl": f"{auth_domain}/authorize",
                "tokenUrl": f"{auth_domain}/oauth/token",
                "scopes": {
                    "openid": "OpenID Connect scope",
                    "profile": "Basic profile information",
                    "email": "Email address",
                    "api:admin": "Full administrative access to API",
                    "api:write": "Create and update own logs, photos, trigs",
                    "api:read-pii": "Read and write user PII (email, realName) for self",
                },
            }
        },
    }

    # Define public endpoints that should not have security requirements
    # Note: GET requests to these paths are public, but POST/PUT/DELETE require auth
    public_endpoints = {
        "/health",
        f"{settings.API_V1_STR}/trigs",
        f"{settings.API_V1_STR}/trigs/export",
        f"{settings.API_V1_STR}/trigs/{{trig_id}}",
        f"{settings.API_V1_STR}/trigs/{{trig_id}}/logs",
        f"{settings.API_V1_STR}/trigs/{{trig_id}}/map",
        f"{settings.API_V1_STR}/trigs/{{trig_id}}/photos",
        f"{settings.API_V1_STR}/trigs/waypoint/{{waypoint}}",
        f"{settings.API_V1_STR}/photos",
        f"{settings.API_V1_STR}/photos/{{photo_id}}",
        f"{settings.API_V1_STR}/photos/{{photo_id}}/evaluate",
        f"{settings.API_V1_STR}/users",
        f"{settings.API_V1_STR}/users/{{user_id}}",
        f"{settings.API_V1_STR}/users/{{user_id}}/badge",
        f"{settings.API_V1_STR}/users/{{user_id}}/logs",
        f"{settings.API_V1_STR}/users/{{user_id}}/map",
        f"{settings.API_V1_STR}/users/{{user_id}}/photos",
        f"{settings.API_V1_STR}/logs",
        f"{settings.API_V1_STR}/logs/{{log_id}}",
        f"{settings.API_V1_STR}/logs/{{log_id}}/photos",
        f"{settings.API_V1_STR}/stats/site",
    }

    # Define endpoints that are public regardless of HTTP method
    # Used for special cases like migration/onboarding endpoints
    fully_public_endpoints = {
        f"{settings.API_V1_STR}/legacy/login",
    }

    # Define endpoints with optional auth (should not have required security)
    optional_auth_endpoints: set[str] = {
        f"{settings.API_V1_STR}/admin/contact",
    }

    admin_endpoints = {
        f"{settings.API_V1_STR}/legacy/username-duplicates",
        f"{settings.API_V1_STR}/legacy/email-duplicates",
        f"{settings.API_V1_STR}/legacy/migrate_users",
        f"{settings.API_V1_STR}/admin/cache/stats",
        f"{settings.API_V1_STR}/admin/cache",
    }

    # Add security requirement to protected endpoints only
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method in ["get", "post", "put", "delete", "patch"]:
                endpoint = openapi_schema["paths"][path][method]

                # Skip fully public endpoints (all HTTP methods)
                if path in fully_public_endpoints:
                    continue

                # Skip public endpoints (GET requests only)
                if path in public_endpoints and method == "get":
                    continue

                # For optional auth endpoints, set optional security (grey padlock in Swagger)
                if path in optional_auth_endpoints:
                    endpoint["security"] = [
                        {"OAuth2": []},
                        {},
                    ]  # Empty object makes it optional
                    continue

                # Add security requirement to write endpoints and admin endpoints
                if path in admin_endpoints:
                    endpoint["security"] = [
                        {"OAuth2": ["openid", "profile", "api:admin"]}
                    ]
                elif method in ["post", "put", "patch", "delete"]:
                    # Require authentication for write operations
                    endpoint["security"] = [{"OAuth2": []}]
                else:
                    # GET requests to protected paths require authentication
                    endpoint["security"] = [{"OAuth2": []}]

    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi  # type: ignore

# Add timing middleware first to capture total request time
app.add_middleware(TimingMiddleware)


class HealthCheckLoggingFilter(BaseHTTPMiddleware):
    """Middleware to suppress logging for health check endpoints."""

    async def dispatch(self, request: Request, call_next):
        # Suppress logging context for health check requests
        if request.url.path == "/health":
            # Temporarily disable logging for this request
            logging.disable(logging.CRITICAL)
            try:
                response = await call_next(request)
                return response
            finally:
                # Re-enable logging
                logging.disable(logging.NOTSET)
        else:
            return await call_next(request)


# Add health check logging filter first
app.add_middleware(HealthCheckLoggingFilter)

# Set up CORS
if settings.BACKEND_CORS_ORIGINS:
    cors_origins = []
    for origin in settings.BACKEND_CORS_ORIGINS:
        origin_str = str(origin).strip()
        if origin_str.endswith("/"):
            origin_str = origin_str.rstrip("/")
        cors_origins.append(origin_str)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,  # Bearer tokens only, no cookies
        allow_methods=["*"],
        allow_headers=["*"],
    )

# Set up profiling middleware (development and staging only)
if settings.PROFILING_ENABLED and should_enable_profiling(settings.ENVIRONMENT):
    app.add_middleware(
        ProfilingMiddleware,
        default_format=settings.PROFILING_DEFAULT_FORMAT,
    )
    logger.info(
        f"Profiling enabled for {settings.ENVIRONMENT} environment "
        f"(default format: {settings.PROFILING_DEFAULT_FORMAT})"
    )
elif settings.PROFILING_ENABLED and not should_enable_profiling(settings.ENVIRONMENT):
    logger.warning(
        f"Profiling disabled in {settings.ENVIRONMENT} environment for security"
    )

# Include API router
app.include_router(api_router, prefix=settings.API_V1_STR)


@app.get("/health")
def health_check(db: Session = Depends(get_db)):
    """Health check endpoint with database connectivity verification."""
    # Import version information
    try:
        from api.__version__ import __build_time__, __version__

        version_info = {"version": __version__, "build_time": __build_time__}
    except ImportError:
        version_info = {"version": "unknown", "build_time": "unknown"}

    # Check database connectivity
    db_status = "unknown"
    db_error = None
    try:
        # Query trig table to verify database connectivity
        # Use a simple count query that doesn't depend on specific data existing
        result = db.execute(text("SELECT COUNT(*) FROM trig LIMIT 1"))
        result.scalar()  # Execute the query but don't store result
        db_status = "connected"
        # Don't log successful health checks - they happen every few seconds
    except Exception as e:
        db_status = "error"
        db_error = str(e)
        # Only log failures - this is important
        logger.error(f"Database health check failed: {e}")

    # Return unhealthy status if database is not connected
    if db_status != "connected":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "status": "unhealthy",
                "environment": settings.ENVIRONMENT,
                "version": version_info["version"],
                "build_time": version_info["build_time"],
                "database": db_status,
                "error": db_error,
            },
        )

    return {
        "status": "healthy",
        "environment": settings.ENVIRONMENT,
        "version": version_info["version"],
        "build_time": version_info["build_time"],
        "database": db_status,
    }


# Instrument FastAPI app AFTER all routes are added
# This must be done at the end so the instrumentor can see all routes
if settings.OTEL_ENABLED:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

    FastAPIInstrumentor.instrument_app(
        app,
        excluded_urls="/health,/metrics",
    )
    logger.info("FastAPI app instrumented with OpenTelemetry (after routes added)")


@app.get("/logout", include_in_schema=False)
def logout():
    """
    Logout endpoint for Swagger UI testing.

    Redirects to Auth0's logout endpoint to clear the Auth0 session,
    then returns to Swagger docs. This allows easy user switching during testing.

    Usage in Swagger:
    1. Click 'Authorize' and log in
    2. Test your endpoints
    3. Navigate to /logout in browser to clear session
    4. Return to Swagger and authorize with a different user
    """
    if not settings.AUTH0_CUSTOM_DOMAIN:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="AUTH0_CUSTOM_DOMAIN not configured",
        )

    # Get the base URL for returnTo (must match Allowed Logout URLs in Auth0)
    return_to = f"{settings.FASTAPI_URL}/docs"

    # Auth0 logout endpoint (use custom domain for user-facing URLs)
    # https://auth0.com/docs/api/authentication#logout
    client_id = settings.AUTH0_SPA_CLIENT_ID or ""
    logout_url = (
        f"https://{settings.AUTH0_CUSTOM_DOMAIN}/v2/logout?"
        f"client_id={client_id}&"
        f"returnTo={return_to}"
    )

    return RedirectResponse(url=logout_url)


if __name__ == "__main__":
    import os

    import uvicorn

    # Use 127.0.0.1 for security unless explicitly overridden (schema configurable)
    host = os.getenv("UVICORN_HOST", "127.0.0.1")
    port = int(os.getenv("UVICORN_PORT", "8000"))
    uvicorn.run(app, host=host, port=port)
