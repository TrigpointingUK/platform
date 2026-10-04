"""add trig variants

Revision ID: b7cfe27fcd3e
Revises: 730cbacea27f
Create Date: 2026-10-04 13:10:00.000000

A variant qualifies a trig's type without being a type of its own. The first
use: Concrete Ring, Bronze Ring and Detector Plate were separate trig types,
but per OS terminology they are all Buried Blocks, differing only by the
material of the detector buried with them (Bolts can have one too).

- trig_variant: generic lookup of variant values, grouped by group_code. Seeded
  with group DETECTOR ("Detector material"): Concrete ring, Bronze ring,
  Detector plate, Scrap metal. Future differentiations are new rows.
- trig_type.variant_group: the group a type's trigs may choose from. Set to
  DETECTOR for BURIED_BLOCK and BOLT; others can be set in the types admin.
- trig.variant_id: nullable FK; NULL = not recorded

Each old type's trigs get the matching variant and a new type, chosen from the
OS "TYPE OF MARK" attribute (attr/attrval, the same source as
scripts/update_intersected_type_from_attrval.py):

- OS mark exactly BOLT -> BOLT (e.g. a bolt set in a concrete ring)
- anything else -> BURIED_BLOCK

Trigs whose OS mark is not plainly BURIED BLK or BOLT (e.g. BLOCK, conflicting
or missing records) still become Buried Blocks, but are logged by waypoint for
manual review in the admin UI. Then the old type is deleted.

In production (Oct 2026) this is 138 Concrete Ring, 11 Detector Plate and 8
Bronze Ring trigs; 8 go to Bolt and 10 are flagged for review. Staging has none
of these types, so there the data move is a no-op. Bronze Ring and Detector
Plate were added through the types admin, so each old type is matched by code
or name and skipped (logged) if absent; more than one match aborts the
migration rather than guessing.

trig.upd_timestamp is preserved (trigger disabled around the UPDATE, as in
730cbacea27f) - reclassifying types isn't an edit to the trigs themselves.

The downgrade recreates the old types (code/name from the variant;
description, wiki_url and sort_order are not restored - the upgrade logs the
original rows) and moves Buried Blocks and Bolts with that variant back to
them.

Row counts are logged for the `make migrate-*` audit trail.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7cfe27fcd3e"
down_revision: Union[str, Sequence[str], None] = "730cbacea27f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

_TRIGGER = "set_upd_timestamp_utc"
_TARGET_TYPE = "BURIED_BLOCK"
_BOLT_TYPE = "BOLT"
_GROUP_CODE = "DETECTOR"
_GROUP_NAME = "Detector material"
_GROUP_TYPES = ("BURIED_BLOCK", "BOLT")

# (variant code, name, sort_order, SQL matching the old trig_type `tt`, or None)
_VARIANTS = [
    ("CONCRETE_RING", "Concrete ring", 10, "tt.code = 'CONCRETE_RING'"),
    (
        "BRONZE_RING",
        "Bronze ring",
        20,
        "tt.code = 'BRONZE_RING' OR tt.name ILIKE 'bronze%ring%'",
    ),
    (
        "DETECTOR_PLATE",
        "Detector plate",
        30,
        "tt.code = 'DETECTOR_PLATE' OR tt.name ILIKE 'detector%plate%'",
    ),
    ("SCRAP_METAL", "Scrap metal", 40, None),
]

# Downgrade: names and legacy_physical_type for the recreated types
_OLD_TYPES = {
    "CONCRETE_RING": ("Concrete Ring", "Concrete Ring"),
    "BRONZE_RING": ("Bronze Ring", None),
    "DETECTOR_PLATE": ("Detector Plate", None),
}


# Each trig's distinct OS "TYPE OF MARK" values, normalised, as a sorted array
_OS_MARKS = """
    SELECT s.trig_id,
           array_agg(DISTINCT upper(trim(av.value_string))
                     ORDER BY upper(trim(av.value_string))) AS marks
    FROM attrset s
    JOIN attrset_attrval aa ON aa.attrset_id = s.id
    JOIN attrval av ON av.id = aa.attrval_id
    JOIN attr a ON a.id = av.attr_id AND a.name = 'TYPE OF MARK'
    WHERE av.value_string IS NOT NULL
    GROUP BY s.trig_id
