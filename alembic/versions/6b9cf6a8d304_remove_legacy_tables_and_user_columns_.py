"""remove legacy tables and user columns batch 2

Revision ID: 6b9cf6a8d304
Revises: bb808d64115f
Create Date: 2025-11-30 16:17:26.889345

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "6b9cf6a8d304"
down_revision: Union[str, Sequence[str], None] = "bb808d64115f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove additional legacy tables and user columns.
    
    This migration removes:
    - 6 legacy tables with no code references
    - 3 user columns for obsolete features
    
    Tables removed:
    - barrytools (76 rows) - Legacy "Barry's Tools" feature
    - coord2county (35,247 rows) - Coordinate-to-county lookup
    - trigdata (7,314 rows) - Extended trig data
    - trigdatafields (32 rows) - Meta-table for trigdata
    - tphotoclass (5,292 rows) - Photo classification
    - tquizscores (3,277 rows) - Quiz scores (user confirmed removal OK)
    
    User columns removed:
    - admin_ind - Legacy admin flag (replaced by Auth0 roles)
    - disclaimer_ind - Terms acceptance flag
    - disclaimer_timestamp - Terms acceptance timestamp
    
    Date: 2025-11-30
    """
    # Drop legacy tables (in alphabetical order for clarity)
    op.drop_table("barrytools")
    op.drop_table("coord2county")
    op.drop_table("tphotoclass")
    op.drop_table("tquizscores")
    op.drop_table("trigdata")
    op.drop_table("trigdatafields")
    
    # Drop user table columns
    op.drop_column("user", "admin_ind")
    op.drop_column("user", "disclaimer_ind")
    op.drop_column("user", "disclaimer_timestamp")


def downgrade() -> None:
    """
    Restore legacy tables and user columns.
    
    WARNING: This will recreate the table structures but NOT restore any data.
    Historical data from these tables (~48k rows) will be permanently lost.
    """
    # Recreate user columns (in reverse order)
    op.add_column("user", sa.Column("disclaimer_timestamp", sa.TIMESTAMP, nullable=True))
    op.add_column("user", sa.Column("disclaimer_ind", sa.CHAR(1), nullable=False, server_default="N"))
    op.add_column("user", sa.Column("admin_ind", sa.CHAR(1), nullable=False, server_default="N"))
    
    # Recreate legacy tables (simplified structures, no data)
    
    # trigdatafields table
    op.create_table(
        "trigdatafields",
        sa.Column("field", sa.String(20), primary_key=True),
        sa.Column("field_group", sa.String(20), nullable=False),
        sa.Column("field_enabled", sa.String(1), nullable=False),
        sa.Column("multipler", sa.DOUBLE_PRECISION, nullable=False),
        sa.Column("description", sa.String(255), nullable=False),
        sa.Column("description_low", sa.String(255), nullable=False),
        sa.Column("description_high", sa.String(255), nullable=False),
        sa.Column("includes_position", sa.String(20), nullable=False),
        sa.Column("data_source", sa.String(10), nullable=False),
        sa.Column("explanation", sa.Text, nullable=False),
    )
    
    # trigdata table
    op.create_table(
        "trigdata",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("osgb_eastings", sa.Integer, nullable=False),
        sa.Column("osgb_northings", sa.Integer, nullable=False),
        sa.Column("area_osgb_height", sa.Integer, nullable=False),
        sa.Column("aroaddist", sa.Integer, nullable=False),
        sa.Column("aroade", sa.Integer, nullable=False),
        sa.Column("aroadn", sa.Integer, nullable=False),
        sa.Column("broaddist", sa.Integer, nullable=False),
        sa.Column("broade", sa.Integer, nullable=False),
        sa.Column("broadn", sa.Integer, nullable=False),
        sa.Column("coastdist", sa.Integer, nullable=False),
        sa.Column("coaste", sa.Integer, nullable=False),
        sa.Column("coastn", sa.Integer, nullable=False),
        sa.Column("forestrydist", sa.Integer, nullable=False),
        sa.Column("forestrye", sa.Integer, nullable=False),
        sa.Column("forestryn", sa.Integer, nullable=False),
        sa.Column("landusedivers", sa.DECIMAL(3, 2), nullable=False),
        sa.Column("moorlanddist", sa.Integer, nullable=False),
        sa.Column("moorlande", sa.Integer, nullable=False),
        sa.Column("moorlandn", sa.Integer, nullable=False),
        sa.Column("railwaydist", sa.Integer, nullable=False),
        sa.Column("railwaye", sa.Integer, nullable=False),
        sa.Column("railwayn", sa.Integer, nullable=False),
        sa.Column("riverdist", sa.Integer, nullable=False),
        sa.Column("rivere", sa.Integer, nullable=False),
        sa.Column("rivern", sa.Integer, nullable=False),
        sa.Column("settdist", sa.Integer, nullable=False),
        sa.Column("sette", sa.Integer, nullable=False),
        sa.Column("settn", sa.Integer, nullable=False),
        sa.Column("slope", sa.DECIMAL(3, 1), nullable=False),
        sa.Column("stne", sa.Integer, nullable=False),
        sa.Column("stnn", sa.Integer, nullable=False),
    )
    
    # tquizscores table
    op.create_table(
        "tquizscores",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False, index=True),
        sa.Column("quiz_date", sa.Date, nullable=False),
        sa.Column("quiz_time", sa.Time, nullable=False),
        sa.Column("score", sa.SmallInteger, nullable=False),
        sa.Column("outof", sa.SmallInteger, nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
        sa.Column("crt_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    # tphotoclass table
    op.create_table(
        "tphotoclass",
        sa.Column("tphoto_id", sa.Integer, primary_key=True),
        sa.Column("class", sa.String(20), primary_key=True),
    )
    
    # coord2county table
    op.create_table(
        "coord2county",
        sa.Column("osgb_eastings", sa.Integer, primary_key=True),
        sa.Column("osgb_northings", sa.Integer, primary_key=True),
        sa.Column("county_id", sa.SmallInteger, nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    # barrytools table (simplified - has many ENUM/SET columns)
    op.create_table(
        "barrytools",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("used_by", sa.Text, nullable=False),
        sa.Column("theme", sa.String(20), nullable=False),
        sa.Column("theme_others", sa.Text, nullable=False),
        sa.Column("type", sa.String(20), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("linkable_ind", sa.String(1), nullable=False),
        sa.Column("title", sa.String(64), nullable=False),
        sa.Column("short_desc", sa.String(64), nullable=False),
        sa.Column("description", sa.Text, nullable=False),
        sa.Column("url", sa.String(255), nullable=False),
        sa.Column("author", sa.String(64), nullable=False),
        sa.Column("author_url", sa.String(255), nullable=False),
        sa.Column("p_type", sa.String(20), nullable=False),
        sa.Column("p_dist", sa.String(20), nullable=False),
        sa.Column("p_date", sa.String(20), nullable=False),
        sa.Column("p_q", sa.String(20), nullable=False),
        sa.Column("p_others", sa.Text, nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
        sa.Column("crt_timestamp", sa.TIMESTAMP, nullable=True),
    )
