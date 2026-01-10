"""cleanup_orphaned_fk_rows

Revision ID: b312d005cf5e
Revises: 53992fd8a62b
Create Date: 2026-01-10 15:45:22.407798

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "b312d005cf5e"
down_revision: Union[str, Sequence[str], None] = "53992fd8a62b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Clean up orphaned foreign key references before constraint validation."""
    # Notes:
    # - This migration performs DATA changes (deletes/updates) to satisfy FK constraints.
    # - It is intentionally not reversible: deleted rows cannot be restored reliably.

    # Delete rows in trigstats with invalid trig_id (trigstats.id == trig.id)
    op.execute(
        sa.text(
            """
            DELETE FROM trigstats ts
            WHERE NOT EXISTS (
                SELECT 1
                FROM trig t
                WHERE t.id = ts.id
            )
            """
        )
    )

    # Delete rows in tlog with invalid user_id
    op.execute(
        sa.text(
            """
            DELETE FROM tlog tl
            WHERE tl.user_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM "user" u
                WHERE u.id = tl.user_id
              )
            """
        )
    )

    # Delete rows in attrset with invalid trig_id
    op.execute(
        sa.text(
            """
            DELETE FROM attrset aset
            WHERE NOT EXISTS (
                SELECT 1
                FROM trig t
                WHERE t.id = aset.trig_id
            )
            """
        )
    )

    # Delete rows in tphoto with an invalid tlog_id
    op.execute(
        sa.text(
            """
            DELETE FROM tphoto p
            WHERE NOT EXISTS (
                SELECT 1
                FROM tlog tl
                WHERE tl.id = p.tlog_id
            )
            """
        )
    )

    # Delete rows in tphotovote with an invalid tphoto_id
    op.execute(
        sa.text(
            """
            DELETE FROM tphotovote v
            WHERE NOT EXISTS (
                SELECT 1
                FROM tphoto p
                WHERE p.id = v.tphoto_id
            )
            """
        )
    )

    # Null invalid user_id in tphotovote (where user no longer exists)
    op.execute(
        sa.text(
            """
            UPDATE tphotovote v
            SET user_id = NULL
            WHERE v.user_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM "user" u
                WHERE u.id = v.user_id
              )
            """
        )
    )

    # Null invalid crt_user_id in trig (where user no longer exists)
    op.execute(
        sa.text(
            """
            UPDATE trig t
            SET crt_user_id = NULL
            WHERE t.crt_user_id IS NOT NULL
              AND NOT EXISTS (
                SELECT 1
                FROM "user" u
                WHERE u.id = t.crt_user_id
              )
            """
        )
    )


def downgrade() -> None:
    """
    Downgrade schema.

    This migration deletes rows and nulls foreign key values; it cannot be reversed safely.
    """
    # No-op by design.
    return
