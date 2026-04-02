"""
Tests for core/security.py — Auth0 token validation, password hashing, scope extraction.
"""

import base64
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import jwt as pyjwt
import pytest

from api.core.security import (
    Auth0TokenValidator,
    extract_scopes,
    get_password_hash,
    verify_password,
)


def _make_rsa_key():
    """Generate a fresh RSA key pair for testing."""
    from cryptography.hazmat.primitives.asymmetric import rsa as rsa_mod

    private_key = rsa_mod.generate_private_key(public_exponent=65537, key_size=2048)
    return private_key


def _encode_int_b64url(value: int, length: int) -> str:
    return base64.urlsafe_b64encode(value.to_bytes(length, "big")).rstrip(b"=").decode()


class TestPasswordFunctions:
    def test_hash_and_verify(self):
        hashed = get_password_hash("testpassword")
        assert verify_password("testpassword", hashed) is True

    def test_wrong_password_fails(self):
        hashed = get_password_hash("correct")
        assert verify_password("wrong", hashed) is False


class TestExtractScopes:
    def test_extracts_from_scope_string(self):
        scopes = extract_scopes({"scope": "openid profile api:admin"})
        assert "api:admin" in scopes
        assert "openid" in scopes

    def test_extracts_from_permissions_list(self):
        scopes = extract_scopes({"permissions": ["api:admin", "api:write"]})
        assert "api:admin" in scopes
        assert "api:write" in scopes

    def test_combines_scope_and_permissions(self):
        scopes = extract_scopes(
            {
                "scope": "openid",
                "permissions": ["api:admin"],
            }
        )
        assert "openid" in scopes
        assert "api:admin" in scopes

    def test_returns_empty_for_empty_payload(self):
        assert extract_scopes({}) == set()

    def test_returns_empty_for_none(self):
        assert extract_scopes(None) == set()

    def test_ignores_non_string_scope(self):
        assert extract_scopes({"scope": 123}) == set()

    def test_ignores_non_list_permissions(self):
        assert extract_scopes({"permissions": "not_a_list"}) == set()


