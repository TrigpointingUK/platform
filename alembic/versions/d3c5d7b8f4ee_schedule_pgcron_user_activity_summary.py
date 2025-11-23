"""schedule pg_cron job for user activity summary refresh

Revision ID: d3c5d7b8f4ee
Revises: e0101988ac27
Create Date: 2025-11-23 22:46:15.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

JOB_NAME = "refresh_user_activity_summary_every_5m"
CRON_EXPRESSION = "*/5 * * * *"
REFRESH_SQL = "REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary"


# revision identifiers, used by Alembic.
revision: str = "d3c5d7b8f4ee"
down_revision: Union[str, Sequence[str], None] = "e0101988ac27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _unschedule_job() -> None:
    stmt = sa.text(
        """
        SELECT cron.unschedule(jobid)
        FROM cron.job
        WHERE jobname = :jobname
        """
    ).bindparams(jobname=JOB_NAME)
    op.execute(stmt)


def upgrade() -> None:
    """Ensure a pg_cron job refreshes the materialised view every five minutes."""
    _unschedule_job()
    stmt = sa.text("SELECT cron.schedule(:jobname, :cron, :command)").bindparams(
        jobname=JOB_NAME,
        cron=CRON_EXPRESSION,
        command=REFRESH_SQL,
    )
    op.execute(stmt)


def downgrade() -> None:
    """Remove the pg_cron refresh job."""
    _unschedule_job()


