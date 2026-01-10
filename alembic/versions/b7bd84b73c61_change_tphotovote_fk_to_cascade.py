"""change_tphotovote_fk_to_cascade

Change the tphotovote.tphoto_id foreign key from ON DELETE SET NULL to
ON DELETE CASCADE. When a photo is deleted, its votes should be deleted
rather than orphaned with a NULL reference.

The application code explicitly deletes tphotovote rows before deleting
tphoto rows, so this constraint serves as a safety net rather than the
primary deletion mechanism.

Revision ID: b7bd84b73c61
Revises: 4ea06b786808
Create Date: 2026-01-10 16:57:06.590866

"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "b7bd84b73c61"
down_revision: Union[str, Sequence[str], None] = "4ea06b786808"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

OLD_CONSTRAINT = "fk_tphotovote_tphoto_id__tphoto_id"
NEW_CONSTRAINT = "fk_tphotovote_tphoto_id__tphoto_id"  # Same name, different behaviour


def _constraint_exists(conn, name: str) -> bool:
    return (
        conn.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
            {"name": name},
        ).scalar()
        is not None
    )


def upgrade() -> None:
    """Upgrade schema: change FK from SET NULL to CASCADE."""
    conn = op.get_bind()

    # Drop the existing SET NULL constraint if it exists
    if _constraint_exists(conn, OLD_CONSTRAINT):
        op.execute(
            sa.text(
                f'ALTER TABLE "tphotovote" DROP CONSTRAINT "{OLD_CONSTRAINT}"'
            )
        )
        logger.info(f"Dropped constraint {OLD_CONSTRAINT}")

    # Add the new CASCADE constraint
    op.execute(
        sa.text(
            f"""
            ALTER TABLE "tphotovote"
            ADD CONSTRAINT "{NEW_CONSTRAINT}"
            FOREIGN KEY ("tphoto_id")
            REFERENCES "tphoto" ("id")
            ON DELETE CASCADE
            NOT VALID
            """
        )
    )
    logger.info(f"Added constraint {NEW_CONSTRAINT} with ON DELETE CASCADE")


def downgrade() -> None:
    """Downgrade schema: revert FK from CASCADE to SET NULL."""
    conn = op.get_bind()

    # Drop the CASCADE constraint if it exists
    if _constraint_exists(conn, NEW_CONSTRAINT):
        op.execute(
            sa.text(
                f'ALTER TABLE "tphotovote" DROP CONSTRAINT "{NEW_CONSTRAINT}"'
            )
        )
        logger.info(f"Dropped constraint {NEW_CONSTRAINT}")

    # Re-add the SET NULL constraint
    op.execute(
        sa.text(
            f"""
            ALTER TABLE "tphotovote"
            ADD CONSTRAINT "{OLD_CONSTRAINT}"
            FOREIGN KEY ("tphoto_id")
            REFERENCES "tphoto" ("id")
            ON DELETE SET NULL
            NOT VALID
            """
        )
    )
    logger.info(f"Added constraint {OLD_CONSTRAINT} with ON DELETE SET NULL")
