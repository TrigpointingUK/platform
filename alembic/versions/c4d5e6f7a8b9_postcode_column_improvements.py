"""postcode column improvements

Revision ID: c4d5e6f7a8b9
Revises: 96c8c6061f3a
Create Date: 2026-01-10

This migration:
- Drops the legacy `postcode6` column from the trig table
- Makes `trig.postcode` nullable (was NOT NULL)
- Adds a foreign key constraint: trig.postcode -> postcodes.code
- Adds a spatial index on postcodes(lat, long) for efficient nearest-postcode queries
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op
from api.core.logging import get_logger

logger = get_logger(__name__)


# revision identifiers, used by Alembic.
revision: str = "c4d5e6f7a8b9"
down_revision: Union[str, Sequence[str], None] = "96c8c6061f3a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade schema:
    1. Drop legacy postcode6 column
    2. Make postcode nullable
    3. Add FK constraint to postcodes table
    4. Add spatial index on postcodes for efficient nearest-postcode queries
    """
    conn = op.get_bind()

    # 1. Drop the legacy postcode6 column from trig table
    logger.info("Dropping legacy postcode6 column from trig table...")
    op.drop_column("trig", "postcode6")
    logger.info("Dropped postcode6 column")

    # 2. Make trig.postcode nullable
    logger.info("Making trig.postcode nullable...")
    op.alter_column(
        "trig",
        "postcode",
        existing_type=sa.String(10),
        nullable=True,
    )
    logger.info("Made trig.postcode nullable")

    # 3. Add foreign key constraint: trig.postcode -> postcodes.code
    # First, we need to set any invalid postcodes to NULL
    # (postcodes that don't exist in the postcodes table)
    logger.info("Setting invalid postcodes to NULL before adding FK constraint...")
    result = conn.execute(
        sa.text(
            """
            UPDATE trig
            SET postcode = NULL
            WHERE postcode IS NOT NULL
              AND postcode NOT IN (SELECT code FROM postcodes)
            """
        )
    )
    logger.info("Set %d invalid postcodes to NULL", result.rowcount)

    logger.info("Adding foreign key constraint trig.postcode -> postcodes.code...")
    op.create_foreign_key(
        "fk_trig_postcode_postcodes",
        "trig",
        "postcodes",
        ["postcode"],
        ["code"],
        ondelete="SET NULL",
    )
    logger.info("Added FK constraint")

    # 4. Add spatial index on postcodes table for efficient nearest-postcode queries
    # Check if index already exists first
    logger.info("Adding spatial index on postcodes(lat, long)...")
    result = conn.execute(
        sa.text(
            """
            SELECT 1 FROM pg_indexes
            WHERE tablename = 'postcodes'
              AND indexname = 'idx_postcodes_lat_long'
            """
        )
    )
    if result.fetchone() is None:
        op.create_index(
            "idx_postcodes_lat_long",
            "postcodes",
            ["lat", "long"],
            unique=False,
        )
        logger.info("Created spatial index idx_postcodes_lat_long")
    else:
        logger.info("Spatial index idx_postcodes_lat_long already exists")


def downgrade() -> None:
    """
    Downgrade schema:
    1. Drop spatial index
    2. Drop FK constraint
    3. Make postcode NOT NULL again (with empty string default)
    4. Re-add postcode6 column
    """
    conn = op.get_bind()

    # 1. Drop spatial index
    op.drop_index("idx_postcodes_lat_long", table_name="postcodes")

    # 2. Drop FK constraint
    op.drop_constraint("fk_trig_postcode_postcodes", "trig", type_="foreignkey")

    # 3. Make postcode NOT NULL again
    # First set NULL values to empty string
    conn.execute(
        sa.text(
            """
            UPDATE trig
            SET postcode = ''
            WHERE postcode IS NULL
            """
        )
    )
    op.alter_column(
        "trig",
        "postcode",
        existing_type=sa.String(10),
        nullable=False,
    )

    # 4. Re-add postcode6 column (empty - data is lost)
    op.add_column(
        "trig",
        sa.Column("postcode6", sa.String(6), nullable=False, server_default=""),
    )
    # Remove the server default after adding the column
    op.alter_column("trig", "postcode6", server_default=None)
