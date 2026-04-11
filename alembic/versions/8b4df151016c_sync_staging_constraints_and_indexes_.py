"""sync staging constraints and indexes with production

Revision ID: 8b4df151016c
Revises: 4a650a61fcbc
Create Date: 2026-04-10 21:54:40.150103

The staging database was restored from a MySQL dump that omitted most
PRIMARY KEY constraints, FOREIGN KEY constraints, and indexes.  Production
was migrated correctly and has all of these.

This migration idempotently adds every PK, FK, and index that production
has but staging lacks.  Running it on production is a safe no-op because
every helper checks for existence before acting.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

revision: str = "8b4df151016c"
down_revision: Union[str, Sequence[str], None] = "4a650a61fcbc"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _conn() -> sa.engine.Connection:
    return op.get_bind()


def _has_pk(table: str) -> bool:
    return bool(
        _conn()
        .execute(
            sa.text(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND table_name = :tbl "
                "  AND constraint_type = 'PRIMARY KEY'"
            ),
            {"tbl": table},
        )
        .scalar()
    )


def _has_unique_index(table: str, index_name: str) -> bool:
    return bool(
        _conn()
        .execute(
            sa.text(
                "SELECT 1 FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "  AND tablename = :tbl "
                "  AND indexname = :idx"
            ),
            {"tbl": table, "idx": index_name},
        )
        .scalar()
    )


def _has_fk(constraint_name: str) -> bool:
    return bool(
        _conn()
        .execute(
            sa.text(
                "SELECT 1 FROM information_schema.table_constraints "
                "WHERE table_schema = 'public' "
                "  AND constraint_name = :name "
                "  AND constraint_type = 'FOREIGN KEY'"
            ),
            {"name": constraint_name},
        )
        .scalar()
    )


def _has_index(index_name: str) -> bool:
    return bool(
        _conn()
        .execute(
            sa.text(
                "SELECT 1 FROM pg_indexes "
                "WHERE schemaname = 'public' "
                "  AND indexname = :idx"
            ),
            {"idx": index_name},
        )
        .scalar()
    )


def _ensure_pk(table: str, columns: str = "id", pk_name: str | None = None) -> None:
    """Add a PRIMARY KEY constraint if the table doesn't already have one.

    If a unique index with the expected _pkey name already exists (MySQL
    migration artefact), promote it to a real PK constraint using
    ALTER TABLE ... ADD CONSTRAINT ... PRIMARY KEY USING INDEX.
    """
    if _has_pk(table):
        return

    name = pk_name or f"{table}_pkey"

    if _has_unique_index(table, name):
        _conn().execute(
            sa.text(
                f'ALTER TABLE "{table}" '
                f"ADD CONSTRAINT {name} PRIMARY KEY USING INDEX {name}"
            )
        )
        logger.info("Promoted existing unique index %s to PK on %s", name, table)
    else:
        op.create_primary_key(name, table, columns.split(", "))
        logger.info("Created PK %s on %s(%s)", name, table, columns)


def _ensure_fk(
    constraint_name: str,
    source_table: str,
    source_cols: list[str],
    target_table: str,
    target_cols: list[str],
    ondelete: str | None = None,
) -> None:
    if _has_fk(constraint_name):
        return
    kw: dict = {}
    if ondelete:
        kw["ondelete"] = ondelete
    op.create_foreign_key(
        constraint_name,
        source_table,
        target_table,
        source_cols,
        target_cols,
        **kw,
    )
    logger.info(
        "Created FK %s: %s(%s) → %s(%s)",
        constraint_name,
        source_table,
        source_cols,
        target_table,
        target_cols,
    )


def _ensure_index(
    index_name: str,
    table: str,
    columns: list[str],
    unique: bool = False,
    postgresql_using: str | None = None,
) -> None:
    if _has_index(index_name):
        return
    kw: dict = {}
    if postgresql_using:
        kw["postgresql_using"] = postgresql_using
    op.create_index(index_name, table, columns, unique=unique, **kw)
    logger.info("Created index %s on %s(%s)", index_name, table, columns)


# ---------------------------------------------------------------------------
# Data fixups
# ---------------------------------------------------------------------------


def _fix_tphotovote_duplicate() -> None:
    """Remove duplicate tphotovote id=1 test row on staging if present."""
    conn = _conn()
    dupes = conn.execute(
        sa.text("SELECT COUNT(*) FROM tphotovote WHERE id = 1")
    ).scalar()
    if dupes and dupes > 1:
        result = conn.execute(
            sa.text(
                "DELETE FROM tphotovote "
                "WHERE id = 1 AND tphoto_id = 1 AND user_id = 1"
            )
        )
        logger.info(
            "Deleted %d duplicate tphotovote test row(s) with id=1",
            result.rowcount,
        )


def _fix_tphoto_orphans() -> None:
    """NULL out tlog_id on tphoto rows that reference non-existent tlogs."""
    conn = _conn()
    result = conn.execute(
        sa.text(
            "UPDATE tphoto SET tlog_id = NULL "
            "WHERE tlog_id IS NOT NULL "
            "  AND tlog_id NOT IN (SELECT id FROM tlog)"
        )
    )
    if result.rowcount:
        logger.info("NULLed tlog_id on %d orphaned tphoto row(s)", result.rowcount)


# ---------------------------------------------------------------------------
# upgrade / downgrade
# ---------------------------------------------------------------------------


def upgrade() -> None:
    # -----------------------------------------------------------------------
    # 0. Data fixups required before constraints can be added
    # -----------------------------------------------------------------------
    _fix_tphotovote_duplicate()
    _fix_tphoto_orphans()

    # -----------------------------------------------------------------------
    # 1. Primary keys (production names)
    # -----------------------------------------------------------------------
    _ensure_pk("alembic_version", columns="version_num", pk_name="alembic_version_pkc")
    _ensure_pk("area")  # area_pkey on id
    _ensure_pk("area_type")  # area_type_pkey on id
    _ensure_pk("attr")  # attr_pkey on id
    _ensure_pk("attrset")  # attrset_pkey on id
    _ensure_pk("attrset_attrval", columns="attrset_id, attrval_id")
    _ensure_pk("attrsource")  # attrsource_pkey on id
    _ensure_pk("attrval")  # attrval_pkey on id
    _ensure_pk("server")  # server_pkey on id
    _ensure_pk("status")  # status_pkey on id
    _ensure_pk("tlog")  # tlog_pkey on id
    _ensure_pk("town", columns="name")
    _ensure_pk("tphoto")  # tphoto_pkey on id
    _ensure_pk("tphotovote")  # tphotovote_pkey on id
    # user and trig already handled by previous migration (4a650a61fcbc)

    # -----------------------------------------------------------------------
    # 2. Foreign keys (matching production constraint names)
    # -----------------------------------------------------------------------
    _ensure_fk(
        "fk_tlog_user_id__user_id",
        "tlog",
        ["user_id"],
        "user",
        ["id"],
        ondelete="SET NULL",
    )
    _ensure_fk(
        "fk_tlog_trig_id__trig_id",
        "tlog",
        ["trig_id"],
        "trig",
        ["id"],
        ondelete="SET NULL",
    )

    _ensure_fk(
        "fk_tphoto_tlog_id__tlog_id",
        "tphoto",
        ["tlog_id"],
        "tlog",
        ["id"],
        ondelete="SET NULL",
    )
    _ensure_fk(
        "fk_tphoto_server_id__server_id",
        "tphoto",
        ["server_id"],
        "server",
        ["id"],
        ondelete="SET NULL",
    )

    _ensure_fk(
        "fk_tphotovote_tphoto_id__tphoto_id",
        "tphotovote",
        ["tphoto_id"],
        "tphoto",
        ["id"],
        ondelete="CASCADE",
    )
    _ensure_fk(
        "fk_tphotovote_user_id__user_id",
        "tphotovote",
        ["user_id"],
        "user",
        ["id"],
        ondelete="SET NULL",
    )

    _ensure_fk(
        "fk_trig_admin_user_id__user_id",
        "trig",
        ["admin_user_id"],
        "user",
        ["id"],
        ondelete="SET NULL",
    )
    _ensure_fk(
        "fk_trig_crt_user_id__user_id",
        "trig",
        ["crt_user_id"],
        "user",
        ["id"],
        ondelete="SET NULL",
    )
    _ensure_fk(
        "fk_trig_status_id__status_id",
        "trig",
        ["status_id"],
        "status",
        ["id"],
        ondelete="SET NULL",
    )

    _ensure_fk(
        "fk_trigstats_id__trig_id",
        "trigstats",
        ["id"],
        "trig",
        ["id"],
        ondelete="CASCADE",
    )

    _ensure_fk(
        "fk_attr_attrsource_id__attrsource_id",
        "attr",
        ["attrsource_id"],
        "attrsource",
        ["id"],
        ondelete="RESTRICT",
    )
    _ensure_fk(
        "fk_attrset_attrsource_id__attrsource_id",
        "attrset",
        ["attrsource_id"],
        "attrsource",
        ["id"],
        ondelete="RESTRICT",
    )
    _ensure_fk(
        "fk_attrset_trig_id__trig_id",
        "attrset",
        ["trig_id"],
        "trig",
        ["id"],
        ondelete="RESTRICT",
    )
    _ensure_fk(
        "fk_attrset_attrval_attrset_id__attrset_id",
        "attrset_attrval",
        ["attrset_id"],
        "attrset",
        ["id"],
        ondelete="RESTRICT",
    )
    _ensure_fk(
        "fk_attrset_attrval_attrval_id__attrval_id",
        "attrset_attrval",
        ["attrval_id"],
        "attrval",
        ["id"],
        ondelete="RESTRICT",
    )
    _ensure_fk(
        "fk_attrval_attr_id__attr_id",
        "attrval",
        ["attr_id"],
        "attr",
        ["id"],
        ondelete="RESTRICT",
    )

    _ensure_fk(
        "area_type_parent_type_id_fkey",
        "area_type",
        ["parent_type_id"],
        "area_type",
        ["id"],
    )
    _ensure_fk("area_area_type_id_fkey", "area", ["area_type_id"], "area_type", ["id"])
    _ensure_fk("area_parent_id_fkey", "area", ["parent_id"], "area", ["id"])

    # -----------------------------------------------------------------------
    # 3. Indexes (matching production names and definitions)
    # -----------------------------------------------------------------------

    # tlog — production has 7 indexes; staging has 2
    # tlog_pkey is created implicitly by _ensure_pk("tlog") above
    _ensure_index("frontpage_1", "tlog", ["trig_id", "user_id", "date", "time"])
    _ensure_index("frontpage_2", "tlog", ["date", "user_id", "time", "trig_id"])
    _ensure_index("idx_tlog_upd_timestamp", "tlog", ["upd_timestamp"])
    # ix_tlog_user_trig already exists; userid_trigid is a duplicate — skip

    # tphoto — production has 3 indexes; staging has 0
    _ensure_index("tlog_id", "tphoto", ["tlog_id"])
    _ensure_index("idx_tphoto_deleted_ind", "tphoto", ["deleted_ind"])

    # tphotovote — production has photoid index
    _ensure_index("photoid", "tphotovote", ["tphoto_id"])

    # trig — production has an extra wide index
    _ensure_index(
        "id", "trig", ["id", "name", "osgb_gridref", "osgb_eastings", "osgb_northings"]
    )

    # user — production has idx_user_crt_date
    _ensure_index("idx_user_crt_date", "user", ["crt_date"])

    # town — production has 3 indexes
    _ensure_index(
        "idx_town_location_gist", "town", ["location"], postgresql_using="gist"
    )
    _ensure_index("osgb", "town", ["osgb_eastings", "osgb_northings"])

    # postcodes — production has idx_code_prefix
    _ensure_index("idx_code_prefix", "postcodes", ["code"])

    # attrset — production has attrsrc_trig composite
    _ensure_index("attrsrc_trig", "attrset", ["attrsource_id", "trig_id"])

    # attrset_attrval — production has fk_trig_attrval_attrval1_idx
    _ensure_index("fk_trig_attrval_attrval1_idx", "attrset_attrval", ["attrval_id"])

    # attrval — production has two indexes
    _ensure_index("fk_attrval_attr1_idx", "attrval", ["attr_id"])
    _ensure_index("attr_value", "attrval", ["attr_id", "value_string"])


def downgrade() -> None:
    # Dropping constraints and indexes is not reversible in a meaningful way
    # for a sync migration.  The previous state was "broken staging" which
    # we do not want to restore.
    pass
