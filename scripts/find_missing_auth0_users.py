#!/usr/bin/env python3
"""
Find mismatches between database users and Auth0 export.

This script compares database users against an Auth0 JSON export file to find:
1. Users that exist in the database but are missing from Auth0
2. Users that exist in Auth0 but are missing from the database

This is much faster than querying the Auth0 API for each user individually.

Usage:
    python scripts/find_missing_auth0_users.py
    python scripts/find_missing_auth0_users.py --auth0-file ~/Downloads/trigpointing.json.gz
    python scripts/find_missing_auth0_users.py --output missing_users.json

The Auth0 export file should be a gzip-compressed file containing one JSON object
per line, with at minimum an "Id" field (auth0 user ID) and "Name" field.

Database connection:
    Uses AWS Secrets Manager (fastapi-production-postgres-credentials) with
    localhost:5433 tunnel by default.
"""

import argparse
import gzip
import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple
from urllib.parse import quote_plus

try:
    import boto3
except ImportError:
    boto3 = None  # type: ignore

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add parent directory to path so we can import from api
sys.path.insert(0, str(Path(__file__).parent.parent))


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


def get_all_users_with_auth0_id(db: Session) -> List[Dict]:
    """
    Query database for all users with auth0_user_id.

    Returns list of dicts with 'name' and 'auth0_user_id', ordered by auth0_user_id.
    """
    query = text(
        """
        SELECT name, auth0_user_id
        FROM "user"
        WHERE auth0_user_id IS NOT NULL
          AND auth0_user_id LIKE 'auth0|%'
        ORDER BY auth0_user_id
        """
    )

    result = db.execute(query)
    users = []
    for row in result:
        users.append({
            "name": row[0],
            "auth0_user_id": row[1],
        })

    return users


