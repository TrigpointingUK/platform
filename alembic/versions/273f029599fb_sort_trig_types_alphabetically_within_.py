"""sort trig_types alphabetically within groups

Revision ID: 273f029599fb
Revises: 5976531f653c
Create Date: 2026-01-11 23:32:41.624479

This migration updates the sort_order column in trig_type to be
alphabetical by name within each group, making the dropdown UI
more user-friendly.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "273f029599fb"
down_revision: Union[str, Sequence[str], None] = "5976531f653c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    """Update trig_type.sort_order to alphabetical order by name within each group."""
    conn = op.get_bind()

    # Drop the unique constraint temporarily to allow reordering
    op.drop_constraint("uq_trig_type_group_sort", "trig_type", type_="unique")

    # Update sort_order to be alphabetical by name within each group
    # Uses ROW_NUMBER() to assign sequential values based on alphabetical order
    logger.info("Updating trig_type sort_order to alphabetical order by name...")
    result = conn.execute(
        sa.text(
            """
            UPDATE trig_type
            SET sort_order = subq.new_sort_order
            FROM (
                SELECT
                    id,
                    ROW_NUMBER() OVER (
                        PARTITION BY group_id
                        ORDER BY name
                    ) * 10 AS new_sort_order
                FROM trig_type
            ) AS subq
            WHERE trig_type.id = subq.id
            """
        )
    )
    logger.info("Updated sort_order for %d trig_type rows", result.rowcount)

    # Re-add the unique constraint
    op.create_unique_constraint(
        "uq_trig_type_group_sort", "trig_type", ["group_id", "sort_order"]
    )


def downgrade() -> None:
    """Revert to original sort_order values."""
    conn = op.get_bind()

    # Drop the unique constraint temporarily
    op.drop_constraint("uq_trig_type_group_sort", "trig_type", type_="unique")

    # Original sort_order values from the initial migration, keyed by code
    # These were manually assigned in arbitrary order
    original_sort_orders = {
        # PILLAR group
        "PILLAR": 10,
        "HOTINE": 20,
        "VANESSA": 30,
        "STONE_PILLAR": 40,
        # FBM group
        "FBM": 10,
        # SURVEY_MARK group
        "BOLT": 10,
        "BLOCK": 20,
        "RIVET": 30,
        "CUT": 40,
        "DISC": 50,
        "SURFACE_BLOCK": 60,
        "BURIED_BLOCK": 70,
        "CURRY_STOOL": 80,
        "CURRY_STL": 85,
        "SPIDER": 90,
        "BRASS_PLATE": 100,
        "BERNTSEN": 110,
        "FENOMARK": 120,
        "PLATFORM_BOLT": 130,
        "CONCRETE_RING": 140,
        "CANNON": 150,
        "PIPE": 160,
        "BURIED_BLK": 165,
        "HOLE": 170,
        "HYDROG": 180,
        "MARK": 190,
        "OLD_TRIG": 200,
        "PEG": 210,
        "PLATE": 220,
        "PUNCH_MARK": 230,
        "WIRE": 240,
        # INTERSECTED group
        "INTERSECTED_STATION": 10,
        "VANE": 20,
        "SPIRE": 30,
        "TOWER": 40,
        "CHIMNEY": 50,
        "MAST": 60,
        "LIGHTHOUSE": 70,
        "MONUMENT": 80,
        "MEMORIAL": 90,
        "OBELISK": 100,
        "BEACON": 110,
        "CAIRN": 120,
        "FLAGSTAFF": 130,
        "CROSS": 140,
        "DOME": 150,
        "CUPOLA": 160,
        "BELFRY": 170,
        "AERIAL": 180,
        "APEX": 190,
        "CENTRE": 200,
        "LAMP": 210,
        "LIGHTNING_CONDUCTOR": 220,
        "PINNACLE": 230,
        "POLE": 240,
        "POST": 250,
        "PYLON": 260,
        "STONE": 270,
        "TOPOGRAPH": 280,
        "TURRET": 290,
        "VENT": 300,
        # ACTIVE group
        "ACTIVE_STATION": 10,
        # OTHER group
        "OTHER": 10,
        "UNKNOWN_USER_ADDED": 20,
    }

    logger.info("Reverting trig_type sort_order to original values...")

    # First set all to high negative values to avoid constraint violations
    conn.execute(sa.text("UPDATE trig_type SET sort_order = -id"))

    # Then update to original values
    for code, sort_order in original_sort_orders.items():
        conn.execute(
            sa.text("UPDATE trig_type SET sort_order = :sort_order WHERE code = :code"),
            {"code": code, "sort_order": sort_order},
        )

    logger.info("Reverted sort_order for %d trig_type rows", len(original_sort_orders))

    # Re-add the unique constraint
    op.create_unique_constraint(
        "uq_trig_type_group_sort", "trig_type", ["group_id", "sort_order"]
    )