class TestAuth0TokenValidatorInit:
    @patch("api.core.security.settings")
    def test_creates_jwks_url_from_custom_domain(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()
        assert validator.jwks_url == "https://auth.example.com/.well-known/jwks.json"

    @patch("api.core.security.settings")
    def test_jwks_url_none_when_no_domain(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = None
        mock_settings.AUTH0_TENANT_DOMAIN = None
        mock_settings.AUTH0_API_AUDIENCE = None
        validator = Auth0TokenValidator()
        assert validator.jwks_url is None


class TestGetJWKS:
    @patch("api.core.security.settings")
    def test_returns_none_when_no_jwks_url(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = None
        mock_settings.AUTH0_TENANT_DOMAIN = None
        mock_settings.AUTH0_API_AUDIENCE = None
        validator = Auth0TokenValidator()
        assert validator._get_jwks() is None

    @patch("api.core.security.settings")
    def test_returns_cached_jwks(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()
        validator._jwks_cache = {"keys": []}
        validator._jwks_cache_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        result = validator._get_jwks()
        assert result == {"keys": []}

    @patch("api.core.security.settings")
    @patch("api.core.security.requests.get")
    def test_fetches_and_caches_jwks(self, mock_get, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        mock_response = MagicMock()
        mock_response.json.return_value = {"keys": [{"kid": "key1"}]}
        mock_get.return_value = mock_response

        validator = Auth0TokenValidator()
        result = validator._get_jwks()
        assert result == {"keys": [{"kid": "key1"}]}
        assert validator._jwks_cache is not None

    @patch("api.core.security.settings")
    @patch("api.core.security.requests.get")
    def test_returns_none_on_network_error(self, mock_get, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        mock_get.side_effect = Exception("Network error")

        validator = Auth0TokenValidator()
        assert validator._get_jwks() is None


class TestJwkToPublicKey:
    @patch("api.core.security.settings")
    def test_converts_rsa_jwk(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()

        private_key = _make_rsa_key()
        public_numbers = private_key.public_key().public_numbers()
        n_bytes = public_numbers.n.to_bytes(256, "big")
        e_bytes = public_numbers.e.to_bytes(3, "big")

        jwk = {
            "kty": "RSA",
            "n": base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode(),
            "e": base64.urlsafe_b64encode(e_bytes).rstrip(b"=").decode(),
        }
        result = validator._jwk_to_public_key(jwk)
        assert result is not None

    @patch("api.core.security.settings")
    def test_returns_none_on_invalid_jwk(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()
        result = validator._jwk_to_public_key({"kty": "RSA", "n": "bad", "e": "bad"})
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_jwk_for_non_rsa(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()
        jwk = {"kty": "EC", "x": "abc", "y": "def"}
        result = validator._jwk_to_public_key(jwk)
        assert result == jwk


class TestValidateAuth0Token:
    @patch("api.core.security.settings")
    def test_raises_when_no_custom_domain(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = None
        mock_settings.AUTH0_TENANT_DOMAIN = None
        mock_settings.AUTH0_API_AUDIENCE = None
        validator = Auth0TokenValidator()
        with pytest.raises(ValueError, match="AUTH0_CUSTOM_DOMAIN"):
            validator.validate_auth0_token("some.token.here")

    @patch("api.core.security.settings")
    def test_returns_none_when_no_audience(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = None
        validator = Auth0TokenValidator()
        result = validator.validate_auth0_token("some.token.here")
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_when_jwks_fails(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(return_value=None)
        result = validator.validate_auth0_token("some.token.here")
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_for_invalid_token_header(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(return_value={"keys": []})
        result = validator.validate_auth0_token("not-a-valid-jwt")
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_when_kid_not_found(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"

        private_key = _make_rsa_key()
        token = pyjwt.encode(
            {
                "sub": "auth0|123",
                "aud": "https://api.example.com",
                "iss": "https://auth.example.com/",
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "unknown_kid"},
        )
        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(return_value={"keys": [{"kid": "other_kid"}]})
        result = validator.validate_auth0_token(token)
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_for_expired_token(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"

        private_key = _make_rsa_key()
        public_key = private_key.public_key()
        public_numbers = public_key.public_numbers()
        n_bytes = public_numbers.n.to_bytes(256, "big")
        e_bytes = public_numbers.e.to_bytes(3, "big")

        token = pyjwt.encode(
            {
                "sub": "auth0|123",
                "aud": "https://api.example.com",
                "iss": "https://auth.example.com/",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test_kid"},
        )

        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(
            return_value={
                "keys": [
                    {
                        "kid": "test_kid",
                        "kty": "RSA",
                        "n": base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode(),
                        "e": base64.urlsafe_b64encode(e_bytes).rstrip(b"=").decode(),
                    }
                ]
            }
        )
        result = validator.validate_auth0_token(token)
        assert result is None


class TestValidateM2MToken:
    @patch("api.core.security.settings")
    def test_returns_none_when_no_custom_domain(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = None
        mock_settings.AUTH0_TENANT_DOMAIN = None
        mock_settings.AUTH0_API_AUDIENCE = None
        validator = Auth0TokenValidator()
        result = validator.validate_m2m_token("some.token.here")
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_when_no_audience(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = None
        validator = Auth0TokenValidator()
        result = validator.validate_m2m_token("some.token.here")
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_when_jwks_unavailable(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(return_value=None)
        result = validator.validate_m2m_token("some.token")
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_for_invalid_header(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"
        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(return_value={"keys": []})
        result = validator.validate_m2m_token("not-valid")
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_when_kid_not_found(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"

        private_key = _make_rsa_key()
        token = pyjwt.encode(
            {"sub": "client_id", "aud": "https://api.example.com"},
            private_key,
            algorithm="RS256",
            headers={"kid": "missing"},
        )
        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(return_value={"keys": [{"kid": "other"}]})
        result = validator.validate_m2m_token(token)
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_for_expired_m2m_token(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"

        private_key = _make_rsa_key()
        public_numbers = private_key.public_key().public_numbers()
        n_bytes = public_numbers.n.to_bytes(256, "big")
        e_bytes = public_numbers.e.to_bytes(3, "big")

        token = pyjwt.encode(
            {
                "sub": "client",
                "aud": "https://api.example.com",
                "iss": "https://tenant.auth0.com/",
                "exp": datetime.now(timezone.utc) - timedelta(hours=1),
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test_m2m_kid"},
        )

        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(
            return_value={
                "keys": [
                    {
                        "kid": "test_m2m_kid",
                        "kty": "RSA",
                        "n": base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode(),
                        "e": base64.urlsafe_b64encode(e_bytes).rstrip(b"=").decode(),
                    }
                ]
            }
        )
        result = validator.validate_m2m_token(token)
        assert result is None

    @patch("api.core.security.settings")
    def test_returns_none_for_invalid_audience(self, mock_settings):
        mock_settings.AUTH0_CUSTOM_DOMAIN = "auth.example.com"
        mock_settings.AUTH0_TENANT_DOMAIN = "tenant.auth0.com"
        mock_settings.AUTH0_API_AUDIENCE = "https://api.example.com"

        private_key = _make_rsa_key()
        public_numbers = private_key.public_key().public_numbers()
        n_bytes = public_numbers.n.to_bytes(256, "big")
        e_bytes = public_numbers.e.to_bytes(3, "big")

        token = pyjwt.encode(
            {
                "sub": "client",
                "aud": "https://wrong-audience.com",
                "iss": "https://tenant.auth0.com/",
                "exp": datetime.now(timezone.utc) + timedelta(hours=1),
            },
            private_key,
            algorithm="RS256",
            headers={"kid": "test_aud_kid"},
        )

        validator = Auth0TokenValidator()
        validator._get_jwks = MagicMock(
            return_value={
                "keys": [
                    {
                        "kid": "test_aud_kid",
                        "kty": "RSA",
                        "n": base64.urlsafe_b64encode(n_bytes).rstrip(b"=").decode(),
                        "e": base64.urlsafe_b64encode(e_bytes).rstrip(b"=").decode(),
                    }
                ]
            }
        )
        result = validator.validate_m2m_token(token)
        assert result is None
