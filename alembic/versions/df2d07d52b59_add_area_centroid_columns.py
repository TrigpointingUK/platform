"""add_area_centroid_columns

Revision ID: df2d07d52b59
Revises: j9e0f1a2b3c4
Create Date: 2026-02-01 18:33:42.732572

This migration adds center_lat and center_lon columns to the area table
to store the centroid of each area's boundary polygon. This enables
distance-based sorting of areas from a given location.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "df2d07d52b59"
down_revision: Union[str, Sequence[str], None] = "j9e0f1a2b3c4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add centroid columns to area table and populate from boundary polygons.
    
    Uses PostGIS ST_Centroid to calculate the centroid of each area's boundary.
    """
    # Add columns
    op.add_column(
        "area",
        sa.Column("center_lat", sa.DECIMAL(11, 8), nullable=True),
    )
    op.add_column(
        "area",
        sa.Column("center_lon", sa.DECIMAL(12, 8), nullable=True),
    )
    
    # Backfill centroids using PostGIS
    conn = op.get_bind()
    result = conn.execute(
        sa.text("""
            UPDATE area 
            SET center_lat = ST_Y(ST_Centroid(boundary::geometry)),
                center_lon = ST_X(ST_Centroid(boundary::geometry))
            WHERE boundary IS NOT NULL
        """)
    )
    logger.info(f"Updated {result.rowcount} area centroids")


def downgrade() -> None:
    """Remove centroid columns from area table."""
    op.drop_column("area", "center_lon")
    op.drop_column("area", "center_lat")
