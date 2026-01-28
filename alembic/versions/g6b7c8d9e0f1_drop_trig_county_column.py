"""drop trig.county column

Revision ID: g6b7c8d9e0f1
Revises: f5a6b7c8d9e0
Create Date: 2026-01-27

This migration drops the deprecated trig.county column. County information
is now derived from the trig_area table joined with area where area_type_id = 7
(county_1991).

The column data is preserved in a backup before dropping for safety.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "g6b7c8d9e0f1"
down_revision: Union[str, Sequence[str], None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Drop the trig.county column after backing up the data."""
    connection = op.get_bind()

    # Create a backup table with trig_id and county values
    logger.info("Creating backup of trig.county data...")
    connection.execute(
        sa.text(
            """
            CREATE TABLE IF NOT EXISTS _trig_county_backup AS
            SELECT id AS trig_id, county
            FROM trig
            WHERE county IS NOT NULL AND county != ''
            """
        )
    )

    backup_count = connection.execute(
        sa.text("SELECT COUNT(*) FROM _trig_county_backup")
    ).scalar()
    logger.info(f"Backed up {backup_count} county values to _trig_county_backup")

    # Drop the county column
    logger.info("Dropping trig.county column...")
    op.drop_column("trig", "county")

    logger.info("Migration complete: trig.county column dropped")


def downgrade() -> None:
    """Restore the trig.county column from backup."""
    connection = op.get_bind()

    # Re-add the county column
    logger.info("Re-adding trig.county column...")
    op.add_column(
        "trig",
        sa.Column("county", sa.String(20), nullable=False, server_default=""),
    )

    # Restore data from backup if it exists
    backup_exists = connection.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM information_schema.tables
                WHERE table_name = '_trig_county_backup'
            )
            """
        )
    ).scalar()

    if backup_exists:
        logger.info("Restoring county data from backup...")
        result = connection.execute(
            sa.text(
                """
                UPDATE trig t
                SET county = b.county
                FROM _trig_county_backup b
                WHERE t.id = b.trig_id
                """
            )
        )
        logger.info(f"Restored {result.rowcount} county values from backup")

    # Remove the server default after restoration
    op.alter_column("trig", "county", server_default=None)

    logger.info("Downgrade complete: trig.county column restored")

