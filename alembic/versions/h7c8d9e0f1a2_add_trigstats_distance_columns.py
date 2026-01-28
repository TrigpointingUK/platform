"""add trigstats distance columns for coordinate discrepancy monitoring

Revision ID: h7c8d9e0f1a2
Revises: g6b7c8d9e0f1
Create Date: 2026-01-28

This migration adds two new columns to the trigstats table for monitoring
coordinate discrepancies between different data sources:

- dist_wgs_osgb: Distance in metres between WGS84 coords (transformed via OSTN15)
  and the stored OSGB coords in trig table
- dist_osgb_osgb: Distance in metres between trig.osgb* coords and attrval coords
  (attr_id 4=eastings, 5=northings)

These are nullable columns that will be populated incrementally as trigstats
records are updated.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "h7c8d9e0f1a2"
down_revision: Union[str, Sequence[str], None] = "g6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add distance columns to trigstats table."""
    logger.info("Adding dist_wgs_osgb column to trigstats...")
    op.add_column(
        "trigstats",
        sa.Column(
            "dist_wgs_osgb",
            sa.DECIMAL(10, 4),
            nullable=True,
            comment="Distance (m) between WGS84->OSTN15 and stored OSGB coords",
        ),
    )

    logger.info("Adding dist_osgb_osgb column to trigstats...")
    op.add_column(
        "trigstats",
        sa.Column(
            "dist_osgb_osgb",
            sa.DECIMAL(10, 4),
            nullable=True,
            comment="Distance (m) between trig.osgb* and attrval OSGB coords",
        ),
    )

    logger.info("Migration complete: distance columns added to trigstats")


def downgrade() -> None:
    """Remove distance columns from trigstats table."""
    logger.info("Removing dist_osgb_osgb column from trigstats...")
    op.drop_column("trigstats", "dist_osgb_osgb")

    logger.info("Removing dist_wgs_osgb column from trigstats...")
    op.drop_column("trigstats", "dist_wgs_osgb")

    logger.info("Downgrade complete: distance columns removed from trigstats")
