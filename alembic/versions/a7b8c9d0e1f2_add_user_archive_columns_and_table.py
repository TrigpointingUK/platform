"""add user archive columns and table

Revision ID: a7b8c9d0e1f2
Revises: b2f3a4c5d6e7
Create Date: 2026-04-12 12:00:00.000000

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, Sequence[str], None] = "b2f3a4c5d6e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "user",
        sa.Column("archive_frequency", sa.CHAR(1), nullable=False, server_default="N"),
    )
    op.add_column(
        "user",
        sa.Column("archive_format", sa.CHAR(1), nullable=False, server_default="C"),
    )

    op.create_table(
        "user_archive",
        sa.Column("id", sa.Integer, primary_key=True, autoincrement=True),
        sa.Column(
            "user_id",
            sa.Integer,
            sa.ForeignKey("user.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", sa.CHAR(1), nullable=False),
        sa.Column("frequency_at_send", sa.CHAR(1), nullable=False),
        sa.Column("format_at_send", sa.CHAR(1), nullable=False),
        sa.Column("log_count", sa.Integer, nullable=True),
        sa.Column("file_size_bytes", sa.BigInteger, nullable=True),
        sa.Column("error_message", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("user_archive")
    op.drop_column("user", "archive_format")
    op.drop_column("user", "archive_frequency")
