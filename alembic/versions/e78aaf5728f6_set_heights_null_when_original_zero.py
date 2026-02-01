"""set_heights_null_when_original_zero

Revision ID: e78aaf5728f6
Revises: df2d07d52b59
Create Date: 2026-02-01 21:46:45.600150

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e78aaf5728f6"
down_revision: Union[str, Sequence[str], None] = "df2d07d52b59"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    """
    Set osgb_height and wgs_height to NULL where original_osgb_height is 0.

    A height of 0 typically indicates "unknown" rather than an actual height
    of 0 metres, so these should be NULL for proper handling in queries and
    display logic.
    """
    conn = op.get_bind()

    # Update osgb_height to NULL where original_osgb_height = 0
    result = conn.execute(sa.text("""
            UPDATE trig
            SET osgb_height = NULL
            WHERE original_osgb_height = 0
              AND osgb_height IS NOT NULL
        """))
    logger.info(
        "Set osgb_height to NULL for %d rows where original_osgb_height = 0",
        result.rowcount,
    )

    # Update wgs_height to NULL where original_osgb_height = 0
    result = conn.execute(sa.text("""
            UPDATE trig
            SET wgs_height = NULL
            WHERE original_osgb_height = 0
              AND wgs_height IS NOT NULL
        """))
    logger.info(
        "Set wgs_height to NULL for %d rows where original_osgb_height = 0",
        result.rowcount,
    )


def downgrade() -> None:
    """
    Downgrade is a no-op - we cannot restore the original 0 values
    as we don't know which rows previously had 0 vs NULL.
    """
    logger.warning(
        "Downgrade for set_heights_null_when_original_zero is a no-op. "
        "Height values cannot be automatically restored."
    )
