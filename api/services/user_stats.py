"""Helpers for maintaining derived user statistics objects such as materialised views."""

import logging

from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def refresh_user_activity_summary(db: Session, *, concurrently: bool = True) -> None:
    """Refresh the user activity summary materialised view.

    Parameters
    ----------
    db:
        SQLAlchemy session/connection used to issue the refresh.
    concurrently:
        When True (default) attempt a concurrent refresh first. Concurrent refresh
        allows reads to continue during the refresh, preventing lock contention in
        parallel test environments. Falls back to non-concurrent if concurrent fails
        (e.g., when the view is empty or not yet populated).

    Notes
    -----
    Concurrent refresh requires:
    - A unique index on the view (idx_user_activity_summary_user_id exists)
    - The view to contain at least one row
    - The connection to not be in a transaction block (we commit before refresh)

    In test environments with parallel workers (pytest-xdist), using concurrent
    refresh prevents the exclusive lock that would otherwise block all reads
    during the refresh operation.
    """
    # Ensure any pending transaction is committed before refresh
    # (REFRESH MATERIALIZED VIEW CONCURRENTLY cannot run inside a transaction)
    db.commit()

    if concurrently:
        try:
            db.execute(
                text("REFRESH MATERIALIZED VIEW CONCURRENTLY user_activity_summary")
            )
            db.commit()
            return
        except OperationalError as e:
            # Concurrent refresh can fail if:
            # - The view is empty (no rows to compare against)
            # - There's no unique index (but we have one)
            # Fall back to non-concurrent refresh
            db.rollback()
            logger.debug(
                "Concurrent refresh failed, falling back to non-concurrent: %s",
                str(e),
            )

    # Non-concurrent refresh (takes exclusive lock, blocks reads)
    db.execute(text("REFRESH MATERIALIZED VIEW user_activity_summary"))
    db.commit()
