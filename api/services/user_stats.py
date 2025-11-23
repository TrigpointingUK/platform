"""Helpers for maintaining derived user statistics objects such as materialised views."""

from sqlalchemy import text
from sqlalchemy.orm import Session


def refresh_user_activity_summary(db: Session, *, concurrently: bool = False) -> None:
    """Refresh the user activity summary materialised view.

    Parameters
    ----------
    db:
        SQLAlchemy session/connection used to issue the refresh.
    concurrently:
        When True attempt a concurrent refresh. Concurrent refresh cannot run inside
        a transaction block, so this should only be used in dedicated scripts.
    """

    clause = (
        "REFRESH MATERIALIZED VIEW CONCURRENTLY"
        if concurrently
        else "REFRESH MATERIALIZED VIEW"
    )
    db.execute(text(f"{clause} user_activity_summary"))
    db.commit()
