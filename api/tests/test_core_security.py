"""
Comprehensive tests for core security functions.
"""

from api.core.security import (
    extract_scopes,
    get_password_hash,
    verify_password,
)


class TestSecurityFunctions:
    """Test cases for core security functions."""

    def test_extract_scopes_valid_token(self):
        """Test extracting scopes from a valid JWT token."""
        token_payload = {
            "scope": "api:read api:write api:admin",
            "token_type": "auth0",
        }
        scopes = extract_scopes(token_payload)
        assert scopes == {"api:read", "api:write", "api:admin"}

    def test_extract_scopes_empty_scope(self):
        """Test extracting scopes from token with empty scope."""
        token_payload = {"scope": "", "token_type": "auth0"}
        scopes = extract_scopes(token_payload)
        assert scopes == set()

    def test_extract_scopes_no_scope_key(self):
        """Test extracting scopes from token without scope key."""
        token_payload = {"token_type": "auth0"}
        scopes = extract_scopes(token_payload)
        assert scopes == set()

    def test_extract_scopes_whitespace_scope(self):
        """Test extracting scopes with whitespace."""
        token_payload = {
            "scope": "  api:read   api:write  api:admin  ",
            "token_type": "auth0",
        }
        scopes = extract_scopes(token_payload)
        assert scopes == {"api:read", "api:write", "api:admin"}

    def test_verify_password_valid(self):
        """Test password verification with valid password."""
        plain_password = "testpassword123"
        hashed_password = get_password_hash(plain_password)
        assert verify_password(plain_password, hashed_password)
        assert not verify_password("wrongpassword", hashed_password)

    def test_verify_password_invalid(self):
        """Test password verification with invalid password."""
        plain_password = "testpassword123"
        hashed_password = get_password_hash(plain_password)
        assert not verify_password("wrongpassword", hashed_password)

    def test_get_password_hash(self):
        """Test password hashing function."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify the original password
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_get_password_hash_consistency(self):
        """Test that password hashing is consistent."""
        password = "testpassword123"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)

        # Hashes should be different due to salt
        assert hash1 != hash2
        # But both should verify the original password
        assert verify_password(password, hash1)
        assert verify_password(password, hash2)

    def test_password_verification_edge_cases(self):
        """Test password verification with realistic edge cases for legacy system."""
        # Empty password
        empty_hash = get_password_hash("")
        assert verify_password("", empty_hash)

        # Reasonably long password (within bcrypt limits for legacy compatibility)
        long_password = "a" * 50  # Reduced from 1000 to stay within legacy limits
        long_hash = get_password_hash(long_password)
        assert verify_password(long_password, long_hash)

        # Password with special characters
        special_password = "!@#$%^&*()_+{}[]|\\:;\"'<>?,./"
        special_hash = get_password_hash(special_password)
        assert verify_password(special_password, special_hash)

    def test_legacy_password_behavior_preserved(self):
        """
        CRITICAL: This test ensures legacy password behavior is never modified.

        These functions MUST preserve exact legacy behavior for migration purposes.
        If this test fails, it means someone has "improved" the password functions
        and broken compatibility with existing legacy data.

        DO NOT modify this test or the password functions to make this pass.
        The legacy behavior is intentionally preserved as-is.
        """
        # Test that the functions exist and work with basic passwords
        password = "legacy_password_123"
        hashed = get_password_hash(password)

        # Verify the hash format is standard bcrypt (starts with $2b$)
        assert hashed.startswith("$2b$"), "Legacy hash format must be preserved"

        # Verify verification works
        assert verify_password(password, hashed), "Legacy verification must work"
        assert not verify_password(
            "wrong_password", hashed
        ), "Legacy verification must reject wrong passwords"

        # Verify that the functions are simple and don't have complex logic
        import inspect

        verify_source = inspect.getsource(verify_password)
        hash_source = inspect.getsource(get_password_hash)

        # These functions should be simple - no truncation, no compatibility code logic
        assert (
            "truncat" not in verify_source.lower()
        ), "verify_password must not truncate passwords"
        assert (
            "truncat" not in hash_source.lower()
        ), "get_password_hash must not truncate passwords"
        assert (
            "COMPAT_PREFIX" not in verify_source
        ), "verify_password must not have compatibility code"
        assert (
            "COMPAT_PREFIX" not in hash_source
        ), "get_password_hash must not have compatibility code"
        assert (
            "_normalise_password" not in verify_source
        ), "verify_password must not normalize passwords"
        assert (
            "_normalise_password" not in hash_source
        ), "get_password_hash must not normalize passwords"