"""


def _type_id(conn, code: str) -> int:
    type_id = conn.execute(
        sa.text("SELECT id FROM trig_type WHERE code = :code"), {"code": code}
    ).scalar()
    if type_id is None:
        raise RuntimeError(f"trig_type {code} not found")
    return int(type_id)


def _trig_trigger_enabled(conn) -> bool:
    """True if trig has the upd_timestamp trigger and it is enabled."""
    state = conn.execute(
        sa.text("""
            SELECT tgenabled
            FROM pg_trigger
            WHERE tgrelid = 'trig'::regclass AND tgname = :name
            """),
        {"name": _TRIGGER},
    ).scalar()
    return state == "O"


def upgrade() -> None:
    conn = op.get_bind()

    op.create_table(
        "trig_variant",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("group_code", sa.String(length=20), nullable=False),
        sa.Column("group_name", sa.String(length=30), nullable=False),
        sa.Column("code", sa.String(length=20), nullable=False, unique=True),
        sa.Column("name", sa.String(length=30), nullable=False),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
    )
    op.create_index("ix_trig_variant_group_code", "trig_variant", ["group_code"])
    op.add_column(
        "trig",
        sa.Column(
            "variant_id",
            sa.Integer(),
            sa.ForeignKey("trig_variant.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_trig_variant_id", "trig", ["variant_id"])
    op.add_column(
        "trig_type",
        sa.Column("variant_group", sa.String(length=20), nullable=True),
    )

    for code, name, sort_order, _ in _VARIANTS:
        result = conn.execute(
            sa.text("""
                INSERT INTO trig_variant
                    (group_code, group_name, code, name, sort_order)
                VALUES (:group_code, :group_name, :code, :name, :sort_order)
                """),
            {
                "group_code": _GROUP_CODE,
                "group_name": _GROUP_NAME,
                "code": code,
                "name": name,
                "sort_order": sort_order,
            },
        )
        logger.info("Inserted trig_variant %s: %d row(s)", code, result.rowcount)

    result = conn.execute(
        sa.text("""
            UPDATE trig_type SET variant_group = :group
            WHERE code IN :codes
            """).bindparams(sa.bindparam("codes", expanding=True)),
        {"group": _GROUP_CODE, "codes": list(_GROUP_TYPES)},
    )
    logger.info(
        "Set variant_group %s on %s: %d row(s)",
        _GROUP_CODE,
        ", ".join(_GROUP_TYPES),
        result.rowcount,
    )

    target_id = _type_id(conn, _TARGET_TYPE)
    bolt_id = _type_id(conn, _BOLT_TYPE)

    toggle_trigger = _trig_trigger_enabled(conn)
    logger.info(
        "trig trigger %s: %s",
        _TRIGGER,
        "enabled - disabling during the update" if toggle_trigger else "not enabled",
    )
    if toggle_trigger:
        op.execute(f"ALTER TABLE trig DISABLE TRIGGER {_TRIGGER}")

    for code, _, _, match_sql in _VARIANTS:
        if match_sql is None:
            continue
        old_types = conn.execute(
            sa.text(f"""
                SELECT tt.id, tt.code, tt.name, tt.description, tt.wiki_url,
                       tt.sort_order, tt.legacy_physical_type, tc.code AS category
                FROM trig_type tt
                JOIN trig_category tc ON tc.id = tt.category_id
                WHERE ({match_sql}) AND tt.id <> :target
                """),
            {"target": target_id},
        ).fetchall()
        if not old_types:
            logger.info("No trig_type found for %s - skipping", code)
            continue
        if len(old_types) > 1:
            raise RuntimeError(
                f"Ambiguous trig_type for {code}: "
                + ", ".join(f"{t.id} {t.code} {t.name!r}" for t in old_types)
            )
        old = old_types[0]
        logger.info(
            "Merging trig_type %s into %s: %r", code, _TARGET_TYPE, dict(old._mapping)
        )

        review = conn.execute(
            sa.text(f"""
                SELECT t.id, t.waypoint, t.name,
                       coalesce(array_to_string(m.marks, ' + '), '(none)') AS marks
                FROM trig t
                LEFT JOIN ({_OS_MARKS}) m ON m.trig_id = t.id
                WHERE t.type_id = :old
                  AND m.marks IS DISTINCT FROM ARRAY['BURIED BLK']
                  AND m.marks IS DISTINCT FROM ARRAY['BOLT']
                ORDER BY t.id
                """),
            {"old": old.id},
        ).fetchall()
        for row in review:
            logger.info(
                "REVIEW %s %s %r: OS mark %s - becoming %s (%s)",
                old.code,
                row.waypoint,
                row.name,
                row.marks,
                _TARGET_TYPE,
                code,
            )

        result = conn.execute(
            sa.text(f"""
                UPDATE trig
                SET type_id = :bolt,
                    variant_id = (SELECT id FROM trig_variant WHERE code = :variant)
                WHERE type_id = :old
                  AND id IN (
                      SELECT trig_id FROM ({_OS_MARKS}) m
                      WHERE m.marks = ARRAY['BOLT']
                  )
                """),
            {"bolt": bolt_id, "variant": code, "old": old.id},
        )
        logger.info(
            "Moved trigs from %s to %s (OS mark BOLT): %d row(s)",
            old.code,
            _BOLT_TYPE,
            result.rowcount,
        )

        result = conn.execute(
            sa.text("""
                UPDATE trig
                SET type_id = :target,
                    variant_id = (SELECT id FROM trig_variant WHERE code = :variant)
                WHERE type_id = :old
                """),
            {"target": target_id, "variant": code, "old": old.id},
        )
        logger.info(
            "Moved trigs from %s to %s: %d row(s)",
            old.code,
            _TARGET_TYPE,
            result.rowcount,
        )

        result = conn.execute(
            sa.text("DELETE FROM trig_type WHERE id = :id"), {"id": old.id}
        )
        logger.info("Deleted trig_type %s: %d row(s)", old.code, result.rowcount)

    if toggle_trigger:
        op.execute(f"ALTER TABLE trig ENABLE TRIGGER {_TRIGGER}")

    counts = conn.execute(sa.text("""
            SELECT v.code, count(t.id) AS trigs
            FROM trig_variant v
            LEFT JOIN trig t ON t.variant_id = v.id
            GROUP BY v.code, v.sort_order
            ORDER BY v.sort_order
            """)).fetchall()
    for row in counts:
        logger.info("Trigs with variant %s: %d", row.code, row.trigs)


def downgrade() -> None:
    conn = op.get_bind()

    target = conn.execute(
        sa.text("SELECT id, category_id FROM trig_type WHERE code = :code"),
        {"code": _TARGET_TYPE},
    ).fetchone()
    # Types the upgrade moved trigs to
    new_type_ids = [
        int(row.id)
        for row in conn.execute(
            sa.text("SELECT id FROM trig_type WHERE code IN (:target, :bolt)"),
            {"target": _TARGET_TYPE, "bolt": _BOLT_TYPE},
        )
    ]

    toggle_trigger = _trig_trigger_enabled(conn)
    if toggle_trigger:
        op.execute(f"ALTER TABLE trig DISABLE TRIGGER {_TRIGGER}")

    if target is not None:
        for code, (name, legacy) in _OLD_TYPES.items():
            trigs = conn.execute(
                sa.text("""
                    SELECT count(*) FROM trig t
                    JOIN trig_variant v ON v.id = t.variant_id
                    WHERE t.type_id IN :new_types AND v.code = :variant
                    """).bindparams(sa.bindparam("new_types", expanding=True)),
                {"new_types": new_type_ids, "variant": code},
            ).scalar()
            exists = conn.execute(
                sa.text("SELECT 1 FROM trig_type WHERE code = :code"), {"code": code}
            ).scalar()
            if not trigs and code != "CONCRETE_RING":
                logger.info("No trigs with %s - not recreating its type", code)
                continue
            if not exists:
                result = conn.execute(
                    sa.text("""
                        INSERT INTO trig_type
                            (category_id, code, name, sort_order, legacy_physical_type)
                        SELECT :category, :code, :name,
                               COALESCE(MAX(sort_order), 0) + 10, :legacy
                        FROM trig_type WHERE category_id = :category
                        """),
                    {
                        "category": target.category_id,
                        "code": code,
                        "name": name,
                        "legacy": legacy,
                    },
                )
                logger.info("Recreated trig_type %s: %d row(s)", code, result.rowcount)
            result = conn.execute(
                sa.text("""
                    UPDATE trig
                    SET type_id = (SELECT id FROM trig_type WHERE code = :code)
                    WHERE type_id IN :new_types
                      AND variant_id = (SELECT id FROM trig_variant WHERE code = :code)
                    """).bindparams(sa.bindparam("new_types", expanding=True)),
                {"code": code, "new_types": new_type_ids},
            )
            logger.info("Moved trigs back to %s: %d row(s)", code, result.rowcount)

    if toggle_trigger:
        op.execute(f"ALTER TABLE trig ENABLE TRIGGER {_TRIGGER}")

    op.drop_column("trig_type", "variant_group")
    op.drop_index("ix_trig_variant_id", table_name="trig")
    op.drop_column("trig", "variant_id")
    op.drop_index("ix_trig_variant_group_code", table_name="trig_variant")
    op.drop_table("trig_variant")
