#!/usr/bin/env python3
"""
Fix Auth0 users with ERROR- prefixed auth0_user_id values.

This script:
1. Queries database for users with auth0_user_id LIKE 'ERROR-%'
2. For each user:
   - Searches Auth0 for existing user with matching email
   - Deletes the incorrect Auth0 user if found
   - Creates new Auth0 user with proper configuration
   - Updates database with new Auth0 user ID

Usage:
    python scripts/fix_error_auth0_users.py --limit 10
    python scripts/fix_error_auth0_users.py --limit 100 --environment production
    python scripts/fix_error_auth0_users.py --dry-run --limit 5

Environment variables required:
    AWS_DEFAULT_REGION (or AWS_REGION)
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (or use --fetch-from-secrets)
    AUTH0_TENANT_DOMAIN, AUTH0_M2M_CLIENT_ID, AUTH0_M2M_CLIENT_SECRET, AUTH0_CONNECTION
"""

import argparse
import json
import os
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import quote_plus

import boto3
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

# Add parent directory to path so we can import from api
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.crud.user import update_user_auth0_id
from api.services.auth0_service import Auth0Service


class MigrationStats:
    """Track migration statistics."""

    def __init__(self):
        self.total = 0
        self.successful = 0
        self.failed = 0
        self.skipped = 0
        self.duplicates = 0
        self.errors: List[Dict] = []

    def record_success(self, user_id: int, email: str, new_auth0_id: str):
        """Record a successful migration."""
        self.successful += 1
        # Check if this is a duplicate marker
        if new_auth0_id.startswith("DUPLICATE-") or "[DUPLICATE]" in new_auth0_id:
            self.duplicates += 1
            print(f"  🔗 Duplicate: User {user_id} ({email}) -> {new_auth0_id}")
        else:
            print(f"  ✓ Success: User {user_id} ({email}) -> {new_auth0_id}")

    def record_failure(self, user_id: int, email: str, error: str):
        """Record a failed migration."""
        self.failed += 1
        self.errors.append({"user_id": user_id, "email": email, "error": error})
        print(f"  ✗ Failed: User {user_id} ({email}) - {error}")

    def record_skip(self, user_id: int, email: str, reason: str):
        """Record a skipped user."""
        self.skipped += 1
        print(f"  ⊘ Skipped: User {user_id} ({email}) - {reason}")

    def print_summary(self):
        """Print migration summary."""
        print("\n" + "=" * 80)
        print("MIGRATION SUMMARY")
        print("=" * 80)
        print(f"Total users processed: {self.total}")
        print(f"Successful: {self.successful}")
        print(f"  - Fixed with new Auth0 users: {self.successful - self.duplicates}")
        print(f"  - Marked as duplicates: {self.duplicates}")
        print(f"Failed: {self.failed}")
        print(f"Skipped: {self.skipped}")

        if self.errors:
            print("\nERRORS:")
            for error in self.errors:
                print(f"  - User {error['user_id']} ({error['email']}): {error['error']}")

        print("=" * 80)


def get_aws_secret(secret_name: str, region: str = "eu-west-2") -> Dict:
    """
    Retrieve a secret from AWS Secrets Manager.

    Args:
        secret_name: Name of the secret
        region: AWS region

    Returns:
        Dictionary containing the secret data
    """
    client = boto3.client("secretsmanager", region_name=region)
    response = client.get_secret_value(SecretId=secret_name)
    return json.loads(response["SecretString"])


