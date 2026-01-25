"""add tlog status column for draft logs

Revision ID: a5b6c7d8e9f0
Revises: d1334ccc0ad2
Create Date: 2026-01-25 12:00:00.000000

"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "a5b6c7d8e9f0"
down_revision: Union[str, Sequence[str], None] = "d1334ccc0ad2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

JOB_NAME = "cleanup_abandoned_draft_logs"
CRON_EXPRESSION = "0 * * * *"  # Every hour
CLEANUP_SQL = "DELETE FROM tlog WHERE status = 'D' AND upd_timestamp < NOW() - INTERVAL '24 hours'"


def _cron_available(connection) -> bool:
    """Check if pg_cron extension is available."""
    check_stmt = sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'cron')"
    )
    return bool(connection.execute(check_stmt).scalar())


def _unschedule_job(connection) -> None:
    """Remove any existing job with our name."""
    stmt = sa.text(
        """
        SELECT cron.unschedule(jobid)
        FROM cron.job
        WHERE jobname = :jobname
        """
    ).bindparams(jobname=JOB_NAME)
    connection.execute(stmt)


def upgrade() -> None:
    """Add status column to tlog table and schedule cleanup job."""
    connection = op.get_bind()

    # Add status column with default 'P' (Published)
    # All existing logs are published, new logs default to published unless explicitly draft
    op.add_column(
        "tlog",
        sa.Column(
            "status",
            sa.CHAR(1),
            nullable=False,
            server_default="P",
        ),
    )

    # Add index for efficient filtering by status
    op.create_index("ix_tlog_status", "tlog", ["status"])

    # Log how many rows were updated (all existing rows get 'P')
    result = connection.execute(sa.text("SELECT COUNT(*) FROM tlog"))
    row_count = result.scalar()
    logger.info(f"Added status column to tlog table. {row_count} existing rows set to 'P' (Published)")

    # Schedule pg_cron cleanup job for abandoned drafts
    if _cron_available(connection):
        _unschedule_job(connection)
        stmt = sa.text("SELECT cron.schedule(:jobname, :cron, :command)").bindparams(
            jobname=JOB_NAME,
            cron=CRON_EXPRESSION,
            command=CLEANUP_SQL,
        )
        connection.execute(stmt)
        logger.info(f"Scheduled pg_cron job '{JOB_NAME}' to clean up abandoned drafts hourly")
    else:
        logger.warning(
            "Skipping pg_cron scheduling because the cron schema was not found. "
            "Install/enable pg_cron to automatically clean up abandoned draft logs."
        )


def downgrade() -> None:
    """Remove status column and cleanup job."""
    connection = op.get_bind()

    # Unschedule the cleanup job if pg_cron is available
    if _cron_available(connection):
        _unschedule_job(connection)
        logger.info(f"Unscheduled pg_cron job '{JOB_NAME}'")
    else:
        logger.warning("pg_cron not installed; nothing to unschedule during downgrade.")

    # Remove the index
    op.drop_index("ix_tlog_status", table_name="tlog")

    # Remove the status column
    op.drop_column("tlog", "status")
    logger.info("Removed status column from tlog table")

