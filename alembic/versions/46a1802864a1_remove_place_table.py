"""remove place table

Revision ID: 46a1802864a1
Revises: f2555e1e4940
Create Date: 2025-12-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "46a1802864a1"
down_revision: Union[str, Sequence[str], None] = "f2555e1e4940"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove the legacy place table.
    
    This table contains 39,134 rows of legacy location data including:
    - Motorway junctions (e.g., "M1 Junction 1")
    - Various place types with address information
    
    The table has no SQLAlchemy model, no API endpoints reference it,
    and it was only used by the legacy PHP site. Location search is now
    handled by the 'town' table and 'postcodes' (NSPL) table.
    
    Date: 2025-12-02
    """
    op.drop_table("place")


def downgrade() -> None:
    """
    Restore the place table.
    
    WARNING: This will recreate the table structure but NOT restore any data.
    Historical data (~39k rows) will be permanently lost.
    """
    op.create_table(
        "place",
        sa.Column("type", sa.CHAR(6), primary_key=True, nullable=False),
        sa.Column("name", sa.CHAR(50), primary_key=True, nullable=False),
        sa.Column("addr1", sa.CHAR(50), primary_key=True, nullable=False),
        sa.Column("addr2", sa.CHAR(50), primary_key=True, nullable=False),
        sa.Column("addr3", sa.CHAR(50), primary_key=True, nullable=False),
        sa.Column("addr4", sa.CHAR(50), primary_key=True, nullable=False),
        sa.Column("addr5", sa.CHAR(50), primary_key=True, nullable=False),
        sa.Column("addr6", sa.CHAR(50), primary_key=True, nullable=False),
        sa.Column("postcode8", sa.CHAR(8), primary_key=True, nullable=False),
        sa.Column("phone", sa.CHAR(15), nullable=False),
        sa.Column("wgs_lat", sa.DECIMAL(6, 5), nullable=False),
        sa.Column("wgs_long", sa.DECIMAL(6, 5), nullable=False),
        sa.Column("osgb_eastings", sa.Integer, nullable=False),
        sa.Column("osgb_northings", sa.Integer, nullable=False),
        sa.Column("osgb_gridref", sa.CHAR(14), nullable=False),
    )
