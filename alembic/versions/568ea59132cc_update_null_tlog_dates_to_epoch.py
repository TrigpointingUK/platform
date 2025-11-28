"""update_null_tlog_dates_to_epoch

Revision ID: 568ea59132cc
Revises: 1fa5427f5d6e
Create Date: 2025-11-28 17:53:04.921628

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "568ea59132cc"
down_revision: Union[str, Sequence[str], None] = "1fa5427f5d6e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update null date values in tlog table to 1970-01-01.
    
    During migration from legacy MySQL, date values that were '0000-00-00' became NULL.
    This migration sets those NULL dates to 1970-01-01 as a sensible epoch date.
    """
    # Update all rows in tlog where date is NULL to 1970-01-01
    op.execute(
        sa.text(
            "UPDATE tlog SET date = '1970-01-01' WHERE date IS NULL"
        )
    )


def downgrade() -> None:
    """Revert dates from 1970-01-01 back to NULL.
    
    WARNING: This will set all dates that are exactly 1970-01-01 back to NULL.
    This may affect rows that legitimately had this date set.
    """
    # Revert 1970-01-01 dates back to NULL
    op.execute(
        sa.text(
            "UPDATE tlog SET date = NULL WHERE date = '1970-01-01'"
        )
    )