def get_database_connection(
    fetch_from_secrets: bool = False,
    secret_name: str = "fastapi-production-credentials",
    region: str = "eu-west-2",
) -> Session:
    """
    Create a database connection.

    Args:
        fetch_from_secrets: Whether to fetch credentials from AWS Secrets Manager
        secret_name: Name of the secret containing database credentials
        region: AWS region

    Returns:
        SQLAlchemy Session object
    """
    if fetch_from_secrets:
        print(f"📡 Fetching database credentials from AWS Secrets Manager: {secret_name}")
        secret = get_aws_secret(secret_name, region)
        db_host = secret["host"]
        db_port = secret.get("port", 3306)
        db_user = secret["username"]
        db_password = secret["password"]
        db_name = secret["dbname"]
    else:
        db_host = os.getenv("DB_HOST")
        db_port = os.getenv("DB_PORT", "3306")
        db_user = os.getenv("DB_USER")
        db_password = os.getenv("DB_PASSWORD")
        db_name = os.getenv("DB_NAME")

        if not all([db_host, db_user, db_password, db_name]):
            raise ValueError(
                "Missing database environment variables. "
                "Set DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME "
                "or use --fetch-from-secrets"
            )

    # Use MySQL connection for production
    db_url = (
        f"mysql+pymysql://{quote_plus(db_user)}:{quote_plus(db_password)}"
        f"@{db_host}:{db_port}/{db_name}"
    )

    print(f"📊 Connecting to database: {db_host}:{db_port}/{db_name}")
    engine = create_engine(db_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def is_valid_email(email: str) -> bool:
    """
    Check if an email address is valid.

    Args:
        email: Email address to validate

    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    # Check for common invalid values
    invalid_values = ['none', 'null', 'n/a', 'na', '-', 'unknown', '']
    if email.lower() in invalid_values:
        return False
    
    # Basic email regex validation
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(email_pattern, email) is not None


def set_auth0_id_to_null(db: Session, user_id: int) -> bool:
    """
    Set a user's auth0_user_id to NULL in the database.

    Args:
        db: Database session
        user_id: User ID to update

    Returns:
        True if successful, False otherwise
    """
    query = text(
        """
        UPDATE user
        SET auth0_user_id = NULL
        WHERE id = :user_id
        """
    )
    
    try:
        db.execute(query, {"user_id": user_id})
        db.commit()
        return True
    except Exception as e:
        print(f"    ✗ Error setting auth0_user_id to NULL: {e}")
        db.rollback()
        return False


def get_error_users(db: Session, limit: int) -> List[Dict]:
    """
    Query database for users with ERROR- prefixed auth0_user_id.

    Args:
        db: Database session
        limit: Maximum number of users to retrieve

    Returns:
        List of user dictionaries
    """
    query = text(
        """
        SELECT id, name, email, auth0_user_id
        FROM user
        WHERE auth0_user_id LIKE 'ERROR-%'
        ORDER BY id
        LIMIT :limit
        """
    )

    result = db.execute(query, {"limit": limit})
    users = []
    for row in result:
        users.append(
            {"id": row[0], "name": row[1], "email": row[2], "auth0_user_id": row[3]}
        )

    return users


def check_for_duplicate_user(db: Session, email: str, current_user_id: int) -> Optional[Dict]:
    """
    Check if another user exists with the same email and a valid Auth0 ID.

    Args:
        db: Database session
        email: Email address to check
        current_user_id: ID of the current ERROR- user (to exclude from search)

    Returns:
        Dictionary with user info if duplicate found, None otherwise
    """
    query = text(
        """
        SELECT id, name, email, auth0_user_id
        FROM user
        WHERE email = :email
        AND id != :current_user_id
        AND auth0_user_id LIKE 'auth0|%'
        LIMIT 1
        """
    )

    result = db.execute(query, {"email": email, "current_user_id": current_user_id})
    row = result.fetchone()

    if row:
        return {
            "id": row[0],
            "name": row[1],
            "email": row[2],
            "auth0_user_id": row[3],
        }

    return None


def generate_duplicate_marker(valid_user_id: int) -> str:
    """
    Generate a DUPLICATE- marker with the valid user's ID and random number.

    Args:
        valid_user_id: The ID of the valid user (the one with the working Auth0 account)

    Returns:
        String like "DUPLICATE-164-98765432" where 164 is the valid user's ID
    """
    import random
    random_digits = random.randint(10000000, 99999999)
    return f"DUPLICATE-{valid_user_id}-{random_digits}"




def fix_user(
    db: Session,
    auth0_service: Auth0Service,
    user: Dict,
    dry_run: bool,
    stats: MigrationStats,
) -> None:
    """
    Fix a single user with ERROR- prefixed auth0_user_id.

    Args:
        db: Database session
        auth0_service: Auth0Service instance
        user: User dictionary from database
        dry_run: Whether to run in dry-run mode
        stats: MigrationStats object
    """
    user_id = user["id"]
    username = user["name"]
    email = user["email"]
    old_auth0_id = user["auth0_user_id"]

    print(f"\n{'[DRY RUN] ' if dry_run else ''}Processing user {user_id}: {username} ({email})")
    print(f"  Current auth0_user_id: {old_auth0_id}")

    # Check for invalid email
    if not is_valid_email(email):
        print(f"  ⚠️  Invalid or missing email address: {email}")
        
        if not dry_run:
            print(f"    📝 Setting auth0_user_id to NULL...")
            success = set_auth0_id_to_null(db, user_id)
            
            if not success:
                stats.record_failure(user_id, email, "Failed to set auth0_user_id to NULL")
                return
            
            print(f"    ✓ Set auth0_user_id to NULL")
            stats.record_skip(user_id, email or username, "Invalid email - set to NULL")
        else:
            print(f"    [DRY RUN] Would set auth0_user_id to NULL")
            stats.record_skip(user_id, email or username, "Invalid email - would set to NULL")
        
        return

    # Skip if no email (shouldn't happen after validation above, but keep for safety)
    if not email:
        stats.record_skip(user_id, email or username, "No email address")
        return

    # NEW STEP: Check for duplicate user with same email and valid Auth0 ID
    print(f"  🔍 Checking for duplicate user with email: {email}")
    duplicate_user = check_for_duplicate_user(db, email, user_id)

    if duplicate_user:
        # This is a duplicate - mark it instead of fixing
        print(f"    ⚠️  Found duplicate user: {duplicate_user['id']} ({duplicate_user['name']})")
        print(f"    Valid Auth0 ID: {duplicate_user['auth0_user_id']}")
        print(f"    → This user (ID {user_id}) is a duplicate and should be marked")

        duplicate_marker = generate_duplicate_marker(duplicate_user['id'])

        if not dry_run:
            print(f"    📝 Marking as duplicate: {duplicate_marker}")
            success = update_user_auth0_id(db, user_id, duplicate_marker)

            if not success:
                stats.record_failure(user_id, email, "Failed to update database with DUPLICATE marker")
                return

            print(f"    ✓ Marked as duplicate successfully")
            stats.record_success(user_id, email, duplicate_marker)
        else:
            print(f"    [DRY RUN] Would mark as duplicate: {duplicate_marker}")
            stats.record_success(user_id, email, f"[DUPLICATE] {duplicate_marker}")

        return

    # No duplicate found - proceed with normal fix process
    print(f"    No duplicate user found - proceeding with normal fix")

    # Step 1: Search Auth0 for existing user with this email
    print(f"  🔍 Searching Auth0 for user with email: {email}")
    existing_auth0_user = auth0_service.find_user_by_email(email)

    if existing_auth0_user:
        existing_auth0_id = existing_auth0_user.get("user_id")
        print(f"    Found existing Auth0 user: {existing_auth0_id}")

        # Step 2: Delete the existing Auth0 user
        if not dry_run:
            print(f"    🗑️  Deleting existing Auth0 user: {existing_auth0_id}")
            deleted = auth0_service.delete_user(existing_auth0_id)
            if not deleted:
                stats.record_failure(
                    user_id, email, f"Failed to delete Auth0 user {existing_auth0_id}"
                )
                return
            print(f"    ✓ Deleted Auth0 user")
            
            # Wait for Auth0 deletion to propagate (avoid race condition)
            print(f"    ⏱️  Waiting 3 seconds for Auth0 deletion to propagate...")
            time.sleep(3)
        else:
            print(f"    [DRY RUN] Would delete Auth0 user: {existing_auth0_id}")
    else:
        print(f"    No existing Auth0 user found")

    # Step 3: Generate random password (not needed as create_user_for_admin_migration does it)

    # Step 4: Create new Auth0 user with manual_migration flag
    if not dry_run:
        print(f"    🔨 Creating new Auth0 user...")
        try:
            new_auth0_user = auth0_service.create_user_for_admin_migration(
                username=username,
                email=email,
                legacy_user_id=user_id,
            )

            if not new_auth0_user:
                stats.record_failure(user_id, email, "Failed to create new Auth0 user")
                return

            new_auth0_id = new_auth0_user.get("user_id")
            print(f"    ✓ Created Auth0 user: {new_auth0_id}")
            print(f"    New auth0_user_id: {new_auth0_id}")
        except Exception as e:
            stats.record_failure(user_id, email, f"Auth0 creation error: {str(e)}")
            return

        # Step 5: Update database with new auth0_user_id
        print(f"    💾 Updating database...")
        success = update_user_auth0_id(db, user_id, new_auth0_id)

        if not success:
            stats.record_failure(user_id, email, "Failed to update database")
            return

        stats.record_success(user_id, email, new_auth0_id)
    else:
        print(f"    [DRY RUN] Would create new Auth0 user and update database")
        stats.record_success(user_id, email, "[DRY RUN - no actual ID]")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Fix Auth0 users with ERROR- prefixed auth0_user_id values"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=1,
        help="Number of users to process (default: 1)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without making them",
    )
    parser.add_argument(
        "--environment",
        choices=["production", "staging"],
        default="production",
        help="Target environment (default: production)",
    )
    parser.add_argument(
        "--fetch-from-secrets",
        action="store_true",
        help="Fetch database credentials from AWS Secrets Manager",
    )
    parser.add_argument(
        "--region",
        default="eu-west-2",
        help="AWS region (default: eu-west-2)",
    )

    args = parser.parse_args()

    # Determine secret name based on environment
    if args.environment == "production":
        secret_name = "fastapi-production-credentials"
    else:
        secret_name = "fastapi-staging-credentials"

    print("=" * 80)
    print("FIX ERROR- PREFIXED AUTH0 USERS")
    print("=" * 80)
    print(f"Environment: {args.environment}")
    print(f"Limit: {args.limit}")
    print(f"Dry run: {args.dry_run}")
    print(f"AWS Region: {args.region}")
    print("=" * 80)

    # Initialize statistics
    stats = MigrationStats()

    try:
        # Connect to database
        db = get_database_connection(args.fetch_from_secrets, secret_name, args.region)

        # Initialize Auth0 service
        print("\n🔐 Initializing Auth0 service...")
        auth0_service = Auth0Service()
        print(f"   Connection: {auth0_service.connection}")
        print(f"   Tenant: {auth0_service.tenant_domain}")

        # Query for users with ERROR- prefixed auth0_user_id
        print(f"\n🔍 Querying database for users with ERROR- prefixed auth0_user_id...")
        users = get_error_users(db, args.limit)
        print(f"   Found {len(users)} users to process")

        if not users:
            print("\n✓ No users found with ERROR- prefixed auth0_user_id")
            return

        # Confirm before proceeding
        if not args.dry_run:
            response = input(
                f"\n⚠️  This will modify {len(users)} users. Continue? (yes/no): "
            )
            if response.lower() not in ["yes", "y"]:
                print("Aborted.")
                return

        # Process each user
        stats.total = len(users)
        for user in users:
            try:
                fix_user(db, auth0_service, user, args.dry_run, stats)
            except Exception as e:
                stats.record_failure(user["id"], user["email"], str(e))
                print(f"  ✗ Unexpected error: {e}")
                continue

        # Print summary
        stats.print_summary()

        # Close database connection
        db.close()

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

