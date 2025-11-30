"""remove audit tables and gc columns

Revision ID: 726a21695c73
Revises: f59fcf553dee
Create Date: 2025-11-30 12:03:51.927925

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "726a21695c73"
down_revision: Union[str, Sequence[str], None] = "f59fcf553dee"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove legacy audit tables and Geocaching.com columns.
    
    This migration removes:
    - audit table: Legacy audit logging (1 row of data)
    - audit_simple table: Simplified audit logging (0 rows)
    - gc_* columns from user table: Legacy Geocaching.com integration
    
    These features are no longer used in the modern Auth0-based system.
    Date: 2025-11-30
    """
    # Drop legacy audit tables
    op.drop_table("audit")
    op.drop_table("audit_simple")
    
    # Drop Geocaching.com integration columns from user table
    op.drop_column("user", "gc_auth_ind")
    op.drop_column("user", "gc_premium_ind")
    op.drop_column("user", "gc_licence_ind")
    op.drop_column("user", "gc_auth_challenge")
    op.drop_column("user", "gc_auth_timestamp")
    op.drop_column("user", "gc_premium_timestamp")
    op.drop_column("user", "gc_licence_timestamp")


def downgrade() -> None:
    """
    Restore audit tables and gc_* columns.
    
    WARNING: This will recreate the table structure but NOT restore any data.
    The original audit table had 1 row of data which will be permanently lost.
    """
    # Recreate gc_* columns in user table
    op.add_column(
        "user",
        sa.Column(
            "gc_licence_ind",
            sa.CHAR(1),
            nullable=False,
            server_default=sa.text("'N'"),
        ),
    )
    op.add_column(
        "user",
        sa.Column("gc_licence_timestamp", sa.TIMESTAMP, nullable=True),
    )
    op.add_column(
        "user",
        sa.Column(
            "gc_auth_ind",
            sa.CHAR(1),
            nullable=False,
            server_default=sa.text("'N'"),
        ),
    )
    op.add_column(
        "user",
        sa.Column(
            "gc_auth_challenge",
            sa.String(34),
            nullable=False,
            server_default=sa.text("''"),
        ),
    )
    op.add_column(
        "user",
        sa.Column("gc_auth_timestamp", sa.TIMESTAMP, nullable=True),
    )
    op.add_column(
        "user",
        sa.Column(
            "gc_premium_ind",
            sa.CHAR(1),
            nullable=False,
            server_default=sa.text("'N'"),
        ),
    )
    op.add_column(
        "user",
        sa.Column("gc_premium_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    # Recreate audit_simple table
    op.create_table(
        "audit_simple",
        sa.Column("authid", sa.Integer, nullable=False),
        sa.Column("script_name", sa.String(80), nullable=False),
        sa.Column("remote_addr", sa.String(15), nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
    
    # Recreate audit table
    op.create_table(
        "audit",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("authid", sa.Integer, nullable=False),
        sa.Column("authname", sa.String(80), nullable=False),
        sa.Column("authcid", sa.Integer, nullable=False),
        sa.Column("http_host", sa.String(25), nullable=False),
        sa.Column("request_uri", sa.String(255), nullable=False),
        sa.Column("script_name", sa.String(80), nullable=False),
        sa.Column("query_string", sa.String(80), nullable=False),
        sa.Column("request_method", sa.String(5), nullable=False),
        sa.Column("script_filename", sa.String(80), nullable=False),
        sa.Column("http_user_agent", sa.String(80), nullable=False),
        sa.Column("remote_user", sa.String(80), nullable=False),
        sa.Column("remote_addr", sa.String(15), nullable=False),
        sa.Column("upd_timestamp", sa.TIMESTAMP, nullable=True),
    )
