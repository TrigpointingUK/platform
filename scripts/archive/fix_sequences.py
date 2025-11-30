#!/usr/bin/env python3
"""
Fix PostgreSQL sequences after data migration/import.

This script resets all sequences to the correct value based on the maximum
ID in each table. This is necessary after importing data because PostgreSQL
sequences don't automatically update when data is inserted directly.
"""

import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text

from api.db.database import get_session_local


def fix_sequences():
    """Fix all sequences in the database."""
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # List of tables with auto-increment IDs that need sequence fixes
        tables = [
            ("tlog", "tlog_id_seq"),
            ("tphoto", "tphoto_id_seq"),
            ("user", "user_id_seq"),
            ("trig", "trig_id_seq"),
            # Add more tables as needed
        ]

        print("Fixing database sequences...\n")

        for table_name, sequence_name in tables:
            try:
                # Check if table exists
                table_check = db.execute(
                    text(
                        f"SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = '{table_name}')"
                    )
                ).fetchone()

                if not table_check[0]:
                    print(f"⚠  Table {table_name} does not exist, skipping...")
                    continue

                # Get current max ID
                result = db.execute(
                    text(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}")
                ).fetchone()
                max_id = result[0] if result else 0

                # Check if sequence exists
                seq_check = db.execute(
                    text(
                        f"SELECT EXISTS (SELECT FROM pg_sequences WHERE schemaname = 'public' AND sequencename = '{sequence_name}')"
                    )
                ).fetchone()

                if not seq_check[0]:
                    print(f"⚠  Sequence {sequence_name} does not exist, skipping...")
                    continue

                # Get current sequence value
                seq_result = db.execute(
                    text(f"SELECT last_value FROM {sequence_name}")
                ).fetchone()
                current_seq = seq_result[0] if seq_result else 0

                # Reset sequence if needed
                if max_id >= current_seq:
                    new_seq = max_id + 1
                    db.execute(text(f"SELECT setval('{sequence_name}', {new_seq}, false)"))
                    db.commit()
                    print(
                        f"✓ {table_name}: max_id={max_id}, old_seq={current_seq}, new_seq={new_seq}"
                    )
                else:
                    print(
                        f"✓ {table_name}: max_id={max_id}, seq={current_seq} (already correct)"
                    )

            except Exception as e:
                print(f"✗ Error fixing {table_name}: {e}")
                db.rollback()
                continue

        print("\n✓ All sequences fixed!")

    except Exception as e:
        print(f"✗ Fatal error: {e}")
        db.rollback()
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    fix_sequences()

