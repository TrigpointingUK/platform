"""validate_foreign_key_constraints

Revision ID: 96c8c6061f3a
Revises: b7bd84b73c61
Create Date: 2026-01-10 17:39:52.344329

"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

logger = logging.getLogger("alembic.runtime.migration")


# revision identifiers, used by Alembic.
revision: str = "96c8c6061f3a"
down_revision: Union[str, Sequence[str], None] = "b7bd84b73c61"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _qi(identifier: str) -> str:
    """Quote a SQL identifier for PostgreSQL."""
    return '"' + identifier.replace('"', '""') + '"'


def _is_unvalidated_fk(conn, name: str) -> bool:
    row = conn.execute(
        sa.text("SELECT convalidated FROM pg_constraint WHERE conname = :name"),
        {"name": name},
    ).one_or_none()
    if row is None:
        return False
    return row[0] is False


def _validate_fk(conn, *, table: str, constraint: str) -> None:
    if not _is_unvalidated_fk(conn, constraint):
        return

    logger.info("Validating FK constraint %s on %s", constraint, table)
    op.execute(
        sa.text(
            f"""
            ALTER TABLE {_qi(table)}
            VALIDATE CONSTRAINT {_qi(constraint)}
            """
        )
    )


def upgrade() -> None:
    """Validate all FK constraints added as NOT VALID in 53992fd8a62b."""
    conn = op.get_bind()

    # Validate in a deterministic order (parent-ish tables first, then join tables).
    for table, constraint in [
        ("tlog", "fk_tlog_trig_id__trig_id"),
        ("tlog", "fk_tlog_user_id__user_id"),
        ("tphoto", "fk_tphoto_tlog_id__tlog_id"),
        ("tphoto", "fk_tphoto_server_id__server_id"),
        ("tphotovote", "fk_tphotovote_tphoto_id__tphoto_id"),
        ("tphotovote", "fk_tphotovote_user_id__user_id"),
        ("trig", "fk_trig_status_id__status_id"),
        ("trig", "fk_trig_crt_user_id__user_id"),
        ("trig", "fk_trig_admin_user_id__user_id"),
        ("attr", "fk_attr_attrsource_id__attrsource_id"),
        ("attrset", "fk_attrset_trig_id__trig_id"),
        ("attrset", "fk_attrset_attrsource_id__attrsource_id"),
        ("attrval", "fk_attrval_attr_id__attr_id"),
        ("attrset_attrval", "fk_attrset_attrval_attrset_id__attrset_id"),
        ("attrset_attrval", "fk_attrset_attrval_attrval_id__attrval_id"),
        ("trigstats", "fk_trigstats_id__trig_id"),
    ]:
        _validate_fk(conn, table=table, constraint=constraint)


def downgrade() -> None:
    """
    Downgrade schema.

    PostgreSQL does not support "un-validating" a constraint; leaving as a no-op.
    """
    return
