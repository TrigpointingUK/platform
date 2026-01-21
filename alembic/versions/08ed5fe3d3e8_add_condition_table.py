"""add_condition_table

Revision ID: 08ed5fe3d3e8
Revises: b3c4d5e6f7a8
Create Date: 2026-01-21 21:34:59.136537

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "08ed5fe3d3e8"
down_revision: Union[str, Sequence[str], None] = "b3c4d5e6f7a8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create the condition lookup table for trigpoint conditions."""
    op.create_table(
        "condition",
        sa.Column("code", sa.CHAR(1), primary_key=True, nullable=False),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("icon_file", sa.String(100), nullable=True),
        sa.Column("trig_colour", sa.String(20), nullable=True),
        sa.Column("log_colour", sa.String(20), nullable=True),
        sa.Column("similar_codes", sa.String(10), nullable=True),
        sa.Column("wiki_url", sa.String(255), nullable=True),
        sa.Column("sort_order", sa.SmallInteger, nullable=False),
    )

    # Create index on sort_order for efficient ordering
    op.create_index("ix_condition_sort_order", "condition", ["sort_order"])


def downgrade() -> None:
    """Drop the condition table."""
    op.drop_index("ix_condition_sort_order", table_name="condition")
    op.drop_table("condition")
