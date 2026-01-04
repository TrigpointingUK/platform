#!/usr/bin/env python3
"""
Find database users with orphaned auth0_user_id values.

This script:
1. Queries database for users with non-null auth0_user_id (pattern: 'auth0|%')
2. For each user, checks if the Auth0 user actually exists
3. Reports users where the Auth0 user is missing

Usage:
    python scripts/find_orphaned_auth0_users.py --dry-run --limit 100
    python scripts/find_orphaned_auth0_users.py --fetch-from-secrets
    python scripts/find_orphaned_auth0_users.py --output orphaned_users.json

Environment variables required:
    AUTH0_TENANT_DOMAIN, AUTH0_M2M_CLIENT_ID, AUTH0_M2M_CLIENT_SECRET
    AUTH0_CONNECTION (optional, defaults to tuk-users)

Database connection:
    Uses AWS Secrets Manager (fastapi-production-postgres-credentials) with
    localhost:5433 tunnel by default.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus

try:
    import boto3
except ImportError:
    boto3 = None  # type: ignore

import redis
import requests
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add parent directory to path so we can import from api
sys.path.insert(0, str(Path(__file__).parent.parent))


class Auth0TokenManager:
    """Manage Auth0 Management API tokens with Redis caching."""

    def __init__(
        self,
        tenant_domain: str,
        client_id: str,
        client_secret: str,
        redis_url: str = "redis://127.0.0.1:6379",
    ):
        self.tenant_domain = tenant_domain
        self.client_id = client_id
        self.client_secret = client_secret
        self.management_api_audience = f"https://{tenant_domain}/api/v2/"
        self.token_cache_key = f"auth0:mgmt_token:{tenant_domain}"

        # Connect to Redis
        self._redis_client = None
        try:
            self._redis_client = redis.from_url(
                redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
            )
            self._redis_client.ping()
            print(f"✓ Connected to Redis at {redis_url}")
        except Exception as e:
            print(f"⚠️  Redis connection failed: {e}")
            print("   Will request new token from Auth0")

    def get_token(self) -> Optional[str]:
        """Get a valid access token, from cache or by requesting new one."""
        # Try Redis cache first
        if self._redis_client:
            try:
                cached_data = self._redis_client.get(self.token_cache_key)
                if cached_data:
                    token_data = json.loads(cached_data)
                    expires_at = datetime.fromisoformat(token_data["expires_at"])
                    if datetime.now(timezone.utc) < expires_at:
                        print(f"✓ Using cached token from Redis (expires {expires_at})")
                        return token_data["token"]
                    else:
                        print("   Cached token expired, requesting new one...")
            except Exception as e:
                print(f"⚠️  Redis read error: {e}")

        # Request new token
        return self._request_new_token()

    def _request_new_token(self) -> Optional[str]:
        """Request a new token from Auth0."""
        print(f"🔐 Requesting new token from {self.tenant_domain}...")

        token_url = f"https://{self.tenant_domain}/oauth/token"
        payload = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "audience": self.management_api_audience,
            "grant_type": "client_credentials",
        }

        try:
            response = requests.post(token_url, json=payload, timeout=10)
            response.raise_for_status()

            token_data = response.json()
            access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)

            print(f"✓ Obtained new token (expires in {expires_in}s)")
            return access_token

        except requests.exceptions.RequestException as e:
            print(f"❌ Failed to get token: {e}")
            if hasattr(e, "response") and e.response is not None:
                print(f"   Response: {e.response.text}")
            return None


class Auth0UserChecker:
    """Check if users exist in Auth0."""

    def __init__(self, tenant_domain: str, access_token: str, connection: str):
        self.tenant_domain = tenant_domain
        self.access_token = access_token
        self.connection = connection
        self.base_url = f"https://{tenant_domain}/api/v2"

    def user_exists(self, auth0_user_id: str) -> bool:
        """Check if a user exists in Auth0 by their ID."""
        url = f"{self.base_url}/users/{auth0_user_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                # User exists - optionally check connection matches
                user_data = response.json()
                identities = user_data.get("identities", [])
                if identities:
                    user_connection = identities[0].get("connection")
                    if user_connection != self.connection:
                        # User exists but in different connection
                        return True  # Still consider it as "exists"
                return True
            elif response.status_code == 404:
                return False
            else:
                print(f"      ⚠️  Unexpected response {response.status_code}: {response.text[:100]}")
                return True  # Assume exists on error to avoid false positives

        except requests.exceptions.RequestException as e:
            print(f"      ⚠️  Request error: {e}")
            return True  # Assume exists on error


def get_aws_secret(secret_name: str, region: str = "eu-west-1") -> Dict:
    """Retrieve a secret from AWS Secrets Manager."""
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def get_database_connection(
    fetch_from_secrets: bool = True,
    secret_name: str = "fastapi-production-postgres-credentials",
    region: str = "eu-west-1",
    db_host: str = "localhost",
    db_port: int = 5433,
) -> Session:
    """
    Create a database connection.

    By default uses localhost:5433 (tunnel) with credentials from AWS Secrets Manager.
    """
    if fetch_from_secrets:
        print(f"📡 Fetching database credentials from AWS Secrets Manager: {secret_name}")
        secret = get_aws_secret(secret_name, region)
        db_user = secret["username"]
        db_password = secret["password"]
        db_name = secret["dbname"]
    else:
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME")

        if not all([db_user, db_password, db_name]):
            raise ValueError(
                "Missing database environment variables. "
                "Set DB_USER, DB_PASSWORD, DB_NAME "
                "or use --fetch-from-secrets"
            )

    db_url = (
        f"postgresql+psycopg2://{quote_plus(db_user)}:{quote_plus(db_password)}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    print(f"📊 Connecting to database: {db_host}:{db_port}/{db_name}")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def get_users_with_auth0_id(db: Session, limit: int, offset: int = 0) -> List[Dict]:
    """Query database for users with auth0_user_id LIKE 'auth0|%'."""
    query = text(
        """
        SELECT id, name, email, auth0_user_id
        FROM "user"
        WHERE auth0_user_id LIKE 'auth0|%'
        ORDER BY id
        LIMIT :limit OFFSET :offset
        """
    )

    result = db.execute(query, {"limit": limit, "offset": offset})
    users = []
    for row in result:
        users.append({
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "auth0_user_id": row[3],
        })

    return users


def count_users_with_auth0_id(db: Session) -> int:
    """Count total users with auth0_user_id LIKE 'auth0|%'."""
    query = text(
        """
        SELECT COUNT(*) FROM "user" WHERE auth0_user_id LIKE 'auth0|%'
        """
    )
    result = db.execute(query)
    return result.scalar()


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Find database users with orphaned auth0_user_id values"
    )
    parser.add_argument(
        "--limit", type=int, default=100,
        help="Number of users to check per batch (default: 100)",
    )
    parser.add_argument(
        "--max-total", type=int, default=None,
        help="Maximum total users to check (default: all)",
    )
    parser.add_argument(
        "--fetch-from-secrets", action="store_true", default=True,
        help="Fetch database credentials from AWS Secrets Manager (default: True)",
    )
    parser.add_argument(
        "--no-fetch-from-secrets", action="store_false", dest="fetch_from_secrets",
        help="Use environment variables for database credentials",
    )
    parser.add_argument(
        "--secret-name", type=str, default="fastapi-production-postgres-credentials",
        help="AWS Secrets Manager secret name for database credentials",
    )
    parser.add_argument(
        "--region", default="eu-west-1",
        help="AWS region (default: eu-west-1)",
    )
    parser.add_argument(
        "--db-host", type=str, default="localhost",
        help="Database host (default: localhost for tunnel)",
    )
    parser.add_argument(
        "--db-port", type=int, default=5433,
        help="Database port (default: 5433 for tunnel)",
    )
    parser.add_argument(
        "--redis-url", type=str, default="redis://127.0.0.1:6379",
        help="Redis URL for Auth0 token caching (default: redis://127.0.0.1:6379)",
    )
    parser.add_argument(
        "--auth0-connection", type=str, default="tuk-users",
        help="Auth0 connection name (default: tuk-users)",
    )
    parser.add_argument(
        "--output", type=str,
        help="Output file for orphaned user data (JSON format)",
    )
    parser.add_argument(
        "--rate-limit", type=float, default=1.0,
        help="Delay between Auth0 API calls in seconds (default: 1.0)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("FIND ORPHANED AUTH0 USER IDS")
    print("=" * 80)
    print(f"Database: {args.db_host}:{args.db_port}")
    print(f"Secret: {args.secret_name}")
    print(f"Auth0 connection: {args.auth0_connection}")
    print(f"Batch size: {args.limit}")
    print(f"Max total: {args.max_total or 'all'}")
    print("=" * 80)

    # Get Auth0 credentials from environment
    auth0_tenant = os.getenv("AUTH0_TENANT_DOMAIN")
    auth0_client_id = os.getenv("AUTH0_M2M_CLIENT_ID")
    auth0_client_secret = os.getenv("AUTH0_M2M_CLIENT_SECRET")
    auth0_connection = os.getenv("AUTH0_CONNECTION", args.auth0_connection)

    if not all([auth0_tenant, auth0_client_id, auth0_client_secret]):
        print("\n❌ Missing Auth0 environment variables!")
        print("   Required: AUTH0_TENANT_DOMAIN, AUTH0_M2M_CLIENT_ID, AUTH0_M2M_CLIENT_SECRET")
        print("\n   Tip: source your .env file or export the variables")
        sys.exit(1)

    print(f"\n🔐 Auth0 tenant: {auth0_tenant}")
    print(f"   Connection: {auth0_connection}")

    orphaned_users = []

    try:
        # Get Auth0 token
        token_manager = Auth0TokenManager(
            tenant_domain=auth0_tenant,
            client_id=auth0_client_id,
            client_secret=auth0_client_secret,
            redis_url=args.redis_url,
        )

        access_token = token_manager.get_token()
        if not access_token:
            print("\n❌ Failed to obtain Auth0 access token")
            sys.exit(1)

        # Create Auth0 user checker
        auth0_checker = Auth0UserChecker(
            tenant_domain=auth0_tenant,
            access_token=access_token,
            connection=auth0_connection,
        )

        # Connect to database
        db = get_database_connection(
            fetch_from_secrets=args.fetch_from_secrets,
            secret_name=args.secret_name,
            region=args.region,
            db_host=args.db_host,
            db_port=args.db_port,
        )

        total_count = count_users_with_auth0_id(db)
        print(f"\n📊 Total users with auth0_user_id: {total_count}")

        max_to_check = args.max_total if args.max_total else total_count
        offset = 0
        checked = 0

        while checked < max_to_check:
            batch_size = min(args.limit, max_to_check - checked)
            users = get_users_with_auth0_id(db, batch_size, offset)

            if not users:
                break

            print(f"\n🔍 Checking batch: users {offset + 1}-{offset + len(users)}...")

            for user in users:
                auth0_id = user["auth0_user_id"]
                exists = auth0_checker.user_exists(auth0_id)

                if not exists:
                    orphaned_users.append(user)
                    print(f"   ⚠️  ORPHANED: User {user['id']} ({user['name']}) - {auth0_id}")
                else:
                    print(f"   ✓ OK: User {user['id']} ({user['name']})")

                checked += 1

                # Rate limiting - Auth0 has API limits
                time.sleep(args.rate_limit)

            offset += len(users)

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Total users checked: {checked}")
        print(f"Orphaned users found: {len(orphaned_users)}")

        if orphaned_users:
            print("\nOrphaned users:")
            for user in orphaned_users:
                print(f"  - ID {user['id']}: {user['name']} ({user['email']}) -> {user['auth0_user_id']}")

            if args.output:
                with open(args.output, "w") as f:
                    json.dump(orphaned_users, f, indent=2)
                print(f"\n✓ Wrote orphaned users to {args.output}")

        print("=" * 80)

        db.close()

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