def load_auth0_export(file_path: Path) -> Tuple[Set[str], Dict[str, Dict]]:
    """
    Load Auth0 users from a gzip-compressed JSON lines file.

    Each line should be a JSON object with an "Id" field containing the auth0 user ID,
    and a "Name" field containing the user's name.

    Returns:
        Tuple of (set of auth0 user IDs, dict mapping auth0_id to user info dict)
    """
    auth0_ids: Set[str] = set()
    auth0_users: Dict[str, Dict] = {}  # id -> {name, legacy_user_id}
    line_count = 0
    error_count = 0

    print(f"📂 Loading Auth0 export from: {file_path}")

    open_func = gzip.open if str(file_path).endswith('.gz') else open
    mode = 'rt' if str(file_path).endswith('.gz') else 'r'

    with open_func(file_path, mode, encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue

            line_count += 1
            try:
                record = json.loads(line)
                auth0_id = record.get("Id")
                if auth0_id:
                    auth0_ids.add(auth0_id)
                    app_metadata = record.get("AppMetadata", {}) or {}
                    auth0_users[auth0_id] = {
                        "name": record.get("Name", "(unknown)"),
                        "legacy_user_id": app_metadata.get("legacy_user_id"),
                    }
            except json.JSONDecodeError as e:
                error_count += 1
                if error_count <= 5:
                    print(f"   ⚠️  JSON parse error on line {line_count}: {e}")

    print(f"   ✓ Loaded {len(auth0_ids)} unique Auth0 user IDs from {line_count} lines")
    if error_count > 0:
        print(f"   ⚠️  {error_count} lines had JSON parse errors")

    return auth0_ids, auth0_users


def find_missing_from_auth0(db_users: List[Dict], auth0_ids: Set[str]) -> List[Dict]:
    """
    Find users that exist in the database but not in the Auth0 export.

    Args:
        db_users: List of user dicts from database with 'name' and 'auth0_user_id'
        auth0_ids: Set of auth0 user IDs from the export file

    Returns:
        List of user dicts that are missing from Auth0
    """
    missing = []
    for user in db_users:
        if user["auth0_user_id"] not in auth0_ids:
            missing.append(user)
    return missing


def find_missing_from_database(
    auth0_ids: Set[str],
    auth0_users: Dict[str, Dict],
    db_auth0_ids: Set[str],
) -> List[Dict]:
    """
    Find users that exist in Auth0 but not in the database.

    Args:
        auth0_ids: Set of auth0 user IDs from the export file
        auth0_users: Dict mapping auth0_id to user info dict
        db_auth0_ids: Set of auth0 user IDs from the database

    Returns:
        List of user dicts that are missing from database
    """
    missing = []
    for auth0_id in auth0_ids:
        if auth0_id not in db_auth0_ids:
            user_info = auth0_users.get(auth0_id, {})
            missing.append({
                "name": user_info.get("name", "(unknown)") if isinstance(user_info, dict) else "(unknown)",
                "auth0_user_id": auth0_id,
                "legacy_user_id": user_info.get("legacy_user_id") if isinstance(user_info, dict) else None,
            })
    # Sort by auth0_user_id for consistent output
    missing.sort(key=lambda x: x["auth0_user_id"])
    return missing


def main():
    """Main function."""
    default_auth0_file = Path.home() / "Downloads" / "trigpointing.json.gz"

    parser = argparse.ArgumentParser(
        description="Find database users missing from Auth0 export"
    )
    parser.add_argument(
        "--auth0-file", type=str, default=str(default_auth0_file),
        help=f"Path to gzip-compressed Auth0 export JSON file (default: {default_auth0_file})",
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
        "--output", type=str,
        help="Output file for missing user data (JSON format)",
    )

    args = parser.parse_args()

    auth0_file = Path(args.auth0_file)

    print("=" * 80)
    print("FIND MISSING AUTH0 USERS")
    print("=" * 80)
    print(f"Database: {args.db_host}:{args.db_port}")
    print(f"Secret: {args.secret_name}")
    print(f"Auth0 export file: {auth0_file}")
    print("=" * 80)

    # Check Auth0 export file exists
    if not auth0_file.exists():
        print(f"\n❌ Auth0 export file not found: {auth0_file}")
        print("   Please provide the correct path with --auth0-file")
        sys.exit(1)

    try:
        # Load Auth0 export into memory
        print("\n📥 Loading Auth0 export file...")
        auth0_ids, auth0_users = load_auth0_export(auth0_file)

        if not auth0_ids:
            print("\n❌ No Auth0 user IDs found in export file")
            sys.exit(1)

        # Connect to database and load all users
        print("\n📥 Loading users from database...")
        db = get_database_connection(
            fetch_from_secrets=args.fetch_from_secrets,
            secret_name=args.secret_name,
            region=args.region,
            db_host=args.db_host,
            db_port=args.db_port,
        )

        db_users = get_all_users_with_auth0_id(db)
        print(f"   ✓ Loaded {len(db_users)} users with auth0_user_id from database")

        db.close()

        # Build set of database auth0_user_ids for reverse lookup
        db_auth0_ids = {user["auth0_user_id"] for user in db_users}

        # Compare datasets
        print("\n🔍 Comparing datasets...")
        missing_from_auth0 = find_missing_from_auth0(db_users, auth0_ids)
        missing_from_db = find_missing_from_database(auth0_ids, auth0_users, db_auth0_ids)

        # Summary
        print("\n" + "=" * 80)
        print("SUMMARY")
        print("=" * 80)
        print(f"Auth0 export users: {len(auth0_ids)}")
        print(f"Database users with auth0_user_id: {len(db_users)}")
        print(f"In database but missing from Auth0: {len(missing_from_auth0)}")
        print(f"In Auth0 but missing from database: {len(missing_from_db)}")

        if missing_from_auth0:
            print("\n" + "-" * 40)
            print("Users in DATABASE but MISSING from Auth0 export:")
            print("-" * 40)
            for user in missing_from_auth0:
                print(f"  - {user['name']}: {user['auth0_user_id']}")

        if missing_from_db:
            print("\n" + "-" * 40)
            print("Users in AUTH0 but MISSING from database:")
            print("-" * 40)
            for user in missing_from_db:
                legacy_id = user.get('legacy_user_id')
                legacy_str = f" (legacy_user_id: {legacy_id})" if legacy_id else ""
                print(f"  - {user['name']}: {user['auth0_user_id']}{legacy_str}")

        if not missing_from_auth0 and not missing_from_db:
            print("\n✓ All users match between database and Auth0 export")

        if args.output and (missing_from_auth0 or missing_from_db):
            output_data = {
                "missing_from_auth0": missing_from_auth0,
                "missing_from_database": missing_from_db,
            }
            with open(args.output, "w") as f:
                json.dump(output_data, f, indent=2)
            print(f"\n✓ Wrote results to {args.output}")

        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

