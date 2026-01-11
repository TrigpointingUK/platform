"""add trig_type dimension tables

Revision ID: 5976531f653c
Revises: 92954a8373b5
Create Date: 2026-01-11

This migration creates the trig_type_group and trig_type tables for
finer-grained trigpoint classification. It also seeds initial data
and backfills trig.type_id from the existing physical_type column.

Phase 1 of the trig type schema migration:
- Creates trig_type_group table (6 groups)
- Creates trig_type table (~60 types)
- Adds trig.type_id column (nullable initially)
- Backfills type_id from physical_type (case-insensitive)
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "5976531f653c"
down_revision: Union[str, Sequence[str], None] = "92954a8373b5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# Group definitions: (code, name, description, wiki_url, sort_order)
GROUPS = [
    (
        "PILLAR",
        "Pillar",
        "Triangulation pillars",
        "https://wiki.trigpointing.uk/Pillar",
        10,
    ),
    (
        "FBM",
        "FBM",
        "Fundamental Bench Marks",
        "https://wiki.trigpointing.uk/Flush_Bracket",
        20,
    ),
    (
        "SURVEY_MARK",
        "Survey mark",
        "Minor survey marks including bolts, blocks, and rivets",
        None,
        30,
    ),
    (
        "INTERSECTED",
        "Intersected",
        "Intersected stations - church spires, towers, etc.",
        "https://wiki.trigpointing.uk/Intersected_Station",
        40,
    ),
    ("ACTIVE", "Active station", "Active GPS stations", None, 50),
    ("OTHER", "Other", "Other and unknown types", None, 60),
]

# Type definitions: (code, name, description, wiki_url, sort_order, group_code, legacy_physical_type)
# legacy_physical_type is used for case-insensitive matching during backfill
TYPES = [
    # PILLAR group
    (
        "PILLAR",
        "Pillar",
        "Standard triangulation pillar",
        "https://wiki.trigpointing.uk/Pillar",
        10,
        "PILLAR",
        "Pillar",
    ),
    (
        "HOTINE",
        "Hotine Pillar",
        "Hotine-pattern triangulation pillar",
        "https://wiki.trigpointing.uk/Hotine",
        20,
        "PILLAR",
        "",
    ),
    (
        "VANESSA",
        "Vanessa Pillar",
        "Vanessa-pattern triangulation pillar",
        "https://wiki.trigpointing.uk/Vanessa",
        30,
        "PILLAR",
        "",
    ),
    (
        "STONE_PILLAR",
        "Stone Pillar",
        "Stone triangulation pillar",
        None,
        40,
        "PILLAR",
        "",
    ),
    # FBM group
    (
        "FBM",
        "Fundamental Benchmark",
        "Fundamental Benchmark",
        "https://wiki.trigpointing.uk/Flush_Bracket",
        10,
        "FBM",
        "FBM",
    ),
    # SURVEY_MARK group
    ("BOLT", "Bolt", "Survey bolt", None, 10, "SURVEY_MARK", "Bolt"),
    ("BLOCK", "Block", "Survey block", None, 20, "SURVEY_MARK", "Block"),
    ("RIVET", "Rivet", "Survey rivet", None, 30, "SURVEY_MARK", "Rivet"),
    ("CUT", "Cut", "Cut mark", None, 40, "SURVEY_MARK", "Cut"),
    ("DISC", "Disc", "Survey disc", None, 50, "SURVEY_MARK", "Disc"),
    (
        "SURFACE_BLOCK",
        "Surface Block",
        "Surface block",
        None,
        60,
        "SURVEY_MARK",
        "Surface Block",
    ),
    (
        "BURIED_BLOCK",
        "Buried Block",
        "Buried block",
        None,
        70,
        "SURVEY_MARK",
        "Buried Block",
    ),
    (
        "CURRY_STOOL",
        "Curry Stool",
        "Curry stool mark",
        None,
        80,
        "SURVEY_MARK",
        "Curry Stool",
    ),
    (
        "CURRY_STL",
        "Curry St'l",
        "Curry stool (OS abbreviation)",
        None,
        85,
        "SURVEY_MARK",
        "CURRY ST'L",
    ),
    ("SPIDER", "Spider", "Spider mark", None, 90, "SURVEY_MARK", "Spider"),
    (
        "BRASS_PLATE",
        "Brass Plate",
        "Brass plate mark",
        None,
        100,
        "SURVEY_MARK",
        "Brass Plate",
    ),
    ("BERNTSEN", "Berntsen", "Berntsen mark", None, 110, "SURVEY_MARK", "Berntsen"),
    ("FENOMARK", "Fenomark", "Fenomark", None, 120, "SURVEY_MARK", "Fenomark"),
    (
        "PLATFORM_BOLT",
        "Platform Bolt",
        "Platform bolt",
        None,
        130,
        "SURVEY_MARK",
        "Platform Bolt",
    ),
    (
        "CONCRETE_RING",
        "Concrete Ring",
        "Concrete ring",
        None,
        140,
        "SURVEY_MARK",
        "Concrete Ring",
    ),
    ("CANNON", "Cannon", "Cannon mark", None, 150, "SURVEY_MARK", "Cannon"),
    ("PIPE", "Pipe", "Pipe mark", None, 160, "SURVEY_MARK", "Pipe"),
    (
        "BURIED_BLK",
        "Buried Blk",
        "Buried block (OS abbreviation)",
        None,
        165,
        "SURVEY_MARK",
        "BURIED BLK",
    ),
    ("HOLE", "Hole", "Hole mark", None, 170, "SURVEY_MARK", "HOLE"),
    ("HYDROG", "Hydrog", "Hydrographic mark", None, 180, "SURVEY_MARK", "HYDROG"),
    ("MARK", "Mark", "General mark", None, 190, "SURVEY_MARK", "MARK"),
    ("OLD_TRIG", "Old Trig", "Old trig point", None, 200, "SURVEY_MARK", "OLD TRIG"),
    ("PEG", "Peg", "Peg mark", None, 210, "SURVEY_MARK", "PEG"),
    ("PLATE", "Plate", "Plate mark", None, 220, "SURVEY_MARK", "PLATE"),
    ("PUNCH_MARK", "Punch Mark", "Punch mark", None, 230, "SURVEY_MARK", "PUNCH MARK"),
    ("WIRE", "Wire", "Wire mark", None, 240, "SURVEY_MARK", "WIRE"),
    # INTERSECTED group
    (
        "INTERSECTED_STATION",
        "Intersected Station",
        "General intersected station",
        "https://wiki.trigpointing.uk/Intersected_Station",
        10,
        "INTERSECTED",
        "Intersected Station",
    ),
    ("VANE", "Vane", "Weather vane", None, 20, "INTERSECTED", "Vane"),
    ("SPIRE", "Spire", "Church spire", None, 30, "INTERSECTED", "SPIRE"),
    ("TOWER", "Tower", "Tower", None, 40, "INTERSECTED", "TOWER"),
    ("CHIMNEY", "Chimney", "Chimney", None, 50, "INTERSECTED", "CHIMNEY"),
    ("MAST", "Mast", "Mast", None, 60, "INTERSECTED", "MAST"),
    ("LIGHTHOUSE", "Lighthouse", "Lighthouse", None, 70, "INTERSECTED", "LIGHTHOUSE"),
    ("MONUMENT", "Monument", "Monument", None, 80, "INTERSECTED", "MONUMENT"),
    ("MEMORIAL", "Memorial", "Memorial", None, 90, "INTERSECTED", "MEMORIAL"),
    ("OBELISK", "Obelisk", "Obelisk", None, 100, "INTERSECTED", "OBELISK"),
    ("BEACON", "Beacon", "Beacon", None, 110, "INTERSECTED", "BEACON"),
    ("CAIRN", "Cairn", "Cairn", None, 120, "INTERSECTED", "CAIRN"),
    ("FLAGSTAFF", "Flagstaff", "Flagstaff", None, 130, "INTERSECTED", "FLAGSTAFF"),
    ("CROSS", "Cross", "Cross", None, 140, "INTERSECTED", "CROSS"),
    ("DOME", "Dome", "Dome", None, 150, "INTERSECTED", "DOME"),
    ("CUPOLA", "Cupola", "Cupola", None, 160, "INTERSECTED", "CUPOLA"),
    ("BELFRY", "Belfry", "Belfry", None, 170, "INTERSECTED", "BELFRY"),
    ("AERIAL", "Aerial", "Aerial", None, 180, "INTERSECTED", "AERIAL"),
    ("APEX", "Apex", "Apex", None, 190, "INTERSECTED", "APEX"),
    ("CENTRE", "Centre", "Centre point", None, 200, "INTERSECTED", "CENTRE"),
    ("LAMP", "Lamp", "Lamp", None, 210, "INTERSECTED", "LAMP"),
    (
        "LIGHTNING_CONDUCTOR",
        "Lightning Conductor",
        "Lightning conductor",
        None,
        220,
        "INTERSECTED",
        "L'NING C",
    ),
    ("PINNACLE", "Pinnacle", "Pinnacle", None, 230, "INTERSECTED", "PINNACLE"),
    ("POLE", "Pole", "Pole", None, 240, "INTERSECTED", "POLE"),
    ("POST", "Post", "Post", None, 250, "INTERSECTED", "POST"),
    ("PYLON", "Pylon", "Pylon", None, 260, "INTERSECTED", "PYLON"),
    ("STONE", "Stone", "Stone", None, 270, "INTERSECTED", "STONE"),
    ("TOPOGRAPH", "Topograph", "Topograph", None, 280, "INTERSECTED", "TOPOGRAPH"),
    ("TURRET", "Turret", "Turret", None, 290, "INTERSECTED", "TURRET"),
    ("VENT", "Vent", "Vent", None, 300, "INTERSECTED", "VENT"),
    # ACTIVE group
    (
        "ACTIVE_STATION",
        "Active Station",
        "Active GPS station",
        None,
        10,
        "ACTIVE",
        "Active station",
    ),
    # OTHER group
    ("OTHER", "Other", "Other type", None, 10, "OTHER", "Other"),
    (
        "UNKNOWN_USER_ADDED",
        "Unknown - user added",
        "Unknown type (user added)",
        None,
        20,
        "OTHER",
        "Unknown - user added",
    ),
]


def upgrade() -> None:
    """Create trig_type_group and trig_type tables, seed data, add trig.type_id."""
    conn = op.get_bind()

    # 1. Create trig_type_group table
    logger.info("Creating trig_type_group table...")
    op.create_table(
        "trig_type_group",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("description", sa.String(100), nullable=True),
        sa.Column("wiki_url", sa.String(255), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False, unique=True),
    )

    # 2. Create trig_type table
    logger.info("Creating trig_type table...")
    op.create_table(
        "trig_type",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "group_id",
            sa.Integer(),
            sa.ForeignKey("trig_type_group.id"),
            nullable=False,
        ),
        sa.Column("code", sa.String(20), nullable=False, unique=True),
        sa.Column("name", sa.String(30), nullable=False),
        sa.Column("description", sa.String(100), nullable=True),
        sa.Column("wiki_url", sa.String(255), nullable=True),
        sa.Column("sort_order", sa.SmallInteger(), nullable=False),
        sa.Column("legacy_physical_type", sa.String(25), nullable=True),
        sa.UniqueConstraint("group_id", "sort_order", name="uq_trig_type_group_sort"),
    )

    # 3. Seed trig_type_group data
    logger.info("Seeding trig_type_group data (%d groups)...", len(GROUPS))
    for code, name, description, wiki_url, sort_order in GROUPS:
        conn.execute(
            sa.text(
                """
                INSERT INTO trig_type_group (code, name, description, wiki_url, sort_order)
                VALUES (:code, :name, :description, :wiki_url, :sort_order)
                """
            ),
            {
                "code": code,
                "name": name,
                "description": description,
                "wiki_url": wiki_url,
                "sort_order": sort_order,
            },
        )
    logger.info("Seeded %d groups", len(GROUPS))

    # 4. Seed trig_type data
    logger.info("Seeding trig_type data (%d types)...", len(TYPES))
    for (
        code,
        name,
        description,
        wiki_url,
        sort_order,
        group_code,
        legacy_physical_type,
    ) in TYPES:
        conn.execute(
            sa.text(
                """
                INSERT INTO trig_type (group_id, code, name, description, wiki_url, sort_order, legacy_physical_type)
                SELECT g.id, :code, :name, :description, :wiki_url, :sort_order, :legacy_physical_type
                FROM trig_type_group g
                WHERE g.code = :group_code
                """
            ),
            {
                "code": code,
                "name": name,
                "description": description,
                "wiki_url": wiki_url,
                "sort_order": sort_order,
                "group_code": group_code,
                "legacy_physical_type": legacy_physical_type,
            },
        )
    logger.info("Seeded %d types", len(TYPES))

    # 5. Add type_id column to trig table (nullable initially)
    logger.info("Adding type_id column to trig table...")
    op.add_column(
        "trig",
        sa.Column(
            "type_id", sa.Integer(), sa.ForeignKey("trig_type.id"), nullable=True
        ),
    )

    # 6. Backfill type_id from physical_type (case-insensitive match)
    logger.info("Backfilling trig.type_id from physical_type (case-insensitive)...")
    result = conn.execute(
        sa.text(
            """
            UPDATE trig t
            SET type_id = tt.id
            FROM trig_type tt
            WHERE LOWER(t.physical_type) = LOWER(tt.legacy_physical_type)
            AND t.type_id IS NULL
            """
        )
    )
    logger.info("Backfilled type_id for %d trigs", result.rowcount)

    # 7. Check for any unmatched physical_types
    result = conn.execute(
        sa.text(
            """
            SELECT DISTINCT physical_type, COUNT(*) as cnt
            FROM trig
            WHERE type_id IS NULL
            GROUP BY physical_type
            ORDER BY cnt DESC
            """
        )
    )
    unmatched = result.fetchall()
    if unmatched:
        logger.warning("Found %d distinct unmatched physical_types:", len(unmatched))
        for row in unmatched:
            logger.warning("  '%s': %d trigs", row[0], row[1])
    else:
        logger.info("All physical_types matched successfully")

    # 8. Create index on type_id for query performance
    logger.info("Creating index on trig.type_id...")
    op.create_index("ix_trig_type_id", "trig", ["type_id"])


def downgrade() -> None:
    """Remove trig_type tables and trig.type_id column."""
    # Drop index
    op.drop_index("ix_trig_type_id", table_name="trig")

    # Drop type_id column from trig
    op.drop_column("trig", "type_id")

    # Drop trig_type table (must be before trig_type_group due to FK)
    op.drop_table("trig_type")

    # Drop trig_type_group table
    op.drop_table("trig_type_group")
