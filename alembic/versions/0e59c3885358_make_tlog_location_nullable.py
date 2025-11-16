"""make_tlog_location_nullable

Revision ID: 0e59c3885358
Revises:
Create Date: 2025-11-16 22:34:40.523432

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0e59c3885358"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema - make tlog location fields nullable.
    
    Allow logs without specific location data (osgb_eastings, osgb_northings, osgb_gridref).
    Original SQL migration: api/migrations/001_make_tlog_location_nullable.sql
    Date: 2025-11-04
    """
    # Make location fields nullable in tlog table using ALTER COLUMN for PostgreSQL
    op.alter_column('tlog', 'osgb_eastings', existing_type=sa.Integer(), nullable=True)
    op.alter_column('tlog', 'osgb_northings', existing_type=sa.Integer(), nullable=True)
    op.alter_column('tlog', 'osgb_gridref', existing_type=sa.String(14), nullable=True)


def downgrade() -> None:
    """Downgrade schema - revert tlog location fields to NOT NULL.
    
    WARNING: This will fail if any rows have NULL values in these columns.
    """
    # Revert location fields to NOT NULL
    op.alter_column('tlog', 'osgb_eastings', existing_type=sa.Integer(), nullable=False)
    op.alter_column('tlog', 'osgb_northings', existing_type=sa.Integer(), nullable=False)
    op.alter_column('tlog', 'osgb_gridref', existing_type=sa.String(14), nullable=False)
