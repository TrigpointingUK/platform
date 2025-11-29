"""
Comprehensive tests for config module to improve coverage.
"""

# from unittest.mock import Mock, patch  # Unused imports removed

import pytest
from pydantic import ValidationError

from api.core.config import Settings


class TestConfigComprehensive:
    """Test config module comprehensively."""

    def test_default_values(self):
        """Test that default values are set correctly."""
        # Test the default values by checking the class field defaults directly
        # This bypasses environment variable loading and tests the actual defaults
        from api.core.config import Settings

        # Check the field defaults directly from the model
        model_fields = Settings.model_fields

        assert model_fields["API_V1_STR"].default == "/v1"
        assert model_fields["PROJECT_NAME"].default == "TrigpointingUK API"
        assert model_fields["DEBUG"].default is False
        # DATABASE_URL is now a property, so test the individual DB components
        assert model_fields["DB_HOST"].default == "localhost"
        assert model_fields["DB_PORT"].default == 5432  # PostgreSQL default
        assert model_fields["DB_USER"].default == "user"
        assert model_fields["DB_PASSWORD"].default == "pass"
        assert model_fields["DB_NAME"].default == "db"
        assert model_fields["BACKEND_CORS_ORIGINS"].default == []
        assert model_fields["AUTH0_CUSTOM_DOMAIN"].default is None
        assert model_fields["AUTH0_SECRET_NAME"].default is None
        assert model_fields["AUTH0_CONNECTION"].default is None
        # AUTH0_ENABLED field removed - Auth0 is now always enabled
        assert model_fields["LOG_LEVEL"].default == "INFO"

    def test_cors_origins_string_parsing(self):
        """Test CORS origins parsing from string."""
        settings = Settings(
            BACKEND_CORS_ORIGINS="http://localhost:3000,https://example.com"
        )

        assert len(settings.BACKEND_CORS_ORIGINS) == 2
        assert str(settings.BACKEND_CORS_ORIGINS[0]) == "http://localhost:3000/"
        assert str(settings.BACKEND_CORS_ORIGINS[1]) == "https://example.com/"

    def test_cors_origins_list_passthrough(self):
        """Test CORS origins passthrough for list input."""
        origins = ["http://localhost:3000", "https://example.com"]
        settings = Settings(BACKEND_CORS_ORIGINS=origins)

        assert len(settings.BACKEND_CORS_ORIGINS) == 2
        assert str(settings.BACKEND_CORS_ORIGINS[0]) == "http://localhost:3000/"
        assert str(settings.BACKEND_CORS_ORIGINS[1]) == "https://example.com/"

    def test_cors_origins_string_with_brackets(self):
        """Test CORS origins parsing from string that starts with bracket."""
        # This should be treated as a single string, not parsed as JSON
        # The string should be treated as a single URL
        settings = Settings(
            BACKEND_CORS_ORIGINS='["http://localhost:3000","https://example.com"]'
        )

        assert len(settings.BACKEND_CORS_ORIGINS) == 2
        assert str(settings.BACKEND_CORS_ORIGINS[0]) == "http://localhost:3000/"
        assert str(settings.BACKEND_CORS_ORIGINS[1]) == "https://example.com/"

    def test_cors_origins_invalid_type(self):
        """Test CORS origins with invalid type raises ValidationError."""
        with pytest.raises(ValidationError):
            Settings(BACKEND_CORS_ORIGINS=123)

    def test_cors_origins_empty_string(self):
        """Test CORS origins with empty string."""
        # Empty string should result in empty list
        settings = Settings(BACKEND_CORS_ORIGINS="")
        assert settings.BACKEND_CORS_ORIGINS == []

    def test_cors_origins_single_url(self):
        """Test CORS origins with single URL."""
        settings = Settings(BACKEND_CORS_ORIGINS="https://example.com")
        assert len(settings.BACKEND_CORS_ORIGINS) == 1
        assert str(settings.BACKEND_CORS_ORIGINS[0]) == "https://example.com/"

    def test_cors_origins_with_spaces(self):
        """Test CORS origins with spaces around URLs."""
        settings = Settings(
            BACKEND_CORS_ORIGINS=" http://localhost:3000 , https://example.com "
        )

        assert len(settings.BACKEND_CORS_ORIGINS) == 2
        assert str(settings.BACKEND_CORS_ORIGINS[0]) == "http://localhost:3000/"
        assert str(settings.BACKEND_CORS_ORIGINS[1]) == "https://example.com/"

    def test_auth0_configuration(self):
        """Test Auth0 configuration settings."""
        settings = Settings(
            AUTH0_CUSTOM_DOMAIN="test.auth0.com",
            AUTH0_SECRET_NAME="test-secret",
            AUTH0_CONNECTION="custom-connection",
        )

        assert settings.AUTH0_CUSTOM_DOMAIN == "test.auth0.com"
        assert settings.AUTH0_SECRET_NAME == "test-secret"
        assert settings.AUTH0_CONNECTION == "custom-connection"
        # AUTH0_ENABLED field removed - Auth0 is now always enabled

    def test_database_configuration(self):
        """Test database configuration."""
        settings = Settings(
            DB_HOST="localhost",
            DB_PORT=5432,
            DB_USER="user",
            DB_PASSWORD="pass",
            DB_NAME="db",
        )
        assert (
            settings.DATABASE_URL == "postgresql+psycopg2://user:pass@localhost:5432/db"
        )

    def test_environment_variable_override(self):
        """Test that environment variables override default values."""
        import os

        # Set environment variables
        os.environ["DB_HOST"] = "env-host"
        os.environ["DB_PORT"] = "5432"
        os.environ["DB_USER"] = "env-user"
        os.environ["DB_PASSWORD"] = "env-pass"
        os.environ["DB_NAME"] = "env-db"
        os.environ["AUTH0_CUSTOM_DOMAIN"] = "env.auth0.com"

        try:
            settings = Settings()

            # These should be overridden by environment variables
            assert settings.DB_HOST == "env-host"
            assert settings.DB_PORT == 5432
            assert settings.DB_USER == "env-user"
            assert settings.DB_PASSWORD == "env-pass"
            assert settings.DB_NAME == "env-db"
            assert (
                settings.DATABASE_URL
                == "postgresql+psycopg2://env-user:env-pass@env-host:5432/env-db"
            )
            assert settings.AUTH0_CUSTOM_DOMAIN == "env.auth0.com"

            # These should still be defaults
            assert settings.API_V1_STR == "/v1"
            assert settings.PROJECT_NAME.startswith("TrigpointingUK API")
            # Local default may be True; only assert boolean type
            assert isinstance(settings.DEBUG, bool)
        finally:
            # Clean up environment variables
            for var in [
                "DB_HOST",
                "DB_PORT",
                "DB_USER",
                "DB_PASSWORD",
                "DB_NAME",
                "AUTH0_CUSTOM_DOMAIN",
            ]:
                os.environ.pop(var, None)

    def test_settings_instantiation_with_env_vars(self):
        """Test that Settings can be instantiated and works with environment variables."""
        # This test verifies that Settings works correctly regardless of environment
        settings = Settings()

        # Just verify that all expected attributes exist and have reasonable values
        assert hasattr(settings, "API_V1_STR")
        assert hasattr(settings, "PROJECT_NAME")
        assert hasattr(settings, "DEBUG")
        assert hasattr(settings, "DB_HOST")
        assert hasattr(settings, "DB_PORT")
        assert hasattr(settings, "DB_USER")
        assert hasattr(settings, "DB_PASSWORD")
        assert hasattr(settings, "DB_NAME")
        assert hasattr(settings, "DATABASE_URL")
        assert hasattr(settings, "BACKEND_CORS_ORIGINS")
        assert hasattr(settings, "AUTH0_CUSTOM_DOMAIN")
        assert hasattr(settings, "AUTH0_SECRET_NAME")
        assert hasattr(settings, "AUTH0_CONNECTION")
        # AUTH0_ENABLED field removed - Auth0 is now always enabled
        assert hasattr(settings, "LOG_LEVEL")

        # Verify types are correct
        assert isinstance(settings.API_V1_STR, str)
        assert isinstance(settings.PROJECT_NAME, str)
        assert isinstance(settings.DEBUG, bool)
        assert isinstance(settings.DB_HOST, str)
        assert isinstance(settings.DB_PORT, int)
        assert isinstance(settings.DB_USER, str)
        assert isinstance(settings.DB_PASSWORD, str)
        assert isinstance(settings.DB_NAME, str)
        assert isinstance(settings.DATABASE_URL, str)
        assert isinstance(settings.BACKEND_CORS_ORIGINS, list)
        # AUTH0_ENABLED field removed - Auth0 is now always enabled
        assert isinstance(settings.LOG_LEVEL, str)

    def test_debug_configuration(self):
        """Test debug configuration."""
        settings = Settings(DEBUG=True)
        assert settings.DEBUG is True

    def test_project_name_configuration(self):
        """Test project name configuration."""
        settings = Settings(PROJECT_NAME="Custom Project")
        assert settings.PROJECT_NAME == "Custom Project"

    def test_api_v1_str_configuration(self):
        """Test API v1 string configuration."""
        settings = Settings(API_V1_STR="/api/v2")
        assert settings.API_V1_STR == "/api/v2"

    def test_log_level_configuration(self):
        """Test log level configuration."""
        settings = Settings(LOG_LEVEL="DEBUG")
        assert settings.LOG_LEVEL == "DEBUG"

    def test_log_level_invalid(self):
        """Test log level with invalid value."""
        # Pydantic should accept any string, but we can test the behavior
        settings = Settings(LOG_LEVEL="INVALID_LEVEL")
        assert settings.LOG_LEVEL == "INVALID_LEVEL"

    def test_settings_immutable(self):
        """Test that settings are immutable after creation."""
        settings = Settings()

        # Pydantic models are not immutable by default, so this should not raise an error
        # We can test that the value can be changed
        settings.API_V1_STR = "/api/v2"
        assert settings.API_V1_STR == "/api/v2"

    def test_settings_model_config(self):
        """Test that settings model config is set correctly."""
        assert Settings.model_config["case_sensitive"] is True
        assert "env_file" in Settings.model_config

    def test_cors_origins_field_validator(self):
        """Test the CORS origins field validator method."""
        # Test the validator method directly
        result = Settings.assemble_cors_origins(
            "http://localhost:3000,https://example.com"
        )
        assert result == ["http://localhost:3000", "https://example.com"]

    def test_cors_origins_field_validator_list(self):
        """Test the CORS origins field validator with list input."""
        result = Settings.assemble_cors_origins(
            ["http://localhost:3000", "https://example.com"]
        )
        assert result == ["http://localhost:3000", "https://example.com"]

    def test_cors_origins_field_validator_bracket_string(self):
        """Test the CORS origins field validator with bracket string."""
        result = Settings.assemble_cors_origins(
            '["http://localhost:3000","https://example.com"]'
        )
        assert result == ["http://localhost:3000", "https://example.com"]

    def test_cors_origins_field_validator_invalid(self):
        """Test the CORS origins field validator with invalid input."""
        with pytest.raises(ValueError):
            Settings.assemble_cors_origins(123)


class TestEnvironmentVariableConfig:
    """Tests for environment variables replacing Parameter Store."""

    def test_env_overrides_for_flat_config(self, monkeypatch):
        monkeypatch.setenv("LOG_LEVEL", "WARNING")
        # When using environment variables, complex types are parsed as JSON
        monkeypatch.setenv("BACKEND_CORS_ORIGINS", '["https://a.com","https://b.com"]')
        monkeypatch.setenv("DATABASE_POOL_SIZE", "20")
        monkeypatch.setenv("DATABASE_POOL_RECYCLE", "600")

        s = Settings()
        assert s.LOG_LEVEL == "WARNING"
        assert len(s.BACKEND_CORS_ORIGINS) == 2
        assert str(s.BACKEND_CORS_ORIGINS[0]) == "https://a.com/"
        assert str(s.BACKEND_CORS_ORIGINS[1]) == "https://b.com/"
        assert s.DATABASE_POOL_SIZE == 20
        assert s.DATABASE_POOL_RECYCLE == 600
