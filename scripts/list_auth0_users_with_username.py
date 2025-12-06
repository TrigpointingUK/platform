#!/usr/bin/env python3
"""
List Auth0 users who have a username field set.

This script:
1. Queries Auth0 Management API for all users (with pagination)
2. Filters users who have a username field set
3. Outputs their auth0_user_id values

Usage:
    python scripts/list_auth0_users_with_username.py
    python scripts/list_auth0_users_with_username.py --connection Username-Password-Authentication
    python scripts/list_auth0_users_with_username.py --output username_users.txt
    python scripts/list_auth0_users_with_username.py --verbose

Environment variables required:
    AUTH0_TENANT_DOMAIN, AUTH0_M2M_CLIENT_ID, AUTH0_M2M_CLIENT_SECRET, AUTH0_CONNECTION
    REDIS_URL (optional, for token caching)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional

# Add parent directory to path so we can import from api
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.auth0_service import Auth0Service


def get_all_users_with_username(
    auth0_service: Auth0Service,
    connection_filter: Optional[str] = None,
    verbose: bool = False,
) -> List[Dict]:
    """
    Get all Auth0 users who have a username field set.

    Args:
        auth0_service: Auth0Service instance
        connection_filter: Optional connection name to filter by
        verbose: Whether to print verbose output

    Returns:
        List of user dictionaries containing user_id, username, email, nickname
    """
    users_with_username = []
    page = 0
    per_page = 100
    total_users_checked = 0

    if verbose:
        print("🔍 Fetching users from Auth0...")

    while True:
        # Fetch page of users
        endpoint = f"users?per_page={per_page}&page={page}&include_totals=true"

        if verbose:
            print(
                f"   Fetching page {page} (users {page * per_page}-{(page + 1) * per_page})..."
            )

        response = auth0_service._make_auth0_request("GET", endpoint)

        if not response:
            if verbose:
                print(f"   ⚠️  No response from Auth0 API")
            break

        users = response.get("users", [])
        total = response.get("total", 0)

        if not users:
            if verbose:
                print(f"   ✓ No more users to fetch")
            break

        # Check each user for username field
        for user in users:
            total_users_checked += 1
            username = user.get("username")

            # Filter by connection if specified
            if connection_filter:
                identities = user.get("identities", [])
                if not identities:
                    continue
                user_connection = identities[0].get("connection")
                if user_connection != connection_filter:
                    continue

            # Check if username field is set (not None and not empty string)
            if username:
                user_info = {
                    "user_id": user.get("user_id"),
                    "username": username,
                    "email": user.get("email", ""),
                    "nickname": user.get("nickname", ""),
                    "connection": user.get("identities", [{}])[0].get("connection", ""),
                }
                users_with_username.append(user_info)

                if verbose:
                    print(
                        f"   ✓ Found: {user_info['user_id']} "
                        f"(username={username}, connection={user_info['connection']})"
                    )

        # Check if we've fetched all users
        if len(users) < per_page or total_users_checked >= total:
            if verbose:
                print(f"   ✓ Fetched all users (total: {total_users_checked})")
            break

        page += 1

    if verbose:
        print(f"\n📊 Total users checked: {total_users_checked}")
        print(f"📊 Users with username field: {len(users_with_username)}")

    return users_with_username


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="List Auth0 users who have a username field set"
    )
    parser.add_argument(
        "--connection",
        type=str,
        help="Filter by connection name (e.g., Username-Password-Authentication)",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: print to stdout)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output",
    )
    parser.add_argument(
        "--format",
        choices=["id-only", "json", "csv"],
        default="id-only",
        help="Output format (default: id-only)",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("LIST AUTH0 USERS WITH USERNAME FIELD")
    print("=" * 80)
    if args.connection:
        print(f"Connection filter: {args.connection}")
    if args.output:
        print(f"Output file: {args.output}")
    print(f"Format: {args.format}")
    print("=" * 80)

    try:
        # Initialize Auth0 service
        if args.verbose:
            print("\n🔐 Initializing Auth0 service...")
        auth0_service = Auth0Service()
        if args.verbose:
            print(f"   Connection: {auth0_service.connection}")
            print(f"   Tenant: {auth0_service.tenant_domain}")

        # Get all users with username field
        users = get_all_users_with_username(
            auth0_service, args.connection, args.verbose
        )

        if not users:
            print("\n✓ No users found with username field set")
            return

        # Format output
        output_lines = []

        if args.format == "id-only":
            # Just the auth0_user_id values, one per line
            output_lines = [user["user_id"] for user in users]
        elif args.format == "json":
            # Full JSON output
            output_lines = [json.dumps(users, indent=2)]
        elif args.format == "csv":
            # CSV format
            output_lines = ["user_id,username,email,nickname,connection"]
            for user in users:
                output_lines.append(
                    f"{user['user_id']},{user['username']},{user['email']},"
                    f"{user['nickname']},{user['connection']}"
                )

        # Write to file or stdout
        if args.output:
            output_path = Path(args.output)
            output_path.write_text("\n".join(output_lines) + "\n")
            print(f"\n✓ Wrote {len(users)} user IDs to {args.output}")
        else:
            print("\n" + "=" * 80)
            print("USERS WITH USERNAME FIELD:")
            print("=" * 80)
            for line in output_lines:
                print(line)
            print("=" * 80)
            print(f"Total: {len(users)} users")

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
