"""drop status_max column

Revision ID: c2d3e4f5a6b7
Revises: b1c2d3e4f5a6
Create Date: 2026-01-18

Drops the deprecated status_max column from the user table.

The status_max column has been replaced by ui_prefs.default_groups (a list of
trig_type_group.code values). The previous migration (b1c2d3e4f5a6) converted
existing status_max values to default_groups.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c2d3e4f5a6b7"
down_revision: Union[str, Sequence[str], None] = "b1c2d3e4f5a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    """Drop the status_max column from the user table."""
    logger.info("Dropping status_max column from user table...")
    op.drop_column("user", "status_max")
    logger.info("Dropped status_max column")


def downgrade() -> None:
    """Re-add the status_max column to the user table.

    Note: This will restore the column with NULL values. The original values
    cannot be restored unless backed up separately.
    """
    logger.info("Re-adding status_max column to user table...")
    op.add_column(
        "user",
        sa.Column("status_max", sa.Integer(), nullable=True, server_default="0"),
    )
    logger.info("Re-added status_max column (values will be NULL/0)")

