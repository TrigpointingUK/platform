"""schedule pg_cron job for trig_area materialized view refresh

Revision ID: e9f5a7b34d02
Revises: d7e4f8a23c91
Create Date: 2025-12-02

This migration schedules a daily refresh of the trig_area_mv materialized view.
The view precomputes which areas contain each trigpoint, so it only needs
refreshing when:
- New area boundaries are loaded
- Trigpoint locations change (rare)

A daily refresh at 3 AM is sufficient for this use case.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

JOB_NAME = "refresh_trig_area_mv_daily"
CRON_EXPRESSION = "0 3 * * *"  # Daily at 3 AM
REFRESH_SQL = "REFRESH MATERIALIZED VIEW CONCURRENTLY trig_area_mv"


# revision identifiers, used by Alembic.
revision: str = "e9f5a7b34d02"
down_revision: Union[str, Sequence[str], None] = "d7e4f8a23c91"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _cron_available(connection) -> bool:
    """Check if pg_cron extension is installed."""
    check_stmt = sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'cron')"
    )
    return bool(connection.execute(check_stmt).scalar())


def _unschedule_job(connection) -> None:
    """Remove any existing job with this name."""
    stmt = sa.text(
        """
        SELECT cron.unschedule(jobid)
        FROM cron.job
        WHERE jobname = :jobname
        """
    ).bindparams(jobname=JOB_NAME)
    connection.execute(stmt)


def upgrade() -> None:
    """Schedule a pg_cron job to refresh the trig_area_mv daily at 3 AM."""
    connection = op.get_bind()
    if not _cron_available(connection):
        logger.warning(
            "Skipping pg_cron scheduling because the cron schema was not found. "
            "Install/enable pg_cron, then rerun this migration."
        )
        return

    _unschedule_job(connection)
    stmt = sa.text("SELECT cron.schedule(:jobname, :cron, :command)").bindparams(
        jobname=JOB_NAME,
        cron=CRON_EXPRESSION,
        command=REFRESH_SQL,
    )
    connection.execute(stmt)


def downgrade() -> None:
    """Remove the pg_cron refresh job."""
    connection = op.get_bind()
    if not _cron_available(connection):
        logger.warning(
            "pg_cron not installed; nothing to unschedule during downgrade."
        )
        return
    _unschedule_job(connection)
