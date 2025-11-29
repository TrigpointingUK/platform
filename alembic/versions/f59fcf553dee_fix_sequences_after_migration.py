"""fix_sequences_after_migration

This migration fixes PostgreSQL sequences after data migration/import.
When data is imported directly into tables, the sequences don't automatically
update, causing "duplicate key" errors on inserts. This migration resets all
sequences to the correct value based on the maximum ID in each table.

Revision ID: f59fcf553dee
Revises: 42228d2858b0
Create Date: 2025-11-29 11:30:39.780807

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f59fcf553dee"
down_revision: Union[str, Sequence[str], None] = "42228d2858b0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Fix all sequences to start from max(id) + 1."""
    # List of tables with auto-increment IDs
    tables_with_sequences = [
        ("tlog", "tlog_id_seq"),
        ("tphoto", "tphoto_id_seq"),
        ("user", "user_id_seq"),
        ("trig", "trig_id_seq"),
        ("attr", "attr_id_seq"),
        ("attrval", "attrval_id_seq"),
        ("place", "place_id_seq"),
        ("town", "town_id_seq"),
        ("county", "county_id_seq"),
        # Add other tables as needed
    ]

    conn = op.get_bind()

    for table_name, sequence_name in tables_with_sequences:
        # Check if table and sequence exist before trying to fix
        table_exists = conn.execute(
            sa.text(
                f"SELECT EXISTS (SELECT FROM information_schema.tables "
                f"WHERE table_schema = 'public' AND table_name = '{table_name}')"
            )
        ).scalar()

        if not table_exists:
            continue

        seq_exists = conn.execute(
            sa.text(
                f"SELECT EXISTS (SELECT FROM pg_sequences "
                f"WHERE schemaname = 'public' AND sequencename = '{sequence_name}')"
            )
        ).scalar()

        if not seq_exists:
            continue

        # Reset the sequence to max(id) + 1
        # Using false as third parameter means the next nextval() will return the specified value
        conn.execute(
            sa.text(
                f"SELECT setval('{sequence_name}', "
                f"(SELECT COALESCE(MAX(id), 0) + 1 FROM {table_name}), false)"
            )
        )


def downgrade() -> None:
    """No downgrade needed - sequence values cannot be meaningfully reverted."""
    # Sequences are forward-only - there's no meaningful way to downgrade
    # The previous values are lost once advanced
    pass
