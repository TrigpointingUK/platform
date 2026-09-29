"""Tests for merging duplicate Vary headers (api/core/vary.py)."""

import pytest
from fastapi import FastAPI, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from api.core.vary import VaryDedupeMiddleware, merge_vary


@pytest.mark.parametrize(
    "values, expected",
    [
        (["Origin"], "Origin"),
        (["Origin, Origin"], "Origin"),
        (["Origin", "Origin"], "Origin"),
        (["Accept-Encoding, Origin", "origin"], "Accept-Encoding, Origin"),
        (["Origin", "Accept-Encoding"], "Origin, Accept-Encoding"),
        ([" , Origin ,"], "Origin"),
    ],
)
def test_merge_vary(values, expected):
    assert merge_vary(values) == expected


@pytest.fixture
def client():
    """App set up like main.py: CORS with explicit origins, dedupe outside it."""
    app = FastAPI()

    @app.get("/tile")
    def tile():
        return Response(content=b"x", headers={"Vary": "Origin"})

    @app.get("/plain")
    def plain():
        return Response(content=b"x")

    app.add_middleware(CORSMiddleware, allow_origins=["https://trigpointing.uk"])
    app.add_middleware(VaryDedupeMiddleware)
    return TestClient(app)


def test_endpoint_vary_not_duplicated_for_allowed_origin(client):
    response = client.get("/tile", headers={"Origin": "https://trigpointing.uk"})
    assert response.headers.get_list("vary") == ["Origin"]
    assert response.headers["access-control-allow-origin"] == "https://trigpointing.uk"


def test_endpoint_vary_not_duplicated_without_origin(client):
    response = client.get("/tile")
    assert response.headers.get_list("vary") == ["Origin"]


def test_response_without_vary_left_alone(client):
    response = client.get("/plain")
    # Whatever CORSMiddleware adds (depends on the Starlette version), once only
    assert [v for v in response.headers.get_list("vary") if v] in ([], ["Origin"])
