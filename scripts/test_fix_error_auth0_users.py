#!/usr/bin/env python3
"""
Simple validation test for fix_error_auth0_users.py script.

This test verifies the script's structure and basic functionality
without requiring actual database or Auth0 connections.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


def test_script_imports():
    """Test that the script can be imported."""
    # Import the script module
    import scripts.fix_error_auth0_users as script

    # Verify key classes and functions exist
    assert hasattr(script, "MigrationStats")
    assert hasattr(script, "get_error_users")
    assert hasattr(script, "fix_user")
    assert hasattr(script, "get_database_connection")
    assert hasattr(script, "get_aws_secret")


def test_migration_stats():
    """Test MigrationStats class."""
    import scripts.fix_error_auth0_users as script

    stats = script.MigrationStats()

    # Test initial values
    assert stats.total == 0
    assert stats.successful == 0
    assert stats.failed == 0
    assert stats.skipped == 0
    assert len(stats.errors) == 0

    # Test record_success
    stats.record_success(123, "test@example.com", "auth0|abc123")
    assert stats.successful == 1

    # Test record_failure
    stats.record_failure(456, "fail@example.com", "Test error")
    assert stats.failed == 1
    assert len(stats.errors) == 1
    assert stats.errors[0]["user_id"] == 456

    # Test record_skip
    stats.record_skip(789, "skip@example.com", "No email")
    assert stats.skipped == 1


def test_script_help():
    """Test that script help works."""
    import subprocess

    result = subprocess.run(
        ["python", "scripts/fix_error_auth0_users.py", "--help"],
        capture_output=True,
        text=True,
        timeout=5,
    )

    assert result.returncode == 0
    assert "--limit" in result.stdout
    assert "--dry-run" in result.stdout
    assert "--environment" in result.stdout
    assert "--fetch-from-secrets" in result.stdout


def main():
    """Run all tests."""
    print("=" * 80)
    print("TESTING: fix_error_auth0_users.py")
    print("=" * 80)

    tests = [test_script_imports, test_migration_stats, test_script_help]

    passed = 0
    failed = 0
    for test in tests:
        print(f"\nRunning: {test.__name__}")
        try:
            test()
            print(f"✓ {test.__name__} passed")
            passed += 1
        except Exception as e:
            print(f"✗ {test.__name__} failed: {e}")
            failed += 1

    print("\n" + "=" * 80)
    print("RESULTS")
    print("=" * 80)
    total = len(tests)
    print(f"Passed: {passed}/{total}")

    if failed == 0:
        print("\n✓ All tests passed!")
        return 0
    else:
        print(f"\n✗ {failed} test(s) failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())
