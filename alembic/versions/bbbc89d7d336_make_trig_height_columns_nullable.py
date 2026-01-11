"""make trig height columns nullable and convert -1 sentinels to NULL

Revision ID: bbbc89d7d336
Revises: c4d5e6f7a8b9
Create Date: 2026-01-11

The database uses -1 as a sentinel value for unknown heights in both
wgs_height and osgb_height columns. This migration:
1. Makes both height columns nullable
2. Converts -1 sentinel values to NULL (only where BOTH are -1)
"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bbbc89d7d336"
down_revision: Union[str, Sequence[str], None] = "c4d5e6f7a8b9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    """Make height columns nullable and convert -1 sentinels to NULL."""
    # Step 1: Make wgs_height nullable
    op.alter_column(
        "trig",
        "wgs_height",
        existing_type=sa.INTEGER(),
        nullable=True,
    )

    # Step 2: Make osgb_height nullable
    op.alter_column(
        "trig",
        "osgb_height",
        existing_type=sa.INTEGER(),
        nullable=True,
    )

    # Step 3: Convert -1 sentinel values to NULL where BOTH heights are -1
    conn = op.get_bind()
    result = conn.execute(
        sa.text(
            """
            UPDATE trig
            SET wgs_height = NULL, osgb_height = NULL
            WHERE wgs_height = -1 AND osgb_height = -1
            """
        )
    )
    logger.info(
        "Updated %d rows: set wgs_height and osgb_height to NULL where both were -1",
        result.rowcount,
    )


def downgrade() -> None:
    """Revert NULL heights back to -1 and restore NOT NULL constraints."""
    conn = op.get_bind()

    # Step 1: Convert NULL values back to -1
    result = conn.execute(
        sa.text(
            """
            UPDATE trig
            SET wgs_height = -1, osgb_height = -1
            WHERE wgs_height IS NULL AND osgb_height IS NULL
            """
        )
    )
    logger.info(
        "Updated %d rows: set wgs_height and osgb_height to -1 where both were NULL",
        result.rowcount,
    )

    # Step 2: Restore NOT NULL constraint on wgs_height
    op.alter_column(
        "trig",
        "wgs_height",
        existing_type=sa.INTEGER(),
        nullable=False,
    )

    # Step 3: Restore NOT NULL constraint on osgb_height
    op.alter_column(
        "trig",
        "osgb_height",
        existing_type=sa.INTEGER(),
        nullable=False,
    )

