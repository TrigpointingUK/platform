"""remove legacy tables and user columns

Revision ID: bb808d64115f
Revises: 726a21695c73
Create Date: 2025-11-30 15:15:29.188391

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "bb808d64115f"
down_revision: Union[str, Sequence[str], None] = "726a21695c73"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove legacy tables and user columns.
    
    This migration removes:
    - 11 legacy tables with no code references or empty
    - 25 user columns for obsolete features
    
    Tables removed:
    - ad2user (0 rows) - Ad campaign tracking
    - cache (0 rows) - Legacy cache table (now using Valkey)
    - nearest (72 rows) - Nearest points cache
    - osgbiw (31,518 rows) - OSGB Inland Waters data
    - percentile (0 rows) - Statistics percentiles
    - route_item (0 rows) - Route planning
    - sms (518 rows) - SMS notification data
    - tphotostats (0 rows) - Photo statistics
    - tuserstats (0 rows) - User statistics
    - twatch (5 rows) - Watch list
    
    User columns removed:
    - email_challenge - Legacy email validation
    - home1/2/3_* fields - Home location preferences (12 columns)
    - album_rows, album_cols - Photo album layout
    - sms_number, sms_credit, sms_grace - SMS feature
    - cacher_ind, cacher_id - Geocacher integration
    - trigger_ind - Trigger flag
    - nearest_max_m - Search distance
    - online_map_type, online_map_type2 - Map preferences
    - trigmap_b, trigmap_l, trigmap_c - Map display
    - showscores, showhandi - Display preferences
    
    Date: 2025-11-30
    """
    # Drop legacy tables (order doesn't matter, no FK dependencies)
    op.drop_table("ad2user")
    op.drop_table("cache")
    op.drop_table("nearest")
    op.drop_table("osgbiw")
    op.drop_table("percentile")
    op.drop_table("route_item")
    op.drop_table("sms")
    op.drop_table("tphotostats")
    op.drop_table("tuserstats")
    op.drop_table("twatch")
    
    # Drop user table columns
    op.drop_column("user", "email_challenge")
    
    # Home location fields
    op.drop_column("user", "home1_name")
    op.drop_column("user", "home1_eastings")
    op.drop_column("user", "home1_northings")
    op.drop_column("user", "home1_gridref")
    op.drop_column("user", "home2_name")
    op.drop_column("user", "home2_eastings")
    op.drop_column("user", "home2_northings")
    op.drop_column("user", "home2_gridref")
    op.drop_column("user", "home3_name")
    op.drop_column("user", "home3_eastings")
    op.drop_column("user", "home3_northings")
    op.drop_column("user", "home3_gridref")
    
    # Album display preferences
    op.drop_column("user", "album_rows")
    op.drop_column("user", "album_cols")
    
    # SMS notification fields
    op.drop_column("user", "sms_number")
    op.drop_column("user", "sms_credit")
    op.drop_column("user", "sms_grace")
    
    # Feature flags and IDs
    op.drop_column("user", "cacher_ind")
    op.drop_column("user", "cacher_id")
    op.drop_column("user", "trigger_ind")
    
    # Search and map preferences
    op.drop_column("user", "nearest_max_m")
    op.drop_column("user", "online_map_type")
    op.drop_column("user", "online_map_type2")
    op.drop_column("user", "trigmap_b")
    op.drop_column("user", "trigmap_l")
    op.drop_column("user", "trigmap_c")
    op.drop_column("user", "showscores")
    op.drop_column("user", "showhandi")


