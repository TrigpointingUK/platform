"""add_legal_message_to_trig

Add a TEXT column for storing optional legal/access messages for trigpoints.
This field stores HTML content from a WYSIWYG editor.

Revision ID: a2b3c4d5e6f7
Revises: 92954a8373b5
Create Date: 2026-01-12 10:00:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, Sequence[str], None] = "273f029599fb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add legal_message column to trig table."""
    op.add_column(
        "trig",
        sa.Column(
            "legal_message",
            sa.Text(),
            nullable=True,
            comment="Optional legal/access message displayed on trig detail page (HTML)",
        ),
    )


def downgrade() -> None:
    """Remove legal_message column from trig table."""
    op.drop_column("trig", "legal_message")

