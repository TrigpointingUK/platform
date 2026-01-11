"""add PostGIS location column to postcodes table

Revision ID: fa4e26eab380
Revises: bbbc89d7d336
Create Date: 2026-01-11

This migration:
1. Adds a PostGIS GEOGRAPHY(POINT, 4326) location column to postcodes
2. Populates it from the existing lat/long columns
3. Creates a spatial index for efficient nearest-neighbour queries
4. Drops the old B-tree index on (lat, long) as it's superseded by the spatial index
"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from geoalchemy2 import Geography

# revision identifiers, used by Alembic.
revision: str = "fa4e26eab380"
down_revision: Union[str, Sequence[str], None] = "bbbc89d7d336"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    """Add PostGIS location column to postcodes table."""
    conn = op.get_bind()

    # 1. Add the location column (nullable initially)
    # Check if column already exists (for idempotent re-runs after partial failure)
    result = conn.execute(
        sa.text(
            """
            SELECT column_name FROM information_schema.columns
            WHERE table_name = 'postcodes' AND column_name = 'location'
            """
        )
    )
    if result.fetchone() is None:
        logger.info("Adding location column to postcodes table...")
        op.add_column(
            "postcodes",
            sa.Column(
                "location",
                Geography(geometry_type="POINT", srid=4326),
                nullable=True,
            ),
        )
    else:
        logger.info("Location column already exists, skipping add_column")

    # 2. Populate location from lat/long
    # ST_SetSRID(ST_MakePoint(long, lat), 4326) creates a WGS84 point
    # Note: PostGIS POINT uses (longitude, latitude) order
    logger.info("Populating location column from lat/long (2.7M rows, may take a few minutes)...")
    result = conn.execute(
        sa.text(
            """
            UPDATE postcodes
            SET location = ST_SetSRID(ST_MakePoint(long, lat), 4326)::geography
            WHERE location IS NULL
            """
        )
    )
    logger.info("Populated location for %d postcodes", result.rowcount)

    # 3. Make location NOT NULL now that it's populated
    # Check if column is already NOT NULL (for idempotent re-runs)
    result = conn.execute(
        sa.text(
            """
            SELECT is_nullable FROM information_schema.columns
            WHERE table_name = 'postcodes' AND column_name = 'location'
            """
        )
    )
    row = result.fetchone()
    if row and row[0] == "YES":
        logger.info("Making location column NOT NULL...")
        op.alter_column(
            "postcodes",
            "location",
            existing_type=Geography(geometry_type="POINT", srid=4326),
            nullable=False,
        )
    else:
        logger.info("Location column is already NOT NULL, skipping")

    # 4. Create spatial index for efficient KNN queries
    # The index name follows PostGIS conventions
    # Use IF NOT EXISTS to handle re-runs after partial failure
    logger.info("Creating spatial index on postcodes.location...")
    conn.execute(
        sa.text(
            """
            CREATE INDEX IF NOT EXISTS idx_postcodes_location
            ON postcodes USING gist (location)
            """
        )
    )
    logger.info("Created spatial index idx_postcodes_location")

    # 5. Drop the old B-tree index on (lat, long) - no longer needed
    logger.info("Dropping old B-tree index idx_postcodes_lat_long...")
    try:
        op.drop_index("idx_postcodes_lat_long", table_name="postcodes")
        logger.info("Dropped idx_postcodes_lat_long")
    except Exception as e:
        logger.warning("Could not drop idx_postcodes_lat_long (may not exist): %s", e)


def downgrade() -> None:
    """Remove PostGIS location column from postcodes table."""
    # 1. Re-create the B-tree index on (lat, long)
    op.create_index(
        "idx_postcodes_lat_long",
        "postcodes",
        ["lat", "long"],
        unique=False,
    )

    # 2. Drop the spatial index
    op.drop_index("idx_postcodes_location", table_name="postcodes")

    # 3. Drop the location column
    op.drop_column("postcodes", "location")

