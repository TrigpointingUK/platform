"""drop tquery table

Revision ID: 4ea06b786808
Revises: b312d005cf5e
Create Date: 2026-01-10 16:11:59.942518

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "4ea06b786808"
down_revision: Union[str, Sequence[str], None] = "b312d005cf5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_table("tquery")


def downgrade() -> None:
    """Downgrade schema."""
    op.create_table(
        "tquery",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("type", sa.CHAR(length=1), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("sql_from", sa.Text(), nullable=False),
        sa.Column("sql_where", sa.Text(), nullable=False),
        sa.Column("sql_having", sa.Text(), nullable=False),
        sa.Column("sql_order", sa.Text(), nullable=False),
        sa.Column("osgb_eastings", sa.Integer(), nullable=False),
        sa.Column("osgb_northings", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("system_ind", sa.CHAR(length=1), nullable=False),
        sa.Column("upd_timestamp", sa.DateTime(), nullable=True),
        sa.Column("crt_timestamp", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_tquery_id"), "tquery", ["id"], unique=False)
    op.create_index(op.f("ix_tquery_user_id"), "tquery", ["user_id"], unique=False)
