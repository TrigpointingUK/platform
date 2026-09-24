"""uppercase lowercase log condition codes

Revision ID: 730cbacea27f
Revises: c9d0e1f2a3b4
Create Date: 2026-09-24 17:05:00.000000

85 published logs in both tuk_production and tuk_staging have condition 'p'
(lowercase), dated 2003-04-26 to 2011-10-15 - written by the old MySQL site,
whose case-insensitive collation treated 'p' as 'P' (Inaccessible). Postgres
compares case-sensitively, so those logs match no row in the condition table:
they drop out of condition filters and miss the condition's name and icon.

Rather than hard-coding 'p', this uppercases any tlog.condition whose uppercase
form is a valid condition code, so the same migration is correct in both
databases. trig.condition was checked and has no invalid codes.

tlog.upd_timestamp is preserved. The set_upd_timestamp_utc trigger would
otherwise stamp these logs with today's date, and upd_timestamp is used as a
"last active" signal when choosing between duplicate accounts
(api/crud/user.py, api/crud/user_merge.py) - 49 long-inactive users would
suddenly look active. The trigger is disabled only around the UPDATE; DDL is
transactional in Postgres, so a failure rolls the trigger state back too.

The trigger isn't present in every database (staging has lost its
upd_timestamp triggers), so it is only toggled if it exists and is enabled.

Re-running is a no-op (0 rows). Row counts are logged for the
`make migrate-*` audit trail.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "730cbacea27f"
down_revision: Union[str, Sequence[str], None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

_TRIGGER = "set_upd_timestamp_utc"

# Codes that are only invalid because of their case
_CASE_ONLY_INVALID = """
    condition <> upper(condition)
    AND upper(condition) IN (SELECT code FROM condition)
"""


def upgrade() -> None:
    """Uppercase tlog.condition codes that are only invalid because of case."""
    conn = op.get_bind()

    breakdown = conn.execute(sa.text(f"""
            SELECT condition, count(*) AS logs
            FROM tlog
            WHERE {_CASE_ONLY_INVALID}
            GROUP BY condition
            ORDER BY condition
            """)).fetchall()
    for row in breakdown:
        logger.info(
            "tlog.condition %r -> %r: %d log(s) to fix",
            row.condition,
            row.condition.upper(),
            row.logs,
        )

    # Keep each log's upd_timestamp - see the module docstring. 'O' means the
    # trigger is enabled; None means tlog has no such trigger.
    trigger_state = conn.execute(
        sa.text("""
            SELECT tgenabled
            FROM pg_trigger
            WHERE tgrelid = 'tlog'::regclass AND tgname = :name
            """),
        {"name": _TRIGGER},
    ).scalar()
    toggle_trigger = trigger_state == "O"
    logger.info(
        "tlog trigger %s: %s",
        _TRIGGER,
        (
            "enabled - disabling during the update"
            if toggle_trigger
            else "not present or not enabled - nothing to disable"
        ),
    )

    if toggle_trigger:
        op.execute(f"ALTER TABLE tlog DISABLE TRIGGER {_TRIGGER}")
    result = conn.execute(sa.text(f"""
            UPDATE tlog
            SET condition = upper(condition)
            WHERE {_CASE_ONLY_INVALID}
            """))
    if toggle_trigger:
        op.execute(f"ALTER TABLE tlog ENABLE TRIGGER {_TRIGGER}")
    logger.info("Uppercased tlog.condition: %d row(s) updated", result.rowcount)

    remaining = conn.execute(sa.text("""
            SELECT count(*)
            FROM tlog l
            LEFT JOIN condition c ON c.code = l.condition
            WHERE l.condition IS NOT NULL AND c.code IS NULL
            """)).scalar()
    logger.info("tlog rows with a condition not in the condition table: %d", remaining)


def downgrade() -> None:
    """No-op: the lowercase codes were never valid, so there is nothing to restore.

    Which logs were lowercase isn't recorded, and putting an invalid code back
    would only reintroduce the bug. Downgrading past this revision leaves the
    data as corrected.
    """
    logger.info("No-op downgrade: tlog.condition codes stay uppercase")
