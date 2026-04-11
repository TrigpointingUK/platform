"""add partial indexes and trigram text search indexes

Revision ID: afac436783c8
Revises: dc5f35bace81
Create Date: 2026-04-10

1) Partial index on tphoto: nearly every query filters deleted_ind != 'Y'
   (only 0.1% of photos are deleted).  Replace the full tlog_id index with
   a partial one, and drop the useless full index on deleted_ind (only 2
   distinct values = terrible selectivity).

2) pg_trgm GIN indexes for ILIKE %pattern% and regex (~*) text searches on
   the most frequently searched columns.  The existing btree indexes remain
   for exact match, prefix LIKE, and ORDER BY.

3) No partial index for trig.status_id: production has only 1 deleted trig
   out of 26,971 — the filter excludes essentially zero rows, so a partial
   index would be the same size as the full index.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

revision: str = "afac436783c8"
down_revision: Union[str, Sequence[str], None] = "dc5f35bace81"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _conn() -> sa.engine.Connection:
    return op.get_bind()


def _has_index(index_name: str) -> bool:
    return bool(
        _conn()
        .execute(
            sa.text(
                "SELECT 1 FROM pg_indexes "
                "WHERE schemaname = 'public' AND indexname = :idx"
            ),
            {"idx": index_name},
        )
        .scalar()
    )


def _has_extension(name: str) -> bool:
    return bool(
        _conn()
        .execute(
            sa.text("SELECT 1 FROM pg_extension WHERE extname = :name"),
            {"name": name},
        )
        .scalar()
    )


def _drop_index_if_exists(index_name: str, table: str) -> None:
    if _has_index(index_name):
        op.drop_index(index_name, table_name=table)
        logger.info("Dropped index %s on %s", index_name, table)


def _create_index_if_missing(
    index_name: str,
    table: str,
    columns: list[str],
    **kw: object,
) -> None:
    if not _has_index(index_name):
        op.create_index(index_name, table, columns, **kw)
        logger.info("Created index %s on %s(%s)", index_name, table, columns)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. tphoto partial index
    # ------------------------------------------------------------------

    # Replace full tlog_id index with partial (active photos only)
    _drop_index_if_exists("tlog_id", "tphoto")
    _create_index_if_missing(
        "idx_tphoto_tlog_id_active",
        "tphoto",
        ["tlog_id"],
        postgresql_where=sa.text("deleted_ind != 'Y'"),
    )

    # Drop useless full index on deleted_ind (2 distinct values)
    _drop_index_if_exists("idx_tphoto_deleted_ind", "tphoto")

    # ------------------------------------------------------------------
    # 2. pg_trgm GIN indexes for text search
    # ------------------------------------------------------------------

    if not _has_extension("pg_trgm"):
        op.execute("CREATE EXTENSION pg_trgm")
        logger.info("Created extension pg_trgm")

    # user.name — used by ILIKE %pattern% in user search, locations search
    _create_index_if_missing(
        "ix_user_name_trgm",
        "user",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    # trig.name — used by ILIKE %pattern% in trig search, locations search
    _create_index_if_missing(
        "ix_trig_name_trgm",
        "trig",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    # town.name — used by ILIKE %pattern% in location search
    # town.name is character(25) (fixed-length); gin_trgm_ops requires
    # text/varchar, so we cast in an expression index.
    if not _has_index("ix_town_name_trgm"):
        op.execute(
            "CREATE INDEX ix_town_name_trgm ON town "
            "USING gin ((name::text) gin_trgm_ops)"
        )
        logger.info("Created index ix_town_name_trgm on town(name::text)")

    # tlog.comment — used by ILIKE %pattern% and regex (~*) in log search
    _create_index_if_missing(
        "ix_tlog_comment_trgm",
        "tlog",
        ["comment"],
        postgresql_using="gin",
        postgresql_ops={"comment": "gin_trgm_ops"},
    )


def downgrade() -> None:
    _drop_index_if_exists("ix_tlog_comment_trgm", "tlog")
    _drop_index_if_exists("ix_town_name_trgm", "town")
    _drop_index_if_exists("ix_trig_name_trgm", "trig")
    _drop_index_if_exists("ix_user_name_trgm", "user")

    # Restore full tphoto indexes
    _drop_index_if_exists("idx_tphoto_tlog_id_active", "tphoto")
    _create_index_if_missing("tlog_id", "tphoto", ["tlog_id"])
    _create_index_if_missing("idx_tphoto_deleted_ind", "tphoto", ["deleted_ind"])
