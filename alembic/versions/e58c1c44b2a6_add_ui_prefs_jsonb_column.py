"""add_ui_prefs_jsonb_column

Add a JSONB column for UI preferences that don't affect backend logic.
Migrate existing distance_ind values into ui_prefs.

Revision ID: e58c1c44b2a6
Revises: d408a5e6b274
Create Date: 2025-12-08 18:09:42.927124

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "e58c1c44b2a6"
down_revision: Union[str, Sequence[str], None] = "d408a5e6b274"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add ui_prefs JSONB column and migrate distance_ind into it."""
    # Add ui_prefs column with empty JSON object as default
    op.add_column(
        "user",
        sa.Column(
            "ui_prefs",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            server_default="{}",
        ),
    )

    # Migrate existing distance_ind values into ui_prefs
    # Only migrate non-null values; default 'K' will be handled by frontend
    op.execute(
        """
        UPDATE "user"
        SET ui_prefs = jsonb_build_object('distance_ind', distance_ind)
        WHERE distance_ind IS NOT NULL AND distance_ind != ''
        """
    )


def downgrade() -> None:
    """Remove ui_prefs column."""
    op.drop_column("user", "ui_prefs")
