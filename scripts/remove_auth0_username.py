#!/usr/bin/env python3
"""
Remove the username field from a specific Auth0 user.

This script:
1. Accepts an auth0_user_id as a command-line argument
2. Fetches the user's current details from Auth0
3. Removes the username field by setting it to null
4. Displays before/after state

Usage:
    python scripts/remove_auth0_username.py auth0|1234567890abcdef
    python scripts/remove_auth0_username.py auth0|1234567890abcdef --dry-run
    python scripts/remove_auth0_username.py auth0|1234567890abcdef --verbose

Environment variables required:
    AUTH0_TENANT_DOMAIN, AUTH0_M2M_CLIENT_ID, AUTH0_M2M_CLIENT_SECRET, AUTH0_CONNECTION
    REDIS_URL (optional, for token caching)
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, Optional

# Add parent directory to path so we can import from api
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.services.auth0_service import Auth0Service


def get_user_details(auth0_service: Auth0Service, user_id: str) -> Optional[Dict]:
    """
    Get user details from Auth0.

    Args:
        auth0_service: Auth0Service instance
        user_id: Auth0 user ID

    Returns:
        User dictionary or None if not found
    """
    response = auth0_service._make_auth0_request("GET", f"users/{user_id}")
    return response


def remove_username_field(
    auth0_service: Auth0Service,
    user_id: str,
    dry_run: bool = False,
    verbose: bool = False,
) -> tuple[bool, Optional[str]]:
    """
    Remove the username field from an Auth0 user.

    Args:
        auth0_service: Auth0Service instance
        user_id: Auth0 user ID
        dry_run: Whether to run in dry-run mode
        verbose: Whether to print verbose output

    Returns:
        Tuple of (success: bool, error_message: Optional[str])
    """
    if dry_run:
        print(f"   [DRY RUN] Would attempt to remove username field")
        return True, None

    # Try setting username to None first
    if verbose:
        print("   Attempting to set username to null...")
    response = auth0_service._make_auth0_request(
        "PATCH", f"users/{user_id}", {"username": None}
    )

    if response is not None:
        return True, None

    # Check if we got the "operation_not_supported" error
    if auth0_service._last_error:
        error_response = auth0_service._last_error.get("error_response", {})
        error_code = error_response.get("errorCode")
        error_message = error_response.get("message", "")

        if error_code == "operation_not_supported":
            # This connection doesn't support modifying username field
            return False, (
                "Auth0 connection doesn't support modifying username field.\n"
                f"   Error: {error_message}\n"
                "   \n"
                "   This typically happens with database connections that don't require usernames.\n"
                "   Unfortunately, Auth0's Management API doesn't allow removing the username field\n"
                "   for this connection type. You may need to:\n"
                "   1. Update the connection settings in Auth0 Dashboard to require usernames\n"
                "   2. Or delete and recreate the user without a username field"
            )
        else:
            return False, f"API Error: {error_message} (code: {error_code})"

    return False, "Unknown error occurred"


def display_user_info(user: Dict, title: str = "User Details"):
    """
    Display user information in a formatted way.

    Args:
        user: User dictionary from Auth0
        title: Title to display
    """
    print(f"\n{title}:")
    print("  " + "-" * 76)
    print(f"  User ID:    {user.get('user_id', 'N/A')}")
    print(f"  Username:   {user.get('username', 'N/A')}")
    print(f"  Email:      {user.get('email', 'N/A')}")
    print(f"  Nickname:   {user.get('nickname', 'N/A')}")
    print(f"  Name:       {user.get('name', 'N/A')}")

    identities = user.get("identities", [])
    if identities:
        connection = identities[0].get("connection", "N/A")
        print(f"  Connection: {connection}")

    print("  " + "-" * 76)


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Remove the username field from a specific Auth0 user"
    )
    parser.add_argument(
        "user_id",
        type=str,
        help="Auth0 user ID (e.g., auth0|1234567890abcdef)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview the change without making it",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print verbose output",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompt",
    )

    args = parser.parse_args()

    print("=" * 80)
    print("REMOVE AUTH0 USERNAME FIELD")
    print("=" * 80)
    print(f"User ID: {args.user_id}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 80)

    try:
        # Initialize Auth0 service
        if args.verbose:
            print("\n🔐 Initializing Auth0 service...")
        auth0_service = Auth0Service()
        if args.verbose:
            print(f"   Connection: {auth0_service.connection}")
            print(f"   Tenant: {auth0_service.tenant_domain}")

        # Step 1: Fetch current user details
        print(f"\n🔍 Fetching user details from Auth0...")
        user_before = get_user_details(auth0_service, args.user_id)

        if not user_before:
            print(f"\n❌ Error: User not found with ID: {args.user_id}")
            sys.exit(1)

        # Display current state
        display_user_info(user_before, "Current User Details")

        # Check if username field is set
        username = user_before.get("username")
        if not username:
            print("\n✓ Username field is not set for this user (nothing to remove)")
            sys.exit(0)

        print(f"\n⚠️  Username field is set to: '{username}'")

        # Confirmation prompt (unless --force or --dry-run)
        if not args.dry_run and not args.force:
            response = input("\nRemove username field? (yes/no): ")
            if response.lower() not in ["yes", "y"]:
                print("Aborted.")
                sys.exit(0)

        # Step 2: Remove username field
        print(f"\n{'[DRY RUN] ' if args.dry_run else ''}🔨 Removing username field...")
        success, error_msg = remove_username_field(
            auth0_service, args.user_id, args.dry_run, args.verbose
        )

        if not success:
            print(f"\n❌ Error: Failed to remove username field")
            if error_msg:
                print(f"\n{error_msg}")
            sys.exit(1)

        if args.dry_run:
            print("\n✓ [DRY RUN] Would have removed username field")
            print(f"\nThe username field ('{username}') would be set to null")
        else:
            # Step 3: Fetch updated user details
            print(f"\n🔍 Fetching updated user details...")
            user_after = get_user_details(auth0_service, args.user_id)

            if not user_after:
                print(f"\n⚠️  Warning: Could not fetch updated user details")
            else:
                # Display updated state
                display_user_info(user_after, "Updated User Details")

            # Verify username was removed
            if user_after and user_after.get("username"):
                print(
                    f"\n⚠️  Warning: Username field still set to '{user_after.get('username')}'"
                )
            else:
                print(f"\n✓ Successfully removed username field")

        print("\n" + "=" * 80)
        print("OPERATION COMPLETE")
        print("=" * 80)

    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
