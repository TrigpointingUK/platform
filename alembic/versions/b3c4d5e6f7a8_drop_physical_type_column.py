"""Drop physical_type column from trig table.

The physical_type column is now redundant as all trigs have type_id populated,
which links to trig_type.name for the type display name.

Revision ID: b3c4d5e6f7a8
Revises: 
Create Date: 2026-01-20 14:10:00.000000

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b3c4d5e6f7a8"
down_revision: Union[str, None] = "2560d7a0ad69"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


def upgrade() -> None:
    """Drop the physical_type column from trig table."""
    # Log the migration
    conn = op.get_bind()
    
    # First, verify all trigs have type_id populated
    result = conn.execute(
        sa.text("SELECT COUNT(*) FROM trig WHERE type_id IS NULL")
    )
    null_count = result.scalar()
    
    if null_count > 0:
        logger.warning(
            f"Found {null_count} trigs with NULL type_id. "
            "These will lose physical_type information."
        )
    
    # Drop the column
    op.drop_column("trig", "physical_type")
    logger.info("Dropped physical_type column from trig table")


def downgrade() -> None:
    """Re-add the physical_type column and populate from trig_type.name."""
    # Add the column back
    op.add_column(
        "trig",
        sa.Column("physical_type", sa.String(25), nullable=True),
    )
    
    # Populate from trig_type.name
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            UPDATE trig 
            SET physical_type = tt.name
            FROM trig_type tt
            WHERE trig.type_id = tt.id
        """)
    )
    logger.info(f"Populated physical_type for {result.rowcount} rows from trig_type.name")
    
    # Set default for any remaining nulls
    result = conn.execute(
        sa.text("""
            UPDATE trig 
            SET physical_type = 'Unknown'
            WHERE physical_type IS NULL
        """)
    )
    if result.rowcount > 0:
        logger.info(f"Set physical_type to 'Unknown' for {result.rowcount} rows with NULL type_id")
    
    # Make column not nullable
    op.alter_column(
        "trig",
        "physical_type",
        nullable=False,
    )

