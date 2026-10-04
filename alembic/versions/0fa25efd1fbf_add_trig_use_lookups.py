"""add historic use and recent use lookups

Revision ID: 0fa25efd1fbf
Revises: b7cfe27fcd3e
Create Date: 2026-10-04 16:00:00.000000

trig.historic_use and trig.current_use ("Recent use" in the UI) are free
strings. Until now the allowed values were hardcoded in the SPA's trig
create/edit forms, and the filter chips listed whatever DISTINCT values were
on the trig table, so adding a value meant a code change or SQL.

- trig_historic_use / trig_current_use: lookups of the allowed values, with an
  optional description and a sort_order, maintained from the admin screen.
- No foreign key from trig: the columns stay plain strings and the API keeps
  them in step (a rename updates the trigs, a value in use can't be deleted,
  trig create/edit only accept listed values).

Each lookup is seeded with the values the forms offered, in the forms' order,
then any other non-blank value already on a trig (logged with its trig count,
appended in alphabetical order), so every value in use can be managed.
Blank/NULL values are counted in the log but not seeded.

Row counts are logged for the `make migrate-*` audit trail.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0fa25efd1fbf"
down_revision: Union[str, Sequence[str], None] = "b7cfe27fcd3e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# (table, trig column, name length, values offered by the SPA forms)
_LOOKUPS = [
    (
        "trig_historic_use",
        "historic_use",
        30,
        [
            "none",
            "Primary",
            "Secondary",
            "3rd order",
            "4th order",
            "Fundamental",
            "Intersection",
        ],
    ),
    (
        "trig_current_use",
        "current_use",
        25,
        ["none", "Passive station", "Active station"],
    ),
]


def upgrade() -> None:
    conn = op.get_bind()

    for table, column, length, seed in _LOOKUPS:
        op.create_table(
            table,
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(length=length), nullable=False, unique=True),
            sa.Column("description", sa.String(length=255), nullable=True),
            sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        )

        for i, name in enumerate(seed):
            result = conn.execute(
                sa.text(
                    f"INSERT INTO {table} (name, sort_order) VALUES (:name, :sort)"
                ),
                {"name": name, "sort": i * 10},
            )
            logger.info("Inserted %s %r: %d row(s)", table, name, result.rowcount)

        extras = conn.execute(sa.text(f"""
                SELECT t.{column} AS name, count(*) AS trigs
                FROM trig t
                WHERE trim(coalesce(t.{column}, '')) <> ''
                  AND NOT EXISTS (SELECT 1 FROM {table} u WHERE u.name = t.{column})
                GROUP BY t.{column}
                ORDER BY t.{column}
                """)).fetchall()
        for i, row in enumerate(extras, start=len(seed)):
            result = conn.execute(
                sa.text(
                    f"INSERT INTO {table} (name, sort_order) VALUES (:name, :sort)"
                ),
                {"name": row.name, "sort": i * 10},
            )
            logger.info(
                "Inserted %s %r (already on %d trig(s)): %d row(s)",
                table,
                row.name,
                row.trigs,
                result.rowcount,
            )

        blank = conn.execute(
            sa.text(
                f"SELECT count(*) FROM trig WHERE trim(coalesce({column}, '')) = ''"
            )
        ).scalar()
        logger.info("Trigs with blank %s (not seeded): %d", column, blank)

        counts = conn.execute(sa.text(f"""
                SELECT u.name, count(t.id) AS trigs
                FROM {table} u
                LEFT JOIN trig t ON t.{column} = u.name
                GROUP BY u.name, u.sort_order
                ORDER BY u.sort_order
                """)).fetchall()
        for row in counts:
            logger.info("Trigs with %s %r: %d", column, row.name, row.trigs)


def downgrade() -> None:
    op.drop_table("trig_current_use")
    op.drop_table("trig_historic_use")
