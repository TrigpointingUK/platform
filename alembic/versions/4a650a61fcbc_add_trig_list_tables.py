"""add trig_list and trig_list_item tables

Revision ID: 4a650a61fcbc
Revises: 93d5edf1b17b
Create Date: 2026-04-09

Adds the trig_list and trig_list_item tables for the Lists feature,
and a default_list_id FK column on the user table.
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "4a650a61fcbc"
down_revision: Union[str, Sequence[str], None] = "93d5edf1b17b"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _ensure_pk(table: str, column: str = "id") -> None:
    """Add a PRIMARY KEY if the table doesn't already have one.

    Legacy tables imported from MySQL may lack PK constraints, which
    prevents PostgreSQL from accepting FK references to them.
    """
    conn = op.get_bind()
    has_pk = conn.execute(
        sa.text(
            "SELECT 1 FROM information_schema.table_constraints "
            "WHERE table_name = :tbl AND constraint_type = 'PRIMARY KEY'"
        ),
        {"tbl": table},
    ).scalar()
    if not has_pk:
        op.create_primary_key(f"pk_{table}", table, [column])


def upgrade() -> None:
    _ensure_pk("user")
    _ensure_pk("trig")

    op.create_table(
        "trig_list",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("owner_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "visibility", sa.String(10), nullable=False, server_default="private"
        ),
        sa.Column(
            "editability", sa.String(10), nullable=False, server_default="private"
        ),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["owner_id"], ["user.id"], ondelete="CASCADE"),
        sa.CheckConstraint(
            "visibility IN ('private', 'public', 'admins')",
            name="ck_trig_list_visibility",
        ),
        sa.CheckConstraint(
            "editability IN ('private', 'public', 'admins')",
            name="ck_trig_list_editability",
        ),
    )
    op.create_index("ix_trig_list_id", "trig_list", ["id"])
    op.create_index("ix_trig_list_owner_id", "trig_list", ["owner_id"])

    op.create_table(
        "trig_list_item",
        sa.Column("id", sa.Integer(), nullable=False, autoincrement=True),
        sa.Column("list_id", sa.Integer(), nullable=False),
        sa.Column("trig_id", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("updated_by", sa.Integer(), nullable=True),
        sa.Column("name", sa.String(200), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "metadata",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["list_id"], ["trig_list.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["trig_id"], ["trig.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["user.id"], ondelete="SET NULL"),
        sa.UniqueConstraint("list_id", "trig_id", name="uq_trig_list_item_list_trig"),
    )
    op.create_index("ix_trig_list_item_id", "trig_list_item", ["id"])
    op.create_index(
        "ix_trig_list_item_list_position",
        "trig_list_item",
        ["list_id", "position"],
    )
    op.create_index("ix_trig_list_item_trig_id", "trig_list_item", ["trig_id"])

    op.add_column(
        "user",
        sa.Column("default_list_id", sa.Integer(), nullable=True),
    )
    op.create_foreign_key(
        "fk_user_default_list_id",
        "user",
        "trig_list",
        ["default_list_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade() -> None:
    op.drop_constraint("fk_user_default_list_id", "user", type_="foreignkey")
    op.drop_column("user", "default_list_id")

    op.drop_index("ix_trig_list_item_trig_id", table_name="trig_list_item")
    op.drop_index("ix_trig_list_item_list_position", table_name="trig_list_item")
    op.drop_index("ix_trig_list_item_id", table_name="trig_list_item")
    op.drop_table("trig_list_item")

    op.drop_index("ix_trig_list_owner_id", table_name="trig_list")
    op.drop_index("ix_trig_list_id", table_name="trig_list")
    op.drop_table("trig_list")
