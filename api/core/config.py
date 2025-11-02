"""
Core configuration settings for the FastAPI application.
"""

import json
import logging
from typing import List, Optional, Union

from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    API_V1_STR: str = "/v1"
    PROJECT_NAME: str = "TrigpointingUK API"
    ENVIRONMENT: str = "development"  # staging, production, development
    DEBUG: bool = False

    # Base URL for the API (used for logout redirects, etc.)
    FASTAPI_URL: str = "http://localhost:8000"

    # Database - constructed from individual components
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "user"
    DB_PASSWORD: str = "pass"
    DB_NAME: str = "db"

    # Database Pool Configuration
    DATABASE_POOL_SIZE: int = 5
    DATABASE_POOL_RECYCLE: int = 300

    @property
    def DATABASE_URL(self) -> str:
        """Construct DATABASE_URL from individual database components."""
        return f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []

    # Auth0 Configuration
    AUTH0_CUSTOM_DOMAIN: Optional[str] = (
        None  # User-facing domain (e.g., auth.trigpointing.me)
    )
    AUTH0_TENANT_DOMAIN: Optional[str] = (
        None  # Tenant domain for Management API (e.g., trigpointing-me.eu.auth0.com)
    )
    AUTH0_SECRET_NAME: Optional[str] = None
    AUTH0_CONNECTION: Optional[str] = None

    # Auth0 Client IDs
    AUTH0_SPA_CLIENT_ID: Optional[str] = None  # SPA client for Swagger OAuth2 (PKCE)
    AUTH0_M2M_CLIENT_ID: Optional[str] = (
        None  # M2M client for Management API and webhooks
    )
    AUTH0_M2M_CLIENT_SECRET: Optional[str] = None

    # Auth0 API Audience
    # This is your API identifier - used for both:
    # - Validating tokens from your API clients (users)
    # - Validating M2M tokens from Auth0 Actions (webhooks)
    AUTH0_API_AUDIENCE: Optional[str] = None  # e.g., "https://api.trigpointing.me/"

    # Logging Configuration
    LOG_LEVEL: str = "INFO"

    # Profiling Configuration
    PROFILING_ENABLED: bool = False  # Enable profiling middleware
    PROFILING_DEFAULT_FORMAT: str = "html"  # Options: "html" or "speedscope"

    # Orientation model (ONNX) configuration
    ORIENTATION_MODEL_ENABLED: bool = False
    ORIENTATION_MODEL_PATH: Optional[str] = None
    ORIENTATION_MODEL_THRESHOLD: float = 0.65

    # Photo upload configuration
    PHOTOS_SERVER_ID: int = 1  # Default to S3 server (server.id = 1)
    PHOTOS_S3_BUCKET: str = "trigpointinguk-photos"
    MAX_IMAGE_SIZE: int = 20 * 1024 * 1024  # 20MB
    MAX_IMAGE_DIMENSION: int = 4000
    THUMBNAIL_SIZE: int = 120

    # Redis/ElastiCache Configuration
    REDIS_URL: Optional[str] = None  # e.g., redis://host:6379
    CACHE_ENABLED: bool = True  # Enable/disable caching globally

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        """Parse CORS origins from environment variable."""
        if isinstance(v, str):
            if not v:
                return []
            if v.startswith("["):
                try:
                    data = json.loads(v)
                except json.JSONDecodeError as exc:  # pragma: no cover - guard rail
                    logger.warning(
                        "Failed to decode BACKEND_CORS_ORIGINS JSON: %s", exc
                    )
                    return []
                if isinstance(data, list):
                    return [str(i).strip() for i in data]
                return data
            return [i.strip() for i in v.split(",") if i.strip()]
        if isinstance(v, list):
            return v
        raise ValueError(v)

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env")


settings = Settings()
