"""add area and area_type tables

Revision ID: c8a3f2e91b47
Revises: 80130ca116d1
Create Date: 2025-12-02

This migration creates tables for storing geographic area boundaries:
- area_type: Categories of boundaries (historic counties, admin areas, map sheets, etc.)
- area: The actual boundary polygons with PostGIS GEOGRAPHY type

These enable spatial queries to find which areas contain a trigpoint,
or which trigpoints fall within a given area.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from geoalchemy2 import Geography

# revision identifiers, used by Alembic.
revision: str = "c8a3f2e91b47"
down_revision: Union[str, Sequence[str], None] = "80130ca116d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create area_type and area tables with spatial indexing."""
    
    # Get connection to check for existing tables
    conn = op.get_bind()
    
    # Check if area_type already exists
    area_type_exists = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'area_type')")
    ).scalar()
    
    if not area_type_exists:
        # Create area_type table first (referenced by area)
        op.create_table(
            "area_type",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(50), nullable=False),
            sa.Column("name", sa.String(100), nullable=False),
            sa.Column("description", sa.Text(), nullable=True),
            sa.Column("source_url", sa.String(500), nullable=True),
            sa.Column("parent_type_id", sa.Integer(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["parent_type_id"], ["area_type.id"]),
            sa.UniqueConstraint("code"),
        )
        op.create_index("ix_area_type_id", "area_type", ["id"])
        op.create_index("ix_area_type_code", "area_type", ["code"])

    # Check if area already exists
    area_exists = conn.execute(
        sa.text("SELECT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_name = 'area')")
    ).scalar()
    
    if not area_exists:
        # Create area table with PostGIS Geography column
        op.create_table(
            "area",
            sa.Column("id", sa.Integer(), nullable=False),
            sa.Column("area_type_id", sa.Integer(), nullable=False),
            sa.Column("code", sa.String(50), nullable=True),
            sa.Column("name", sa.String(255), nullable=False),
            sa.Column(
                "boundary",
                Geography(geometry_type="MULTIPOLYGON", srid=4326, spatial_index=False),
                nullable=False,
            ),
            sa.Column("parent_id", sa.Integer(), nullable=True),
            sa.Column("properties", sa.Text(), nullable=True),
            sa.PrimaryKeyConstraint("id"),
            sa.ForeignKeyConstraint(["area_type_id"], ["area_type.id"]),
            sa.ForeignKeyConstraint(["parent_id"], ["area.id"]),
        )
        op.create_index("ix_area_id", "area", ["id"])
        op.create_index("ix_area_area_type_id", "area", ["area_type_id"])
        op.create_index("ix_area_code", "area", ["code"])
        op.create_index("ix_area_name", "area", ["name"])
        op.create_index("ix_area_parent_id", "area", ["parent_id"])

        # Create spatial index on the boundary column using raw SQL
        # GiST index is essential for efficient spatial queries
        op.execute(
            sa.text(
                "CREATE INDEX ix_area_boundary_gist ON area USING GIST (boundary)"
            )
        )


def downgrade() -> None:
    """Drop area and area_type tables."""
    # Use IF EXISTS for safety in case of partial state
    op.execute(sa.text("DROP INDEX IF EXISTS ix_area_boundary_gist"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_area_parent_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_area_name"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_area_code"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_area_area_type_id"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_area_id"))
    op.execute(sa.text("DROP TABLE IF EXISTS area CASCADE"))

    op.execute(sa.text("DROP INDEX IF EXISTS ix_area_type_code"))
    op.execute(sa.text("DROP INDEX IF EXISTS ix_area_type_id"))
    op.execute(sa.text("DROP TABLE IF EXISTS area_type CASCADE"))
