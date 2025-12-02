"""remove county table

Revision ID: a4dd9c096762
Revises: 46a1802864a1
Create Date: 2025-12-02 18:20:34.010912

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4dd9c096762"
down_revision: Union[str, Sequence[str], None] = "46a1802864a1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove the county reference table.

    The county table (72 rows) is a legacy lookup table that is no longer used:
    - No SQLAlchemy model exists for this table
    - The trig.county column stores county names as strings, not foreign keys
    - The coord2county table (which referenced county_id) was already dropped
    - No application code queries or joins to this table

    Date: 2025-12-02
    """
    op.drop_table("county")


def downgrade() -> None:
    """
    Restore the county reference table.

    WARNING: This recreates the table structure but does NOT restore data.
    The 72 rows of county data will be permanently lost.
    """
    op.create_table(
        "county",
        sa.Column("id", sa.SmallInteger, primary_key=True),
        sa.Column("name", sa.CHAR(50), nullable=False),
        sa.Column("country", sa.CHAR(1), nullable=False),
        sa.Column("type", sa.CHAR(1), nullable=False),
        sa.Column("pop", sa.Integer, nullable=False),
        sa.Column("hectares", sa.Integer, nullable=False),
        sa.Column("coast_ind", sa.CHAR(1), nullable=False),
        sa.Column("grey", sa.SmallInteger, nullable=False),
    )
