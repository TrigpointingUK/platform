"""default archive_format to CSV+HTML viewer (R)

Revision ID: b8c9d0e1f2a3
Revises: a7b8c9d0e1f2
Create Date: 2026-04-14

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "a7b8c9d0e1f2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "user",
        "archive_format",
        existing_type=sa.CHAR(length=1),
        server_default="R",
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user",
        "archive_format",
        existing_type=sa.CHAR(length=1),
        server_default="C",
        existing_nullable=False,
    )