def downgrade() -> None:
    """
    Restore legacy tables and user columns.
    
    WARNING: This will recreate the table structures but NOT restore any data.
    Historical data from these tables will be permanently lost.
    """
    # Recreate user columns (in reverse order)
    op.add_column("user", sa.Column("showhandi", sa.CHAR(1), nullable=False, server_default="Y"))
    op.add_column("user", sa.Column("showscores", sa.CHAR(1), nullable=False, server_default="Y"))
    op.add_column("user", sa.Column("trigmap_c", sa.TINYINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("trigmap_l", sa.TINYINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("trigmap_b", sa.TINYINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("online_map_type2", sa.String(10), nullable=False, server_default="lla"))
    op.add_column("user", sa.Column("online_map_type", sa.String(10), nullable=False, server_default=""))
    op.add_column("user", sa.Column("nearest_max_m", sa.MEDIUMINT, nullable=False, server_default="10"))
    
    op.add_column("user", sa.Column("trigger_ind", sa.CHAR(1), nullable=False, server_default="N"))
    op.add_column("user", sa.Column("cacher_id", sa.MEDIUMINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("cacher_ind", sa.CHAR(1), nullable=False, server_default="N"))
    
    op.add_column("user", sa.Column("sms_grace", sa.TINYINT, nullable=False, server_default="5"))
    op.add_column("user", sa.Column("sms_credit", sa.MEDIUMINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("sms_number", sa.String(12), nullable=True))
    
    op.add_column("user", sa.Column("album_cols", sa.TINYINT, nullable=False, server_default="4"))
    op.add_column("user", sa.Column("album_rows", sa.TINYINT, nullable=False, server_default="2"))
    
    op.add_column("user", sa.Column("home3_gridref", sa.String(14), nullable=False, server_default=""))
    op.add_column("user", sa.Column("home3_northings", sa.MEDIUMINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("home3_eastings", sa.MEDIUMINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("home3_name", sa.String(20), nullable=False, server_default=""))
    op.add_column("user", sa.Column("home2_gridref", sa.String(14), nullable=False, server_default=""))
    op.add_column("user", sa.Column("home2_northings", sa.MEDIUMINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("home2_eastings", sa.MEDIUMINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("home2_name", sa.String(20), nullable=False, server_default=""))
    op.add_column("user", sa.Column("home1_gridref", sa.String(14), nullable=False, server_default=""))
    op.add_column("user", sa.Column("home1_northings", sa.MEDIUMINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("home1_eastings", sa.MEDIUMINT, nullable=False, server_default="0"))
    op.add_column("user", sa.Column("home1_name", sa.String(20), nullable=False, server_default=""))
    
    op.add_column("user", sa.Column("email_challenge", sa.String(34), nullable=False, server_default=""))
    
    # Recreate legacy tables (simplified structures, no data)
    op.create_table(
        "twatch",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("trig_id", sa.Integer, nullable=False),
        sa.Column("comment", sa.Text, nullable=True),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    op.create_table(
        "tuserstats",
        sa.Column("user_id", sa.Integer, primary_key=True),
        sa.Column("data", sa.Text, nullable=True),
    )
    
    op.create_table(
        "tphotostats",
        sa.Column("tphoto_id", sa.Integer, primary_key=True),
        sa.Column("views", sa.Integer, nullable=False, server_default="0"),
        sa.Column("votes", sa.Integer, nullable=False, server_default="0"),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    op.create_table(
        "sms",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("user_id", sa.Integer, nullable=False),
        sa.Column("number", sa.String(12), nullable=False),
        sa.Column("message", sa.Text, nullable=False),
        sa.Column("status", sa.CHAR(1), nullable=False),
        sa.Column("sent_timestamp", sa.TIMESTAMP, nullable=True),
        sa.Column("delivered_timestamp", sa.TIMESTAMP, nullable=True),
        sa.Column("cost", sa.Integer, nullable=False, server_default="0"),
        sa.Column("provider", sa.String(20), nullable=True),
        sa.Column("provider_id", sa.String(50), nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("retries", sa.TINYINT, nullable=False, server_default="0"),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    op.create_table(
        "route_item",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("route_id", sa.Integer, nullable=False),
        sa.Column("trig_id", sa.Integer, nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
    )
    
    op.create_table(
        "percentile",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("percentile", sa.DECIMAL(5, 2), nullable=False),
        sa.Column("value", sa.Integer, nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    op.create_table(
        "osgbiw",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("trig_name", sa.String(255), nullable=True),
        sa.Column("original_name", sa.String(255), nullable=True),
        sa.Column("new_name", sa.String(255), nullable=True),
        sa.Column("easting", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("northing", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("height", sa.DECIMAL(9, 3), nullable=True),
        sa.Column("order", sa.Integer, nullable=True),
        sa.Column("type_of_mark", sa.String(255), nullable=True),
        sa.Column("computing_date", sa.String(10), nullable=True),
        sa.Column("class_of_levelling", sa.Integer, nullable=True),
        sa.Column("date_of_levelling", sa.String(255), nullable=True),
        sa.Column("levelling_datum", sa.String(255), nullable=True),
        sa.Column("destroyed_mark_indicator", sa.Integer, nullable=True),
        sa.Column("comments", sa.String(255), nullable=True),
    )
    
    op.create_table(
        "nearest",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("trig_id", sa.Integer, nullable=False),
        sa.Column("nearest_trig_id", sa.Integer, nullable=False),
        sa.Column("distance_m", sa.Integer, nullable=False),
        sa.Column("bearing", sa.Integer, nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
        sa.Column("crt_timestamp", sa.TIMESTAMP, nullable=True),
        sa.Column("type", sa.CHAR(1), nullable=True),
    )
    
    op.create_table(
        "cache",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("key", sa.String(255), nullable=False),
        sa.Column("value", sa.Text, nullable=True),
        sa.Column("expiry", sa.TIMESTAMP, nullable=True),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
        # Additional columns exist but not critical for structure
    )
    
    op.create_table(
        "ad2user",
        sa.Column("ad_code", sa.CHAR(6), primary_key=True),
        sa.Column("user_id", sa.MEDIUMINT, primary_key=True),
        sa.Column("eligible_ind", sa.CHAR(1), nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
