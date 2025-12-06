#!/usr/bin/env python3
"""
Bulk delete duplicate logs that have no photos.

A duplicate is defined as logs with identical:
- user_id, trig_id, date, time, condition, comment

For each duplicate group, keeps the log with the highest ID (most recent).

Usage:
    # Dry run (default) - shows what would be deleted
    python scripts/bulk_delete_duplicate_logs.py

    # Actually delete
    python scripts/bulk_delete_duplicate_logs.py --execute

    # Connect to staging via tunnel on port 5433
    python scripts/bulk_delete_duplicate_logs.py --db-url "postgresql://user:pass@localhost:5433/dbname"
"""

import argparse
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from api.models.user import TLog


def get_duplicate_log_ids_to_delete(db: Session) -> list[int]:
    """
    Find all duplicate log IDs that should be deleted.

    For each group of duplicates (same user_id, trig_id, date, time, condition, comment),
    keeps the one with the highest ID and returns the rest for deletion.

    Only considers logs without photos.
    """
    # Use raw SQL for clarity and efficiency
    result = db.execute(
        text(
            """
        WITH logs_without_photos AS (
            SELECT t.id, t.user_id, t.trig_id, t.date, t.time, t.condition, t.comment
            FROM tlog t
            WHERE NOT EXISTS (
                SELECT 1 FROM tphoto p 
                WHERE p.tlog_id = t.id AND p.deleted_ind != 'Y'
            )
        ),
        duplicate_groups AS (
            SELECT 
                user_id, trig_id, date, time, condition, comment,
                MAX(id) as keep_id
            FROM logs_without_photos
            GROUP BY user_id, trig_id, date, time, condition, comment
            HAVING COUNT(*) > 1
        )
        SELECT lwp.id
        FROM logs_without_photos lwp
        JOIN duplicate_groups dg ON 
            lwp.user_id IS NOT DISTINCT FROM dg.user_id
            AND lwp.trig_id IS NOT DISTINCT FROM dg.trig_id
            AND lwp.date IS NOT DISTINCT FROM dg.date
            AND lwp.time IS NOT DISTINCT FROM dg.time
            AND lwp.condition IS NOT DISTINCT FROM dg.condition
            AND lwp.comment IS NOT DISTINCT FROM dg.comment
        WHERE lwp.id != dg.keep_id
        ORDER BY lwp.id
        """
        )
    )
    return [row[0] for row in result.fetchall()]


def get_sample_duplicates(db: Session, limit: int = 10) -> list[dict]:
    """Get a sample of duplicate groups for review."""
    result = db.execute(
        text(
            """
        WITH logs_without_photos AS (
            SELECT t.*, u.name as user_name, tr.name as trig_name
            FROM tlog t
            LEFT JOIN "user" u ON u.id = t.user_id
            LEFT JOIN trig tr ON tr.id = t.trig_id
            WHERE NOT EXISTS (
                SELECT 1 FROM tphoto p 
                WHERE p.tlog_id = t.id AND p.deleted_ind != 'Y'
            )
        )
        SELECT 
            user_id, user_name, trig_id, trig_name, date, time, condition,
            LEFT(comment, 50) as comment_preview,
            COUNT(*) as duplicate_count,
            array_agg(id ORDER BY id) as log_ids
        FROM logs_without_photos
        GROUP BY user_id, user_name, trig_id, trig_name, date, time, condition, comment
        HAVING COUNT(*) > 1
        ORDER BY COUNT(*) DESC, user_id
        LIMIT :limit
        """
        ),
        {"limit": limit},
    )
    columns = result.keys()
    return [dict(zip(columns, row)) for row in result.fetchall()]


def main():
    parser = argparse.ArgumentParser(
        description="Bulk delete duplicate logs without photos"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the deletion (default is dry-run)",
    )
    parser.add_argument(
        "--sample",
        type=int,
        default=10,
        help="Number of sample duplicates to show (default: 10)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Database URL (default: uses get_engine() from app config)",
    )
    args = parser.parse_args()

    if args.db_url:
        engine = create_engine(args.db_url)
    else:
        from api.db.database import get_engine

        engine = get_engine()

    with Session(engine) as db:
        # Show sample duplicates
        print("\n=== Sample Duplicate Groups ===\n")
        samples = get_sample_duplicates(db, args.sample)
        for sample in samples:
            print(f"User: {sample['user_name']} (ID: {sample['user_id']})")
            print(f"Trig: {sample['trig_name']} (ID: {sample['trig_id']})")
            print(f"Date: {sample['date']}, Time: {sample['time']}")
            print(f"Condition: {sample['condition']}")
            print(f"Comment: {sample['comment_preview']}...")
            print(
                f"Duplicates: {sample['duplicate_count']} logs, IDs: {sample['log_ids']}"
            )
            print("-" * 60)

        # Get all IDs to delete
        ids_to_delete = get_duplicate_log_ids_to_delete(db)
        print(f"\n=== Summary ===")
        print(f"Total logs to delete: {len(ids_to_delete)}")

        if not ids_to_delete:
            print("No duplicate logs found. Nothing to do.")
            return

        if not args.execute:
            print("\n*** DRY RUN - No changes made ***")
            print("Run with --execute to actually delete these logs.")
            return

        # Perform deletion
        print("\n=== Executing Deletion ===")
        confirm = input(f"Delete {len(ids_to_delete)} duplicate logs? (yes/no): ")
        if confirm.lower() != "yes":
            print("Aborted.")
            return

        # Delete in batches
        batch_size = 100
        total_deleted = 0

        for i in range(0, len(ids_to_delete), batch_size):
            batch = ids_to_delete[i : i + batch_size]
            deleted = (
                db.query(TLog)
                .filter(TLog.id.in_(batch))
                .delete(synchronize_session=False)
            )
            total_deleted += deleted
            print(f"  Deleted batch {i // batch_size + 1}: {deleted} logs")

        db.commit()
        print(f"\n=== Complete ===")
        print(f"Total deleted: {total_deleted} logs")


if __name__ == "__main__":
    main()
