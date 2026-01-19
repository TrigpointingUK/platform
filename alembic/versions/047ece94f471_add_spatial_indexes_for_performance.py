"""add spatial indexes for performance

Revision ID: 047ece94f471
Revises: a2b3c4d5e6f7
Create Date: 2026-01-17

This migration adds indexes to improve query performance:
1. GIST spatial index on trig.location for efficient ST_DWithin queries
2. Composite index on tlog(user_id, trig_id) for efficient "has user logged" queries
"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "047ece94f471"
down_revision: Union[str, Sequence[str], None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    """Add performance indexes."""
    conn = op.get_bind()

    # 1. Create GIST spatial index on trig.location
    # This is essential for ST_DWithin to use the spatial index
    # instead of scanning all rows
    # Note: Not using CONCURRENTLY as it can't run inside a transaction
    # The trig table is small (~9000 rows) so lock duration will be brief
    logger.info("Creating GIST spatial index on trig.location...")
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_trig_location_gist
            ON trig USING GIST (location)
            """
        )
    )
    logger.info("Created idx_trig_location_gist")

    # 2. Create composite index on tlog(user_id, trig_id)
    # This optimizes the "has user logged this trig" queries used by
    # exclude_found and only_found filters
    logger.info("Creating composite index on tlog(user_id, trig_id)...")
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS ix_tlog_user_trig
            ON tlog (user_id, trig_id)
            """
        )
    )
    logger.info("Created ix_tlog_user_trig")


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index("ix_tlog_user_trig", table_name="tlog")
    op.drop_index("idx_trig_location_gist", table_name="trig")
