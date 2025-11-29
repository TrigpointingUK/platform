"""update_epoch_tlog_dates_from_timestamp

Revision ID: 42228d2858b0
Revises: 568ea59132cc
Create Date: 2025-11-28 18:00:43.497357

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "42228d2858b0"
down_revision: Union[str, Sequence[str], None] = "568ea59132cc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Update tlog dates that are 1970-01-01 to use date from upd_timestamp.
    
    For rows where date is exactly 1970-01-01 (set by previous migration from NULL),
    extract the date component from upd_timestamp and use that instead.
    This provides more accurate dates based on when the log was last updated.
    
    Only updates rows where upd_timestamp is not NULL.
    """
    # Update date to the date component of upd_timestamp for rows with epoch date
    op.execute(
        sa.text(
            "UPDATE tlog "
            "SET date = upd_timestamp::date "
            "WHERE date = '1970-01-01' AND upd_timestamp IS NOT NULL"
        )
    )


def downgrade() -> None:
    """Revert dates back to 1970-01-01.
    
    WARNING: This cannot accurately restore the original state since we don't know
    which rows originally had 1970-01-01 as their date versus which were updated.
    This migration is effectively irreversible without data loss.
    """
    # Cannot reliably revert this migration
    # Leaving as no-op since we don't have a way to identify which dates
    # were originally 1970-01-01 vs updated from upd_timestamp
    pass
