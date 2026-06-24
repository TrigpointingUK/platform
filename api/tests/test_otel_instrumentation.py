"""Regression tests for OpenTelemetry FastAPI instrumentation.

Background
----------
A production outage was caused by bumping ``fastapi`` 0.136.1 -> 0.138.0 while
``opentelemetry-instrumentation-fastapi`` stayed pinned at 0.63b1. From 0.138
FastAPI places an ``_IncludedRouter`` marker object (which has no ``.path``
attribute) into ``app.routes`` for every ``include_router`` call. OTel 0.63b1
resolves a span name by walking ``app.routes``; its FULL-match branch tolerates
a missing ``.path``, but its PARTIAL-match branch reads ``route.path``
unconditionally and raised
``AttributeError: '_IncludedRouter' object has no attribute 'path'``. An
``_IncludedRouter`` PARTIAL-matches whenever the path is covered but the method
is not - which is precisely what a **CORS preflight ``OPTIONS``** (or any method
mismatch / 405) does. Because the instrumentation middleware wraps the app
*outside* FastAPI's exception handlers, this surfaced as an unhandled HTTP 500.

In production this took down every browser-initiated authenticated flow: the
SPA sends ``Authorization: Bearer`` headers, so the browser preflights those
calls with ``OPTIONS``; the preflight 500'd, so the real request was never sent
(profiles, log creation, the nearest-trigs list, ...). Plain unauthenticated
GETs FULL-match and kept working. (OTel 0.64b0 fixes this by flattening routers
before reading ``.path``.)

Why CI did not catch it
-----------------------
Instrumentation is only attached when ``settings.OTEL_ENABLED`` is true, which
is never the case under test. No test ever ran the app *instrumented*, so the
entire OpenTelemetry ASGI middleware - the only place the crash lives - was
unexercised.

This test closes that gap: it attaches the real instrumentation to an app that
uses ``include_router`` (exactly like the production API) and asserts a request
to an included route does not 500.
"""

from fastapi import APIRouter, FastAPI
from fastapi.testclient import TestClient

from api.core.telemetry import instrument_fastapi_app


def _build_instrumented_app() -> FastAPI:
    app = FastAPI()

    router = APIRouter()

    @router.get("/me")
    def me():  # pragma: no cover - exercised via TestClient
        return {"ok": True}

    # include_router is what puts an `_IncludedRouter` (no `.path`) into
    # app.routes on FastAPI >= 0.138 - the object that broke OTel's span-name
    # resolution in production.
    app.include_router(router, prefix="/users")

    instrument_fastapi_app(app)
    return app


def test_instrumented_included_route_get_succeeds():
    """A normal GET to an included route works (FULL match)."""
    app = _build_instrumented_app()
    with TestClient(app) as client:
        response = client.get("/users/me")

    assert response.status_code == 200, response.text
    assert response.json() == {"ok": True}


def test_instrumented_method_mismatch_returns_405_not_500():
    """A method mismatch (the shape of a CORS preflight) PARTIAL-matches the
    ``_IncludedRouter``. The instrumentation must resolve the span name without
    crashing, so the client sees a clean 405 rather than an unhandled 500.

    This is the exact path that 500'd in production under
    ``opentelemetry-instrumentation-fastapi==0.63b1``.
    """
    app = _build_instrumented_app()
    with TestClient(app) as client:
        response = client.post("/users/me")  # only GET is defined

    assert response.status_code == 405, response.text
