"""
Auth0 Management API service for user synchronization.

This service handles:
- Obtaining Auth0 Management API access tokens
- Creating new Auth0 users
- Updating existing Auth0 users
- Graceful error handling with detailed logging
"""

import json
import secrets
import ssl
import string
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

import redis
import requests
from redis.exceptions import RedisError

from api.core.config import settings
from api.core.logging import get_logger
from api.utils.username_sanitizer import sanitize_username_for_auth0

logger = get_logger(__name__)


class Auth0EmailAlreadyExistsError(Exception):
    """Raised when attempting to create an Auth0 user with an email that already exists."""

    def __init__(self, email: str):
        super().__init__(f"Auth0 user already exists with email '{email}'")
        self.email = email


class Auth0UserCreationFailedError(Exception):
    """Raised when Auth0 user creation fails for an unknown reason."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.details = details or {}


class Auth0Service:
    """Service for interacting with Auth0 Management API."""

    def __init__(self):
        """Initialize the Auth0 service."""
        self.tenant_domain = settings.AUTH0_TENANT_DOMAIN
        self.custom_domain = settings.AUTH0_CUSTOM_DOMAIN
        self.connection = settings.AUTH0_CONNECTION
        self._access_token = None
        self._token_expires_at = None
        self._last_error = None  # Store last error response for caller inspection

        if not self.tenant_domain:
            logger.error("AUTH0_TENANT_DOMAIN is required but not configured")
            raise ValueError("AUTH0_TENANT_DOMAIN is required but not configured")

        if not self.connection:
            logger.error("AUTH0_CONNECTION is required but not configured")
            raise ValueError("AUTH0_CONNECTION is required but not configured")

        # Construct Management API audience from tenant domain
        self.management_api_audience = f"https://{self.tenant_domain}/api/v2/"
        logger.debug(f"Management API audience: {self.management_api_audience}")

        # ElastiCache/Redis connection for token caching
        self._redis_client = None
        if settings.REDIS_URL:
            try:
                # ElastiCache Serverless requires TLS
                # Convert redis:// to rediss:// for serverless endpoints
                redis_url = settings.REDIS_URL
                if "serverless" in redis_url and redis_url.startswith("redis://"):
                    redis_url = redis_url.replace("redis://", "rediss://", 1)

                # Log parsed endpoint (without credentials)
                try:
                    parsed = urlparse(redis_url)
                    logger.info(
                        json.dumps(
                            {
                                "event": "auth0_token_cache_initialised",
                                "redis_scheme": parsed.scheme,
                                "redis_host": parsed.hostname,
                                "redis_port": parsed.port,
                                "redis_db": parsed.path.lstrip("/") or "0",
                            }
                        )
                    )
                except Exception as e:
                    logger.debug(
                        json.dumps(
                            {
                                "event": "auth0_token_cache_initialise_parse_failed",
                                "error": str(e),
                            }
                        )
                    )

                # Build connection with or without TLS depending on scheme
                if parsed.scheme == "rediss":
                    # Create permissive SSL context to avoid verification issues on AWS serverless
                    ssl_context = ssl.create_default_context()
                    ssl_context.check_hostname = False
                    ssl_context.verify_mode = ssl.CERT_NONE

                    self._redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=10,
                        socket_timeout=10,
                        retry_on_timeout=True,
                        ssl=True,
                        ssl_context=ssl_context,
                    )
                else:
                    self._redis_client = redis.from_url(
                        redis_url,
                        decode_responses=True,
                        socket_connect_timeout=10,
                        socket_timeout=10,
                        retry_on_timeout=True,
                    )
                # Test connection
                pong = self._redis_client.ping()
                logger.info(
                    json.dumps(
                        {
                            "event": "auth0_redis_ping",
                            "pong": bool(pong),
                        }
                    )
                )
                logger.info(
                    json.dumps(
                        {
                            "event": "auth0_redis_connected",
                            "connected": True,
                        }
                    )
                )
            except Exception as e:
                logger.warning(
                    json.dumps(
                        {
                            "event": "auth0_redis_connect_failed",
                            "error": str(e),
                            "note": "Token caching disabled, using in-memory cache only.",
                        }
                    )
                )
                self._redis_client = None
        else:
            logger.info(
                json.dumps(
                    {
                        "event": "auth0_token_cache_disabled",
                        "reason": "REDIS_URL not configured",
                    }
                )
            )

        self.token_cache_key = f"auth0:mgmt_token:{self.tenant_domain}"
        self._password_alphabet = string.ascii_letters + string.digits

    def _get_auth0_credentials(self) -> Optional[Dict[str, str]]:
        """
        Retrieve Auth0 credentials from environment variables.

        Returns:
            Dictionary containing Auth0 credentials or None if failed
        """

        try:
            # Get credentials for Management API (M2M)
            client_id = settings.AUTH0_M2M_CLIENT_ID
            client_secret = settings.AUTH0_M2M_CLIENT_SECRET
            domain = settings.AUTH0_TENANT_DOMAIN

            if not client_id or not client_secret:
                log_data = {
                    "event": "auth0_credentials_missing",
                    "client_id_present": bool(client_id),
                    "client_secret_present": bool(client_secret),
                    "domain_present": bool(domain),
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.error(json.dumps(log_data))
                return None

            auth0_credentials = {
                "client_id": client_id,
                "client_secret": client_secret,
                "domain": domain or "",
            }

            log_data = {
                "event": "auth0_credentials_retrieved",
                "source": "environment_variables",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.debug(json.dumps(log_data))
            return auth0_credentials

        except Exception as e:
            log_data = {
                "event": "auth0_credentials_retrieval_failed",
                "error_type": "UnexpectedError",
                "error_message": str(e),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))
            return None

    def _get_access_token(self) -> Optional[str]:
        """
        Get a valid Auth0 Management API access token.

        Checks ElastiCache first (shared across all ECS tasks),
        then in-memory cache, then requests new token.

        Returns:
            Access token string or None if failed
        """

        # Try ElastiCache first (shared across all tasks)
        logger.info(
            json.dumps(
                {
                    "event": "auth0_token_cache_check",
                    "source": "redis",
                    "cache_key": self.token_cache_key,
                }
            )
        )
        if self._redis_client:
            try:
                cached_data = self._redis_client.get(self.token_cache_key)
                if cached_data:
                    token_data = json.loads(cached_data)
                    expires_at = datetime.fromisoformat(token_data["expires_at"])
                    if datetime.now(timezone.utc) < expires_at:
                        logger.info(
                            json.dumps(
                                {
                                    "event": "auth0_token_cache_hit",
                                    "source": "redis",
                                    "expires_at": expires_at.isoformat() + "Z",
                                }
                            )
                        )
                        return token_data["token"]
                logger.info(
                    json.dumps({"event": "auth0_token_cache_miss", "source": "redis"})
                )
            except (RedisError, json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to read token from ElastiCache: {e}")

        # Fall back to in-memory cache
        if (
            self._access_token
            and self._token_expires_at
            and datetime.now(timezone.utc) < self._token_expires_at
        ):
            logger.info(
                json.dumps(
                    {
                        "event": "auth0_token_cache_hit",
                        "source": "memory",
                        "expires_at": self._token_expires_at.isoformat() + "Z",
                    }
                )
            )
            return self._access_token

        # Request new token
        credentials = self._get_auth0_credentials()
        if not credentials:
            return None

        try:
            logger.info(json.dumps({"event": "auth0_access_token_requested"}))
            # Request access token from tenant domain (not custom domain)
            token_url = f"https://{self.tenant_domain}/oauth/token"
            payload = {
                "client_id": credentials["client_id"],
                "client_secret": credentials["client_secret"],
                "audience": self.management_api_audience,  # Use configured audience instead of secret
                "grant_type": "client_credentials",
            }

            response = requests.post(token_url, json=payload, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            self._access_token = token_data["access_token"]

            # Set expiration time (with 5 minute buffer)
            expires_in = token_data.get("expires_in", 3600)
            self._token_expires_at = datetime.now(timezone.utc) + timedelta(
                seconds=expires_in - 300
            )

            # Cache in ElastiCache (shared across all ECS tasks)
            if self._redis_client:
                try:
                    cache_data = {
                        "token": self._access_token,
                        "expires_at": self._token_expires_at.isoformat(),
                    }
                    ttl = int(
                        (
                            self._token_expires_at - datetime.now(timezone.utc)
                        ).total_seconds()
                    )
                    self._redis_client.setex(
                        self.token_cache_key, ttl, json.dumps(cache_data)
                    )
                    logger.info(
                        json.dumps(
                            {
                                "event": "auth0_token_cached_in_elasticache",
                                "cache_key": self.token_cache_key,
                                "expires_in_seconds": ttl,
                            }
                        )
                    )
                except RedisError as e:
                    logger.warning(f"Failed to cache token in ElastiCache: {e}")

            log_data = {
                "event": "auth0_access_token_refreshed",
                "tenant_domain": self.tenant_domain,
                "expires_in_seconds": expires_in,
                "expires_at": self._token_expires_at.isoformat() + "Z",
            }
            logger.info(json.dumps(log_data))
            return self._access_token

        except requests.exceptions.RequestException as e:
            # Try to get response details if available
            response_details = {}
            if hasattr(e, "response") and e.response is not None:
                response_details = {
                    "status_code": e.response.status_code,
                    "response_text": e.response.text,
                    "response_headers": dict(e.response.headers),
                }
                try:
                    response_details["error_response"] = e.response.json()
                except (ValueError, KeyError):
                    pass

            log_data = {
                "event": "auth0_access_token_failed",
                "error_type": "RequestException",
                "error_message": str(e),
                "tenant_domain": self.tenant_domain,
                "token_url": f"https://{self.tenant_domain}/oauth/token",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **response_details,
            }
            logger.error(json.dumps(log_data))
            return None
        except Exception as e:
            log_data = {
                "event": "auth0_access_token_failed",
                "error_type": "UnexpectedError",
                "error_message": str(e),
                "tenant_domain": self.tenant_domain,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))
            return None

    def _make_auth0_request(
        self, method: str, endpoint: str, data: Optional[Dict] = None
    ) -> Optional[Dict]:
        """
        Make a request to the Auth0 Management API.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.)
            endpoint: API endpoint (without domain)
            data: Request data for POST/PATCH requests

        Returns:
            Response data as dictionary or None if failed
        """

        access_token = self._get_access_token()
        if not access_token:
            return None

        try:
            # Use tenant domain for Management API calls, not custom domain
            url = f"https://{self.tenant_domain}/api/v2/{endpoint}"
            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json",
            }

            # Log API call start
            logger.info(
                json.dumps(
                    {
                        "event": "auth0_api_request_started",
                        "method": method,
                        "endpoint": endpoint,
                        "url": url,
                    }
                )
            )

            response = requests.request(
                method=method, url=url, headers=headers, json=data, timeout=10
            )

            # Log successful requests
            if response.status_code in (200, 201, 202, 204):
                self._last_error = None  # Clear any previous error
                log_data = {
                    "event": "auth0_api_request_success",
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "url": url,
                }
                logger.info(json.dumps(log_data))
                if response.status_code == 204 or not response.content:
                    return {}
                try:
                    return response.json()
                except (ValueError, json.JSONDecodeError):
                    return {}
            else:
                # Log failed requests with detailed error information
                try:
                    error_response = response.json()
                except (ValueError, KeyError):
                    error_response = {"raw_response": response.text}

                # Store error for caller inspection
                self._last_error = {
                    "status_code": response.status_code,
                    "error_response": error_response,
                }

                log_data = {
                    "event": "auth0_api_request_failed",
                    "method": method,
                    "endpoint": endpoint,
                    "status_code": response.status_code,
                    "url": url,
                    "error_response": error_response,
                    "response_headers": dict(response.headers),
                }
                logger.error(json.dumps(log_data))
                return None

        except requests.exceptions.RequestException as e:
            # Try to get response details if available
            response_details = {}
            if hasattr(e, "response") and e.response is not None:
                response_details = {
                    "status_code": e.response.status_code,
                    "response_text": e.response.text,
                    "response_headers": dict(e.response.headers),
                }
                try:
                    response_details["error_response"] = e.response.json()
                    # Store error for caller inspection
                    self._last_error = {
                        "status_code": e.response.status_code,
                        "error_response": response_details["error_response"],
                    }
                except (ValueError, KeyError):
                    pass

            log_data = {
                "event": "auth0_api_request_failed",
                "error_type": "RequestException",
                "error_message": str(e),
                "method": method,
                "endpoint": endpoint,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                **response_details,
            }
            logger.error(json.dumps(log_data))
            return None
        except Exception as e:
            self._last_error = None  # Clear error for unexpected exceptions
            log_data = {
                "event": "auth0_api_request_failed",
                "error_type": "UnexpectedError",
                "error_message": str(e),
                "method": method,
                "endpoint": endpoint,
                "url": url,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))
            return None

    def find_user_by_nickname_or_name(self, nickname: str) -> Optional[Dict]:
        """
        Find a user by display identity (nickname/name) in Auth0.

        Args:
            nickname: Display name to search for

        Returns:
            User data dictionary or None if not found
        """

        # Use exact match on nickname first, then name
        sanitized_nickname = sanitize_username_for_auth0(nickname)

        # Try nickname
        endpoint = f'users?q=nickname:"{sanitized_nickname}"&search_engine=v3'
        log_data = {
            "event": "auth0_user_search_by_nickname_started",
            "original_nickname": nickname,
            "sanitized_nickname": sanitized_nickname,
            "endpoint": endpoint,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.debug(json.dumps(log_data))

        response = self._make_auth0_request("GET", endpoint)

        if response and isinstance(response, list) and len(response) > 0:
            # Filter users by connection since Auth0 API doesn't support connection filtering in search
            filtered_users = self._filter_users_by_connection(response, self.connection)

            if filtered_users:
                log_data = {
                    "event": "auth0_user_found_by_nickname",
                    "original_nickname": nickname,
                    "sanitized_nickname": sanitized_nickname,
                    "auth0_user_id": filtered_users[0].get("user_id", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.info(json.dumps(log_data))
                return filtered_users[0]
            else:
                log_data = {
                    "event": "auth0_user_not_found_by_nickname_connection_filtered",
                    "original_nickname": nickname,
                    "sanitized_nickname": sanitized_nickname,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.debug(json.dumps(log_data))
                return None
        else:
            # Try name as fallback
            endpoint = f'users?q=name:"{sanitized_nickname}"&search_engine=v3'
            logger.debug(
                json.dumps(
                    {"event": "auth0_user_search_by_name_started", "endpoint": endpoint}
                )
            )
            response = self._make_auth0_request("GET", endpoint)
            if response and isinstance(response, list) and len(response) > 0:
                filtered_users = self._filter_users_by_connection(
                    response, self.connection
                )
                if filtered_users:
                    logger.info(
                        json.dumps(
                            {
                                "event": "auth0_user_found_by_name",
                                "auth0_user_id": filtered_users[0].get("user_id", ""),
                            }
                        )
                    )
                    return filtered_users[0]
            logger.debug(
                json.dumps(
                    {
                        "event": "auth0_user_not_found_by_nickname_or_name",
                        "nickname": nickname,
                    }
                )
            )
            return None

    def find_user_by_auth0_id(self, auth0_user_id: str) -> Optional[Dict]:
        """
        Find a user by Auth0 user ID.

        Args:
            auth0_user_id: Auth0 user ID to search for

        Returns:
            User data dictionary or None if not found
        """

        log_data = {
            "event": "auth0_find_user_by_id_called",
            "auth0_user_id": auth0_user_id,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.debug(json.dumps(log_data))

        # Get user by ID
        endpoint = f"users/{auth0_user_id}"
        response = self._make_auth0_request("GET", endpoint)

        if response:
            log_data = {
                "event": "auth0_user_found_by_id",
                "auth0_user_id": auth0_user_id,
                "nickname": response.get("nickname", ""),
                "email": response.get("email", ""),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.info(json.dumps(log_data))
            return response
        else:
            log_data = {
                "event": "auth0_user_not_found_by_id",
                "auth0_user_id": auth0_user_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.debug(json.dumps(log_data))
            return None

    def delete_user(self, user_id: str) -> bool:
        """
        Delete a user in Auth0.

        Args:
            user_id: Auth0 user ID to delete

        Returns:
            True if deletion succeeded, False otherwise.
        """

        response = self._make_auth0_request("DELETE", f"users/{user_id}")
        if response is not None:
            log_data = {
                "event": "auth0_user_deleted",
                "auth0_user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.info(json.dumps(log_data))
            return True

        log_data = {
            "event": "auth0_user_delete_failed",
            "auth0_user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.warning(json.dumps(log_data))
        return False

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        """
        Find a user by email in Auth0.

        Args:
            email: Email address to search for

        Returns:
            User data dictionary or None if not found
        """

        log_data = {
            "event": "auth0_find_user_by_email_called",
            "email": email,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.debug(json.dumps(log_data))

        # Search for user by email
        endpoint = f'users?q=email:"{email}"&search_engine=v3'
        response = self._make_auth0_request("GET", endpoint)

        if response and isinstance(response, list) and len(response) > 0:
            # Filter users by connection since Auth0 API doesn't support connection filtering in search
            filtered_users = self._filter_users_by_connection(response, self.connection)

            if filtered_users:
                log_data = {
                    "event": "auth0_user_found_by_email",
                    "email": email,
                    "auth0_user_id": filtered_users[0].get("user_id", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.info(json.dumps(log_data))
                return filtered_users[0]
            else:
                log_data = {
                    "event": "auth0_user_not_found_by_email_connection_filtered",
                    "email": email,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.debug(json.dumps(log_data))
                return None
        else:
            log_data = {
                "event": "auth0_user_not_found_by_email",
                "email": email,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.debug(json.dumps(log_data))
            return None

    def find_user_comprehensive(
        self, username: str, email: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Find a user using multiple search strategies.

        Args:
            username: Username to search for
            email: Email address to search for (optional)

        Returns:
            User data dictionary or None if not found
        """

        # Try username search first
        log_data = {
            "event": "auth0_comprehensive_search_username_attempt",
            "username": username,
            "connection": str(
                self.connection
            ),  # Convert to string to handle MagicMock in tests
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.debug(json.dumps(log_data))

        user = self.find_user_by_nickname_or_name(username)
        if user:
            log_data = {
                "event": "auth0_comprehensive_search_username_success",
                "username": username,
                "auth0_user_id": user.get("user_id", ""),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.debug(json.dumps(log_data))
            return user

        # If email provided, try email search
        if email:
            log_data = {
                "event": "auth0_comprehensive_search_email_attempt",
                "username": username,
                "email": email,
                "connection": str(
                    self.connection
                ),  # Convert to string to handle MagicMock in tests
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.debug(json.dumps(log_data))

            user = self.find_user_by_email(email)
            if user:
                log_data = {
                    "event": "auth0_comprehensive_search_email_success",
                    "username": username,
                    "email": email,
                    "auth0_user_id": user.get("user_id", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.debug(json.dumps(log_data))
                return user

        # Try searching by display name (nickname) without quotes (fallback)
        if not user:
            log_data = {
                "event": "auth0_comprehensive_search_fallback_attempt",
                "display_name": username,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.debug(json.dumps(log_data))
            try:
                endpoint = f"users?q=nickname:{username}&search_engine=v3"
                response = self._make_auth0_request("GET", endpoint)
                if response and isinstance(response, list) and len(response) > 0:
                    # Filter users by connection since Auth0 API doesn't support connection filtering in search
                    filtered_users = self._filter_users_by_connection(
                        response, self.connection
                    )

                    if filtered_users:
                        log_data = {
                            "event": "auth0_user_found_by_nickname_fallback",
                            "display_name": username,
                            "auth0_user_id": filtered_users[0].get("user_id", ""),
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        }
                        logger.info(json.dumps(log_data))
                        return filtered_users[0]
                    else:
                        log_data = {
                            "event": "auth0_user_not_found_by_nickname_fallback_connection_filtered",
                            "display_name": username,
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        }
                        logger.debug(json.dumps(log_data))
            except Exception as e:
                log_data = {
                    "event": "auth0_user_search_fallback_failed",
                    "display_name": username,
                    "error": str(e),
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.debug(json.dumps(log_data))

        log_data = {
            "event": "auth0_comprehensive_search_no_user_found",
            "username": username,
            "email": email or "",
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.info(json.dumps(log_data))
        return None

    def _filter_users_by_connection(
        self, users: List[Dict], connection: str
    ) -> List[Dict]:
        """
        Filter users by connection since Auth0 API doesn't support connection filtering in search.

        Args:
            users: List of user dictionaries from Auth0
            connection: Connection name to filter by

        Returns:
            Filtered list of users matching the connection
        """
        if not users:
            return []

        # Debug: Log the actual user data structure
        log_data = {
            "event": "auth0_users_debug_before_filtering",
            "total_users": len(users),
            "connection": str(
                connection
            ),  # Convert to string to handle MagicMock in tests
            "users_sample": [
                {
                    "user_id": user.get("user_id", ""),
                    "nickname": user.get("nickname", ""),
                    "email": user.get("email", ""),
                    "identities": user.get("identities", []),
                }
                for user in users[:3]  # Log first 3 users for debugging
            ],
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.info(json.dumps(log_data))

        filtered_users = [
            user
            for user in users
            if user.get("identities")
            and len(user.get("identities", [])) > 0
            and user.get("identities", [{}])[0].get("connection") == connection
        ]

        log_data = {
            "event": "auth0_users_filtered_by_connection",
            "total_users": len(users),
            "filtered_users": len(filtered_users),
            "connection": str(
                connection
            ),  # Convert to string to handle MagicMock in tests
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.debug(json.dumps(log_data))

        return filtered_users

    def create_user(
        self,
        username: str,
        email: Optional[str],
        name: str,
        password: str,
        user_id: int,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Create a new user in Auth0.

        Args:
            username: Username for the new user
            email: Email address (optional)
            name: Display name
            password: Password for the new user
            user_id: Database user ID to store in app_metadata
            firstname: First name for given_name field (optional)
            surname: Surname for family_name field (optional)

        Returns:
            Created user data dictionary or None if failed
        """

        # Sanitize username for Auth0 compatibility while preserving original as nickname
        sanitized_username = sanitize_username_for_auth0(username)

        user_data = {
            "connection": self.connection,
            # Use nickname as single display identity; mirror to name
            "nickname": username,
            "name": username,
            "password": password,
            "email_verified": False,
            "verify_email": False,
            "app_metadata": {
                "database_user_id": user_id,
                "original_username": username,
                "legacy_sync": datetime.now(timezone.utc).isoformat() + "Z",
            },
        }

        # Add profile fields if provided
        # Do not push real names; avoid given_name/family_name

        if email:
            user_data["email"] = email
            user_data["email_verified"] = True

        # Create safe user_data for logging (redact password)
        safe_user_data = user_data.copy()
        redacted_text = "***REDACTED***"
        safe_user_data["password"] = redacted_text

        log_data = {
            "event": "auth0_user_creation_api_call",
            "original_username": username,
            "sanitized_username": sanitized_username,
            "email": email or "",
            "connection": self.connection,
            "user_data": safe_user_data,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.debug(json.dumps(log_data))

        response = self._make_auth0_request("POST", "users", user_data)

        if response:
            log_data = {
                "event": "auth0_user_created",
                "original_username": username,
                "sanitized_username": sanitized_username,
                "email": email or "",
                "connection": self.connection,
                "user_data": safe_user_data,
                "auth0_user_id": response.get("user_id") or "",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.info(json.dumps(log_data))
        else:
            # Check if this is a user already exists error
            log_data = {
                "event": "auth0_user_creation_failed",
                "original_username": username,
                "sanitized_username": sanitized_username,
                "email": email or "",
                "connection": self.connection,
                "user_data": safe_user_data,  # Use the redacted version
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))

            # Try to find the existing user and return it instead of failing
            log_data = {
                "event": "auth0_user_creation_conflict_attempting_fallback",
                "username": username,
                "email": email or "",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.warning(json.dumps(log_data))

            # Try to find the existing user
            existing_user = self.find_user_comprehensive(username, email)
            if existing_user:
                log_data = {
                    "event": "auth0_user_creation_conflict_resolved",
                    "username": username,
                    "email": email or "",
                    "auth0_user_id": existing_user.get("user_id", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.info(json.dumps(log_data))
                return existing_user

        return response

    def _generate_random_password(self, length: int = 20) -> str:
        """
        Generate a random password consisting of alphanumeric characters.

        Args:
            length: Desired length of the generated password (default: 20)

        Returns:
            Randomly generated password string
        """

        return "".join(secrets.choice(self._password_alphabet) for _ in range(length))

    def create_user_for_admin_migration(
        self,
        username: str,
        email: str,
        legacy_user_id: int,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Create a new Auth0 database user as part of an admin-triggered migration.

        Steps:
            - Ensure the email is not already present in Auth0 (connection filtered)
            - Generate a temporary 20 character alphanumeric password
            - Create the Auth0 user with email_verified=false
            - Trigger a verification email via Management API

        Args:
            username: Legacy username (will be used for name and nickname fields)
            email: Email address to assign to the Auth0 user
            legacy_user_id: Database user ID for app_metadata linkage
            firstname: Optional first name (unused but accepted for parity)
            surname: Optional surname (unused but accepted for parity)

        Returns:
            Auth0 user dictionary returned by Management API

        Raises:
            Auth0EmailAlreadyExistsError: If an Auth0 user already exists with the email
            Auth0UserCreationFailedError: If Auth0 creation fails for other reasons
        """

        # Ensure we do not proceed if the email already exists in Auth0
        existing_user = self.find_user_by_email(email)
        if existing_user:
            logger.warning(
                json.dumps(
                    {
                        "event": "auth0_admin_migration_email_conflict",
                        "email": email,
                        "auth0_user_id": existing_user.get("user_id"),
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    }
                )
            )
            raise Auth0EmailAlreadyExistsError(email=email)

        password = self._generate_random_password()
        sanitized_username = sanitize_username_for_auth0(username)

        user_data = {
            "connection": self.connection,
            "nickname": username,
            "name": username,
            "email": email,
            "password": password,
            "email_verified": False,
            "verify_email": False,
            "app_metadata": {
                "database_user_id": legacy_user_id,
                "original_username": username,
                "legacy_sync": datetime.now(timezone.utc).isoformat() + "Z",
                "manual_migration": {
                    "trigger": "admin",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                },
            },
        }

        if firstname:
            user_data["given_name"] = firstname
        if surname:
            user_data["family_name"] = surname

        safe_user_data = user_data.copy()
        safe_user_data["password"] = "***REDACTED***"  # nosec B105

        logger.info(
            json.dumps(
                {
                    "event": "auth0_admin_migration_user_creation_started",
                    "username": username,
                    "sanitized_username": sanitized_username,
                    "email": email,
                    "legacy_user_id": legacy_user_id,
                    "user_data": safe_user_data,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
            )
        )

        response = self._make_auth0_request("POST", "users", user_data)
        if not response:
            details = self._last_error if isinstance(self._last_error, dict) else None
            logger.error(
                json.dumps(
                    {
                        "event": "auth0_admin_migration_user_creation_failed",
                        "username": username,
                        "email": email,
                        "legacy_user_id": legacy_user_id,
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        "details": details,
                    }
                )
            )
            raise Auth0UserCreationFailedError(
                message="Failed to create Auth0 user for admin migration",
                details=details,
            )

        auth0_user_id = response.get("user_id")
        logger.info(
            json.dumps(
                {
                    "event": "auth0_admin_migration_user_created",
                    "username": username,
                    "email": email,
                    "legacy_user_id": legacy_user_id,
                    "auth0_user_id": auth0_user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
            )
        )

        # Trigger verification email; warn if it fails but do not abort the migration
        if auth0_user_id:
            verification_success = self.send_verification_email(auth0_user_id)
            if not verification_success:
                logger.warning(
                    json.dumps(
                        {
                            "event": "auth0_admin_migration_verification_email_failed",
                            "username": username,
                            "email": email,
                            "auth0_user_id": auth0_user_id,
                            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                        }
                    )
                )

        return response

    def update_user_email(
        self, user_id: str, email: str, username: Optional[str] = None
    ) -> bool:
        """
        Update a user's email address in Auth0 and trigger verification email.
        Also ensures the 'name' field matches the 'nickname' field.

        Args:
            user_id: Auth0 user ID
            email: New email address
            username: Optional username to set for both name and nickname fields.
                     If not provided, the name will be synced to match the existing nickname.

        Returns:
            True if successful, False otherwise
        """

        # First, get the user's current nickname so we can sync name to it
        user = self._make_auth0_request("GET", f"users/{user_id}")
        if not user:
            log_data = {
                "event": "auth0_user_fetch_for_email_update_failed",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))
            return False

        # Use provided username or existing nickname
        nickname = username if username else user.get("nickname", "")

        # Update email and mark as unverified, also sync name to nickname
        user_data = {
            "email": email,
            "email_verified": False,
            "name": nickname,  # Set name to match nickname
        }

        # If username was provided, also update nickname
        if username:
            user_data["nickname"] = username

        response = self._make_auth0_request("PATCH", f"users/{user_id}", user_data)

        if not response:
            log_data = {
                "event": "auth0_user_email_update_failed",
                "user_id": user_id,
                "email": email,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))
            return False

        log_data = {
            "event": "auth0_user_email_updated",
            "user_id": user_id,
            "email": email,
            "email_verified": "false",
            "name_synced_to_nickname": nickname,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.info(json.dumps(log_data))

        # Step 2: Trigger verification email
        # Auth0 Management API: POST /api/v2/jobs/verification-email
        verification_data = {"user_id": user_id}
        verification_response = self._make_auth0_request(
            "POST", "jobs/verification-email", verification_data
        )

        if verification_response:
            log_data = {
                "event": "auth0_verification_email_sent",
                "user_id": user_id,
                "email": email,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.info(json.dumps(log_data))
        else:
            log_data = {
                "event": "auth0_verification_email_failed",
                "user_id": user_id,
                "email": email,
                "warning": "Email updated but verification email not sent",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.warning(json.dumps(log_data))
            # Don't fail the whole operation - email was updated successfully

        return True

    def update_user_password(self, user_id: str, password: str) -> bool:
        """
        Update a user's password in Auth0.

        Args:
            user_id: Auth0 user ID
            password: New password

        Returns:
            True if successful, False otherwise
        """

        response = self._make_auth0_request(
            "PATCH", f"users/{user_id}", {"password": password}
        )

        if response:
            logger.info(
                json.dumps(
                    {
                        "event": "auth0_user_password_updated",
                        "user_id": user_id,
                    }
                )
            )
            return True
        else:
            logger.error(
                json.dumps(
                    {
                        "event": "auth0_user_password_update_failed",
                        "user_id": user_id,
                    }
                )
            )
            return False

    def send_verification_email(self, user_id: str) -> bool:
        """
        Send verification email to a user.

        Args:
            user_id: Auth0 user ID

        Returns:
            True if successful, False otherwise
        """
        verification_data = {"user_id": user_id}
        verification_response = self._make_auth0_request(
            "POST", "jobs/verification-email", verification_data
        )

        if verification_response:
            log_data = {
                "event": "auth0_verification_email_sent",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.info(json.dumps(log_data))
            return True
        else:
            log_data = {
                "event": "auth0_verification_email_failed",
                "user_id": user_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.warning(json.dumps(log_data))
            return False

    def create_user_for_migration(
        self,
        email: str,
        name: str,
        legacy_user_id: int,
        original_username: str,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Create a new user in Auth0 for migration purposes.

        This creates a user without a password, with email_verified=false,
        suitable for triggering a password reset flow.

        Args:
            email: Email address
            name: Display name (username)
            legacy_user_id: Database user ID to store in app_metadata
            original_username: Original username to store in app_metadata
            firstname: First name for given_name field (optional)
            surname: Surname for family_name field (optional)

        Returns:
            Created user data dictionary or None if failed
        """
        # Generate a random password - user will need to reset it
        import secrets

        temp_password = secrets.token_urlsafe(32)

        user_data = {
            "connection": self.connection,
            "nickname": name,
            "name": name,
            "email": email,
            "password": temp_password,
            "email_verified": False,
            "verify_email": False,
            "app_metadata": {
                "legacy_user_id": legacy_user_id,
                "original_username": original_username,
                "migration_timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            },
        }

        # Add profile fields if provided
        if firstname:
            user_data["given_name"] = firstname
        if surname:
            user_data["family_name"] = surname

        # Create safe user_data for logging (redact password)
        safe_user_data = user_data.copy()
        redacted_text = "***REDACTED***"  # nosec B105
        safe_user_data["password"] = redacted_text

        log_data = {
            "event": "auth0_migration_user_creation_started",
            "email": email,
            "name": name,
            "legacy_user_id": legacy_user_id,
            "connection": self.connection,
            "user_data": safe_user_data,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.info(json.dumps(log_data))

        response = self._make_auth0_request("POST", "users", user_data)

        if response:
            log_data = {
                "event": "auth0_migration_user_created",
                "email": email,
                "name": name,
                "legacy_user_id": legacy_user_id,
                "auth0_user_id": response.get("user_id") or "",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.info(json.dumps(log_data))
        else:
            log_data = {
                "event": "auth0_migration_user_creation_failed",
                "email": email,
                "name": name,
                "legacy_user_id": legacy_user_id,
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))

        return response

    def update_user_app_metadata(self, user_id: str, metadata: Dict[str, Any]) -> bool:
        """
        Merge update to app_metadata for a user in Auth0.

        Args:
            user_id: Auth0 user ID
            metadata: Key-value pairs to set under app_metadata

        Returns:
            True if successful, False otherwise
        """

        body = {"app_metadata": metadata}
        response = self._make_auth0_request("PATCH", f"users/{user_id}", body)

        if response:
            logger.info(
                json.dumps(
                    {
                        "event": "auth0_user_app_metadata_updated",
                        "user_id": user_id,
                        "keys": list(metadata.keys()),
                    }
                )
            )
            return True
        else:
            logger.error(
                json.dumps(
                    {
                        "event": "auth0_user_app_metadata_update_failed",
                        "user_id": user_id,
                        "keys": list(metadata.keys()),
                    }
                )
            )
            return False

    def update_user_profile(
        self,
        user_id: str,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
        nickname: Optional[str] = None,
    ) -> bool:
        """
        Update a user's profile fields in Auth0.

        Args:
            user_id: Auth0 user ID
            firstname: First name for given_name field (optional)
            surname: Surname for family_name field (optional)
            nickname: Nickname field (optional)

        Returns:
            True if successful, False otherwise
        """

        # Only update display identity; avoid given_name/family_name
        user_data = {}
        if nickname is not None:
            user_data["nickname"] = nickname
            user_data["name"] = nickname

        if not user_data:
            # No fields to update
            return True

        response = self._make_auth0_request("PATCH", f"users/{user_id}", user_data)

        if response:
            log_data = {
                "event": "auth0_user_profile_updated",
                "user_id": user_id,
                "updated_fields": list(user_data.keys()),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.info(json.dumps(log_data))
            return True
        else:
            log_data = {
                "event": "auth0_user_profile_update_failed",
                "user_id": user_id,
                "updated_fields": list(user_data.keys()),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))
            return False

    def sync_user_to_auth0(
        self,
        username: str,
        email: Optional[str],
        name: str,
        password: str,
        user_id: int,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
    ) -> Optional[Dict]:
        """
        Sync a user to Auth0, creating or updating as needed.

        This is the main method that should be called after successful authentication.

        Args:
            username: Username from legacy database
            email: Email address from legacy database (optional)
            name: Display name from legacy database
            password: Password from legacy database
            user_id: User ID from legacy database
            firstname: First name from legacy database (optional)
            surname: Surname from legacy database (optional)

        Returns:
            Auth0 user data dictionary or None if sync failed
        """
        log_data = {
            "event": "auth0_sync_method_called",
            "username": username,
            "email": email or "",
            "user_id": user_id,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.info(json.dumps(log_data))

        log_data = {
            "event": "auth0_user_sync_started",
            "username": username,
            "email": email or "",
            "name": name,
            "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        }
        logger.debug(json.dumps(log_data))

        try:
            # Use comprehensive search to find user
            log_data = {
                "event": "auth0_user_search_started",
                "username": username,
                "email": email or "",
                "connection": str(self.connection),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.debug(json.dumps(log_data))

            auth0_user = self.find_user_comprehensive(username, email)

            log_data = {
                "event": "auth0_user_search_completed",
                "username": username,
                "email": email or "",
                "user_found": str(auth0_user is not None),
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.debug(json.dumps(log_data))

            if auth0_user:
                log_data = {
                    "event": "auth0_user_found_during_sync",
                    "username": username,
                    "email": email or "",
                    "auth0_user_id": auth0_user.get("user_id", ""),
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.info(json.dumps(log_data))
                # User exists, always push profile and password; check email change
                current_email = auth0_user.get("email")
                if email and current_email != email:
                    log_data = {
                        "event": "auth0_user_email_update_started",
                        "username": username,
                        "old_email": current_email or "",
                        "new_email": email or "",
                        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                    }
                    logger.info(json.dumps(log_data))
                    self.update_user_email(auth0_user["user_id"], email, username)
                    auth0_user["email"] = email

                # Always push display name (nickname/name)
                logger.info(
                    json.dumps(
                        {
                            "event": "auth0_user_profile_update_started",
                            "username": username,
                            "auth0_user_id": auth0_user["user_id"],
                        }
                    )
                )
                self.update_user_profile(auth0_user["user_id"], nickname=username)

                # Always push password
                logger.info(
                    json.dumps(
                        {
                            "event": "auth0_user_password_update_started",
                            "auth0_user_id": auth0_user["user_id"],
                        }
                    )
                )
                self.update_user_password(auth0_user["user_id"], password)

                # Update legacy_sync metadata timestamp
                self.update_user_app_metadata(
                    auth0_user["user_id"],
                    {"legacy_sync": datetime.now(timezone.utc).isoformat() + "Z"},
                )

                log_data = {
                    "event": "auth0_user_sync_completed_updated",
                    "username": username,
                    "auth0_user_id": auth0_user["user_id"],
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.info(json.dumps(log_data))
                return auth0_user
            else:
                # User doesn't exist, create new one
                log_data = {
                    "event": "auth0_user_not_found_during_sync",
                    "username": username,
                    "email": email or "",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.debug(json.dumps(log_data))

                log_data = {
                    "event": "auth0_user_creation_started",
                    "username": username,
                    "email": email or "",
                    "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
                }
                logger.debug(json.dumps(log_data))
                return self.create_user(
                    username, email, name, password, user_id, firstname, surname
                )

        except Exception as e:
            log_data = {
                "event": "auth0_user_sync_failed",
                "error_type": "UnexpectedError",
                "error_message": str(e),
                "username": username,
                "email": email or "",
                "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
            }
            logger.error(json.dumps(log_data))
            return None


class DisabledAuth0Service:
    """No-op Auth0 service used when configuration is missing.

    Provides the same interface as Auth0Service but performs no operations.
    """

    def find_user_by_nickname_or_name(self, nickname: str) -> Optional[Dict]:
        logger.debug(
            json.dumps(
                {
                    "event": "auth0_disabled_find_user_by_nickname_or_name",
                    "nickname": nickname,
                }
            )
        )
        return None

    def find_user_by_auth0_id(self, auth0_user_id: str) -> Optional[Dict]:
        logger.debug(
            json.dumps(
                {
                    "event": "auth0_disabled_find_user_by_auth0_id",
                    "auth0_user_id": auth0_user_id,
                }
            )
        )
        return None

    def find_user_by_email(self, email: str) -> Optional[Dict]:
        logger.debug(
            json.dumps(
                {
                    "event": "auth0_disabled_find_user_by_email",
                    "email": email,
                }
            )
        )
        return None

    def find_user_comprehensive(
        self, username: str, email: Optional[str] = None
    ) -> Optional[Dict]:
        logger.debug(
            json.dumps(
                {
                    "event": "auth0_disabled_find_user_comprehensive",
                    "display_name": username,
                    "email": email or "",
                }
            )
        )
        return None

    def create_user(
        self,
        username: str,
        email: Optional[str],
        name: str,
        password: str,
        user_id: int,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
    ) -> Optional[Dict]:
        logger.warning(
            json.dumps(
                {
                    "event": "auth0_disabled_create_user",
                    "display_name": username,
                    "email": email or "",
                }
            )
        )
        return None

    def update_user_email(
        self, user_id: str, email: str, username: Optional[str] = None
    ) -> bool:
        logger.warning(
            json.dumps(
                {
                    "event": "auth0_disabled_update_user_email",
                    "user_id": user_id,
                    "email": email,
                    "username": username,
                }
            )
        )
        return False

    def update_user_profile(
        self,
        user_id: str,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
        nickname: Optional[str] = None,
    ) -> bool:
        logger.warning(
            json.dumps(
                {
                    "event": "auth0_disabled_update_user_profile",
                    "user_id": user_id,
                }
            )
        )
        return False

    def sync_user_to_auth0(
        self,
        username: str,
        email: Optional[str],
        name: str,
        password: str,
        user_id: int,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
    ) -> Optional[Dict]:
        logger.info(
            json.dumps(
                {
                    "event": "auth0_disabled_sync_user_to_auth0",
                    "display_name": username,
                    "email": email or "",
                    "user_id": user_id,
                }
            )
        )
        return None

    def create_user_for_admin_migration(
        self,
        email: str,
        name: str,
        legacy_user_id: int,
        original_username: str,
        firstname: Optional[str] = None,
        surname: Optional[str] = None,
    ) -> Optional[Dict]:
        logger.warning(
            json.dumps(
                {
                    "event": "auth0_disabled_create_user_for_admin_migration",
                    "email": email,
                    "name": name,
                    "legacy_user_id": legacy_user_id,
                }
            )
        )
        return None

    def delete_user(self, user_id: str) -> bool:
        logger.warning(
            json.dumps(
                {
                    "event": "auth0_disabled_delete_user",
                    "auth0_user_id": user_id,
                }
            )
        )
        return False


# Global instance with safe fallback when not configured
auth0_service: Any
try:
    auth0_service = Auth0Service()
except Exception as e:  # pragma: no cover - depends on environment
    logger.warning(
        json.dumps(
            {
                "event": "auth0_service_initialization_failed",
                "error": str(e),
                "note": "Using DisabledAuth0Service",
            }
        )
    )
    auth0_service = DisabledAuth0Service()
