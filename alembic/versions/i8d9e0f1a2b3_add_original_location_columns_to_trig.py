"""add original location columns to trig

Revision ID: i8d9e0f1a2b3
Revises: h7c8d9e0f1a2
Create Date: 2026-01-29

Add nullable columns to store the original OS-published location for trigpoints.
The base columns (wgs_*, osgb_*) remain as the current/actual location.

New columns:
- original_wgs_lat: Official OS WGS84 latitude
- original_wgs_long: Official OS WGS84 longitude
- original_osgb_eastings: Official OS grid eastings
- original_osgb_northings: Official OS grid northings
- original_osgb_gridref: Official OS grid reference
- original_grid_system: Grid system ('gb' or 'ie')
- original_location: PostGIS GEOGRAPHY point for spatial queries
- original_provenance: Text field for data cleansing notes

Migration populates all trigs with current coordinates as original,
setting provenance to 'legacy'.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from geoalchemy2 import Geography

from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = "i8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = "h7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add original location columns to trig table and populate for all trigs."""
    conn = op.get_bind()

    # Add new columns
    logger.info("Adding original_wgs_lat column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_wgs_lat",
            sa.DECIMAL(11, 8),
            nullable=True,
            comment="Official OS WGS84 latitude",
        ),
    )

    logger.info("Adding original_wgs_long column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_wgs_long",
            sa.DECIMAL(12, 8),
            nullable=True,
            comment="Official OS WGS84 longitude",
        ),
    )

    logger.info("Adding original_osgb_eastings column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_osgb_eastings",
            sa.DECIMAL(10, 4),
            nullable=True,
            comment="Official OS grid eastings",
        ),
    )

    logger.info("Adding original_osgb_northings column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_osgb_northings",
            sa.DECIMAL(11, 4),
            nullable=True,
            comment="Official OS grid northings",
        ),
    )

    logger.info("Adding original_osgb_gridref column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_osgb_gridref",
            sa.String(14),
            nullable=True,
            comment="Official OS grid reference",
        ),
    )

    logger.info("Adding original_grid_system column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_grid_system",
            sa.CHAR(2),
            nullable=True,
            comment="Grid system: 'gb' or 'ie'",
        ),
    )

    logger.info("Adding original_location PostGIS column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_location",
            Geography(geometry_type="POINT", srid=4326),
            nullable=True,
            comment="PostGIS point for original location spatial queries",
        ),
    )

    logger.info("Adding original_provenance column to trig...")
    op.add_column(
        "trig",
        sa.Column(
            "original_provenance",
            sa.Text(),
            nullable=True,
            comment="Notes for data cleansing tracking",
        ),
    )

    # Create spatial index on original_location
    logger.info("Creating spatial index on original_location...")
    op.create_index(
        "ix_trig_original_location",
        "trig",
        ["original_location"],
        postgresql_using="gist",
    )

    # Populate original columns for ALL trigs from current base columns
    # Grid system is detected from gridref format: single letter = Irish, two letters = OSGB
    logger.info("Populating original columns for all trigs...")
    result = conn.execute(sa.text("""
            UPDATE trig
            SET original_wgs_lat = wgs_lat,
                original_wgs_long = wgs_long,
                original_osgb_eastings = osgb_eastings,
                original_osgb_northings = osgb_northings,
                original_osgb_gridref = osgb_gridref,
                original_grid_system = CASE
                    WHEN LENGTH(SPLIT_PART(osgb_gridref, ' ', 1)) = 1 THEN 'ie'
                    ELSE 'gb'
                END,
                original_location = ST_SetSRID(ST_MakePoint(wgs_long, wgs_lat), 4326)::geography,
                original_provenance = 'legacy'
            """))
    logger.info("Populated original columns for %d trigs", result.rowcount)

    logger.info("Migration complete: original location columns added to trig")


def downgrade() -> None:
    """Remove original location columns from trig table."""
    logger.info("Dropping spatial index ix_trig_original_location...")
    op.drop_index("ix_trig_original_location", table_name="trig")

    logger.info("Removing original_provenance column from trig...")
    op.drop_column("trig", "original_provenance")

    logger.info("Removing original_location column from trig...")
    op.drop_column("trig", "original_location")

    logger.info("Removing original_grid_system column from trig...")
    op.drop_column("trig", "original_grid_system")

    logger.info("Removing original_osgb_gridref column from trig...")
    op.drop_column("trig", "original_osgb_gridref")

    logger.info("Removing original_osgb_northings column from trig...")
    op.drop_column("trig", "original_osgb_northings")

    logger.info("Removing original_osgb_eastings column from trig...")
    op.drop_column("trig", "original_osgb_eastings")

    logger.info("Removing original_wgs_long column from trig...")
    op.drop_column("trig", "original_wgs_long")

    logger.info("Removing original_wgs_lat column from trig...")
    op.drop_column("trig", "original_wgs_lat")

    logger.info("Downgrade complete: original location columns removed from trig")
