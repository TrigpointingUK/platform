"""add original height columns to trig

Revision ID: j9e0f1a2b3c4
Revises: i8d9e0f1a2b3
Create Date: 2026-01-29

Add original height columns to store the official OS-published heights.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = "j9e0f1a2b3c4"
down_revision: Union[str, Sequence[str], None] = "i8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add original height columns to trig table and populate from current heights."""
    conn = op.get_bind()

    logger.info("Adding original_wgs_height column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_wgs_height",
            sa.DECIMAL(8, 4),
            nullable=True,
            comment="Official OS WGS84 height in metres",
        ),
    )

    logger.info("Adding original_osgb_height column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_osgb_height",
            sa.DECIMAL(8, 4),
            nullable=True,
            comment="Official OS OSGB height in metres",
        ),
    )

    # Populate original heights from current heights for all trigs
    logger.info("Populating original height columns for all trigs...")
    result = conn.execute(sa.text("""
            UPDATE trig
            SET original_wgs_height = wgs_height,
                original_osgb_height = osgb_height
            """))
    logger.info("Populated original height columns for %d trigs", result.rowcount)

    logger.info("Migration complete: original height columns added to trig")


def downgrade() -> None:
    """Remove original height columns from trig table."""
    logger.info("Removing original_osgb_height column from trig...")
    op.drop_column("trig", "original_osgb_height")

    logger.info("Removing original_wgs_height column from trig...")
    op.drop_column("trig", "original_wgs_height")

    logger.info("Downgrade complete: original height columns removed from trig")
