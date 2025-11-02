"""
Tests for custom OpenAPI configuration.
"""

from fastapi.testclient import TestClient

from api.core.config import settings


def test_openapi_schema_has_security_schemes(client: TestClient):
    """Test that OpenAPI schema includes OAuth2 security scheme only."""
    response = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "components" in schema
    assert "securitySchemes" in schema["components"]
    assert "OAuth2" in schema["components"]["securitySchemes"]
    # Ensure no Bearer schemes are present
    for k in schema["components"]["securitySchemes"].keys():
        assert not k.lower().startswith("bearer")


def test_openapi_schema_has_security_requirements(client: TestClient):
    """Test that OpenAPI schema includes security requirements on protected endpoints."""
    response = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "paths" in schema

    # Check that protected endpoints have security requirements
    protected_endpoints = [
        f"{settings.API_V1_STR}/legacy/username-duplicates",
        f"{settings.API_V1_STR}/legacy/email-duplicates",
        f"{settings.API_V1_STR}/users/me",
    ]

    for endpoint_path in protected_endpoints:
        if endpoint_path in schema["paths"]:
            for method in ["get", "post", "put", "delete", "patch"]:
                if method in schema["paths"][endpoint_path]:
                    endpoint = schema["paths"][endpoint_path][method]
                    assert "security" in endpoint
                    if endpoint_path.startswith(f"{settings.API_V1_STR}/legacy/"):
                        assert endpoint["security"] == [
                            {"OAuth2": ["openid", "profile", "api:admin"]}
                        ]
                    else:
                        assert endpoint["security"] == [{"OAuth2": []}]


def test_openapi_schema_public_endpoints_no_security(client: TestClient):
    """Test that public endpoints don't have security requirements."""
    response = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert "paths" in schema

    # Check that truly public endpoints don't have security requirements
    public_endpoints = [
        "/health",
        # Note: /v1/legacy/login is excluded because it's a POST that requires authentication
    ]

    for endpoint_path in public_endpoints:
        if endpoint_path in schema["paths"]:
            for method in ["get", "post", "put", "delete", "patch"]:
                if method in schema["paths"][endpoint_path]:
                    endpoint = schema["paths"][endpoint_path][method]
                    # Public endpoints should not have security requirements
                    assert "security" not in endpoint


def test_openapi_schema_metadata(client: TestClient):
    """Test that OpenAPI schema has correct metadata."""
    response = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response.status_code == 200

    schema = response.json()
    assert schema["info"]["title"].startswith("TrigpointingUK API")
    assert schema["info"]["version"] == "1.0.0"
    assert "TrigpointingUK API" in schema["info"]["description"]


def test_openapi_schema_cached(client: TestClient):
    """Test that OpenAPI schema is properly cached."""
    # First request
    response1 = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response1.status_code == 200

    # Second request should return the same cached schema
    response2 = client.get(f"{settings.API_V1_STR}/openapi.json")
    assert response2.status_code == 200

    # Both responses should be identical
    assert response1.json() == response2.json()
