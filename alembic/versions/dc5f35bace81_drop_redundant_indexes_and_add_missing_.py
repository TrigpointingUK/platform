"""drop redundant indexes and add missing indexes

Revision ID: dc5f35bace81
Revises: 8b4df151016c
Create Date: 2026-04-10

Best-practice cleanup for both staging and production:

DROP (redundant / duplicate):
  - trig.idx_trig_original_location  (duplicate of ix_trig_original_location)
  - tlog.userid_trigid               (duplicate of ix_tlog_user_trig)
  - area.ix_area_id                  (duplicate of PK area_pkey)
  - area_type.ix_area_type_id        (duplicate of PK area_type_pkey)
  - area_type.ix_area_type_code      (duplicate of unique area_type_code_key)
  - trig_list.ix_trig_list_id        (duplicate of PK trig_list_pkey)
  - trig_list_item.ix_trig_list_item_id  (duplicate of PK trig_list_item_pkey)
  - postcodes.idx_code_prefix        (duplicate of PK postcodes_pkey)
  - trig.id  (wide legacy index; replaced by PK + new individual indexes)

CREATE (missing, declared by models but never existed):
  - user.ix_user_auth0_user_id   (critical for every auth lookup)
  - user.ix_user_name
  - user.ix_user_email
  - trig.ix_trig_waypoint
  - trig.ix_trig_name
  - trig.ix_trig_status_id
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

revision: str = "dc5f35bace81"
down_revision: Union[str, Sequence[str], None] = "8b4df151016c"
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


def _drop_index_if_exists(index_name: str, table: str) -> None:
    if _has_index(index_name):
        op.drop_index(index_name, table_name=table)
        logger.info("Dropped redundant index %s on %s", index_name, table)


def _create_index_if_missing(
    index_name: str, table: str, columns: list[str], **kw: object
) -> None:
    if not _has_index(index_name):
        op.create_index(index_name, table, columns, **kw)
        logger.info("Created index %s on %s(%s)", index_name, table, columns)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 1. Drop redundant / duplicate indexes
    # ------------------------------------------------------------------

    # Duplicate GIST on trig.original_location (both have 0 scans in prod)
    _drop_index_if_exists("idx_trig_original_location", "trig")

    # Duplicate btree on tlog(user_id, trig_id) — ix_tlog_user_trig remains
    _drop_index_if_exists("userid_trigid", "tlog")

    # PK-duplicate standalone btree indexes on id columns
    _drop_index_if_exists("ix_area_id", "area")
    _drop_index_if_exists("ix_area_type_id", "area_type")
    _drop_index_if_exists("ix_trig_list_id", "trig_list")
    _drop_index_if_exists("ix_trig_list_item_id", "trig_list_item")

    # Non-unique index duplicating unique index on area_type.code
    _drop_index_if_exists("ix_area_type_code", "area_type")

    # Duplicate of PK on postcodes.code
    _drop_index_if_exists("idx_code_prefix", "postcodes")

    # Wide legacy MySQL index on trig(id, name, osgb_gridref, eastings, northings)
    # Served as a covering index but PK + new individual indexes replace it
    _drop_index_if_exists("id", "trig")

    # ------------------------------------------------------------------
    # 2. Add missing indexes declared by SQLAlchemy models
    # ------------------------------------------------------------------

    # user — all three are critical for API query performance
    _create_index_if_missing("ix_user_auth0_user_id", "user", ["auth0_user_id"])
    _create_index_if_missing("ix_user_name", "user", ["name"])
    _create_index_if_missing("ix_user_email", "user", ["email"])

    # trig — declared with index=True but never created in legacy migration
    _create_index_if_missing("ix_trig_waypoint", "trig", ["waypoint"])
    _create_index_if_missing("ix_trig_name", "trig", ["name"])
    _create_index_if_missing("ix_trig_status_id", "trig", ["status_id"])


def downgrade() -> None:
    # Reverse: drop the new indexes, recreate the redundant ones
    _drop_index_if_exists("ix_trig_status_id", "trig")
    _drop_index_if_exists("ix_trig_name", "trig")
    _drop_index_if_exists("ix_trig_waypoint", "trig")
    _drop_index_if_exists("ix_user_email", "user")
    _drop_index_if_exists("ix_user_name", "user")
    _drop_index_if_exists("ix_user_auth0_user_id", "user")

    _create_index_if_missing(
        "id",
        "trig",
        ["id", "name", "osgb_gridref", "osgb_eastings", "osgb_northings"],
    )
    _create_index_if_missing("idx_code_prefix", "postcodes", ["code"])
    _create_index_if_missing("ix_area_type_code", "area_type", ["code"])
    _create_index_if_missing("ix_trig_list_item_id", "trig_list_item", ["id"])
    _create_index_if_missing("ix_trig_list_id", "trig_list", ["id"])
    _create_index_if_missing("ix_area_type_id", "area_type", ["id"])
    _create_index_if_missing("ix_area_id", "area", ["id"])
    _create_index_if_missing("userid_trigid", "tlog", ["user_id", "trig_id"])
    _create_index_if_missing(
        "idx_trig_original_location",
        "trig",
        ["original_location"],
        postgresql_using="gist",
    )
