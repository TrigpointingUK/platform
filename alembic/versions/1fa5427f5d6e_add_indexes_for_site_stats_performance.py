"""add_indexes_for_site_stats_performance

Revision ID: 1fa5427f5d6e
Revises: d3c5d7b8f4ee
Create Date: 2025-11-24 14:17:32.527465

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy import event


# revision identifiers, used by Alembic.
revision: str = "1fa5427f5d6e"
down_revision: Union[str, Sequence[str], None] = "d3c5d7b8f4ee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add database indexes to improve /v1/stats/site endpoint performance.
    
    These indexes support the date/timestamp filtering queries used to calculate
    recent activity statistics (7-day log count, 30-day user count).
    
    Note: CREATE INDEX CONCURRENTLY requires running outside a transaction.
    We handle this by committing the current transaction and using autocommit mode.
    """
    # Get the connection
    connection = op.get_bind()
    
    # Commit any existing transaction
    if connection.in_transaction():
        connection.commit()
    
    # Set isolation level to autocommit for CREATE INDEX CONCURRENTLY
    connection.execution_options(isolation_level="AUTOCOMMIT")
    
    # Index on tlog.upd_timestamp for recent logs query
    # This speeds up: SELECT COUNT(*) FROM tlog WHERE upd_timestamp >= :seven_days_ago
    connection.execute(
        sa.text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tlog_upd_timestamp "
            "ON tlog (upd_timestamp)"
        )
    )
    
    # Index on user.crt_date for recent users query
    # This speeds up: SELECT COUNT(*) FROM user WHERE crt_date >= :thirty_days_ago
    connection.execute(
        sa.text(
            'CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_user_crt_date '
            'ON "user" (crt_date)'
        )
    )
    
    # Index on tphoto.deleted_ind for active photos query
    # This speeds up: SELECT COUNT(*) FROM tphoto WHERE deleted_ind != 'Y'
    connection.execute(
        sa.text(
            "CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_tphoto_deleted_ind "
            "ON tphoto (deleted_ind)"
        )
    )


def downgrade() -> None:
    """Remove the performance indexes."""
    op.drop_index("idx_tlog_upd_timestamp", table_name="tlog", if_exists=True)
    op.drop_index("idx_user_crt_date", table_name="user", if_exists=True)
    op.drop_index("idx_tphoto_deleted_ind", table_name="tphoto", if_exists=True)
