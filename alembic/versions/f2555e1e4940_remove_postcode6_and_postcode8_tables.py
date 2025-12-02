"""remove postcode6 and postcode8 tables

Revision ID: f2555e1e4940
Revises: 47c7642e1aee
Create Date: 2025-12-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f2555e1e4940"
down_revision: Union[str, Sequence[str], None] = "47c7642e1aee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove legacy postcode tables.
    
    This migration removes:
    - postcode6 (8,481 rows) - Legacy 6-character postcode sectors with corrupted WGS84 coords
    - postcode8 (54,552 rows) - Legacy 8-character postcodes from Multimap/Streetmap
    
    These tables have been superseded by the 'postcodes' table containing 2.7M
    postcodes from the official NSPL (National Statistics Postcode Lookup) dataset.
    
    The trig.postcode column now references the new postcodes table directly.
    
    Date: 2025-12-02
    """
    op.drop_table("postcode6")
    op.drop_table("postcode8")


def downgrade() -> None:
    """
    Restore legacy postcode tables.
    
    WARNING: This will recreate the table structures but NOT restore any data.
    Historical data from these tables (~63k rows) will be permanently lost.
    """
    # Recreate postcode8 table
    op.create_table(
        "postcode8",
        sa.Column("code", sa.CHAR(8), primary_key=True, nullable=False),
        sa.Column("osgb_eastings", sa.Integer, nullable=False),
        sa.Column("osgb_northings", sa.Integer, nullable=False),
        sa.Column("source", sa.CHAR(20), nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    # Recreate postcode6 table
    op.create_table(
        "postcode6",
        sa.Column("code", sa.CHAR(6), primary_key=True, nullable=False),
        sa.Column("code4", sa.CHAR(4), nullable=False),
        sa.Column("wgs_lat", sa.DECIMAL(6, 5), nullable=False),
        sa.Column("wgs_long", sa.DECIMAL(6, 5), nullable=False),
        sa.Column("osgb_eastings", sa.Integer, nullable=False),
        sa.Column("osgb_northings", sa.Integer, nullable=False),
        sa.Column("osgb_gridref", sa.CHAR(14), nullable=False),
        sa.Column("county", sa.CHAR(20), nullable=False),
        sa.Column("town", sa.CHAR(50), nullable=False),
        sa.Column("postal_town", sa.CHAR(50), nullable=False),
    )
