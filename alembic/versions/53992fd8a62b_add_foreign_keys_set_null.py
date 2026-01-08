"""add_foreign_keys_set_null

Revision ID: 53992fd8a62b
Revises: f3e16ee9c5f1
Create Date: 2026-01-08 22:24:41.111705

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "53992fd8a62b"
down_revision: Union[str, Sequence[str], None] = "f3e16ee9c5f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _constraint_exists(conn, name: str) -> bool:
    return (
        conn.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname = :name"),
            {"name": name},
        ).scalar()
        is not None
    )


def _add_fk_not_valid(
    *,
    conn,
    table: str,
    constraint: str,
    columns: list[str],
    ref_table: str,
    ref_columns: list[str],
    on_delete: str,
) -> None:
    """
    Add a PostgreSQL FK constraint as NOT VALID.

    NOT VALID avoids scanning existing rows at migration time (reduces lock/impact),
    but still enforces the FK for new rows and updates.
    """
    if _constraint_exists(conn, constraint):
        return

    cols_sql = ", ".join(sa.sql.elements.quoted_name(c, True) for c in columns)
    ref_cols_sql = ", ".join(sa.sql.elements.quoted_name(c, True) for c in ref_columns)

    # Quote table names defensively (e.g. "user" is a keyword).
    table_sql = sa.sql.elements.quoted_name(table, True)
    ref_table_sql = sa.sql.elements.quoted_name(ref_table, True)
    constraint_sql = sa.sql.elements.quoted_name(constraint, True)

    op.execute(
        sa.text(
            f"""
            ALTER TABLE {table_sql}
            ADD CONSTRAINT {constraint_sql}
            FOREIGN KEY ({cols_sql})
            REFERENCES {ref_table_sql} ({ref_cols_sql})
            ON DELETE {on_delete}
            NOT VALID
            """
        )
    )


def upgrade() -> None:
    """Upgrade schema."""
    conn = op.get_bind()

    # ---------------------------------------------------------------------
    # Nullability changes required for ON DELETE SET NULL constraints
    # ---------------------------------------------------------------------
    op.alter_column(
        "tphoto",
        "tlog_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "tphoto",
        "server_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "tphotovote",
        "tphoto_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "tphotovote",
        "user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "trig",
        "status_id",
        existing_type=sa.Integer(),
        nullable=True,
    )
    op.alter_column(
        "trig",
        "crt_user_id",
        existing_type=sa.Integer(),
        nullable=True,
    )

    # ---------------------------------------------------------------------
    # Foreign keys (NOT VALID; validate later once any legacy orphans are cleaned)
    # ---------------------------------------------------------------------
    # Set NULL behaviour (no cascades)
    _add_fk_not_valid(
        conn=conn,
        table="tlog",
        constraint="fk_tlog_trig_id__trig_id",
        columns=["trig_id"],
        ref_table="trig",
        ref_columns=["id"],
        on_delete="SET NULL",
    )
    _add_fk_not_valid(
        conn=conn,
        table="tlog",
        constraint="fk_tlog_user_id__user_id",
        columns=["user_id"],
        ref_table="user",
        ref_columns=["id"],
        on_delete="SET NULL",
    )
    _add_fk_not_valid(
        conn=conn,
        table="tphoto",
        constraint="fk_tphoto_tlog_id__tlog_id",
        columns=["tlog_id"],
        ref_table="tlog",
        ref_columns=["id"],
        on_delete="SET NULL",
    )
    _add_fk_not_valid(
        conn=conn,
        table="tphoto",
        constraint="fk_tphoto_server_id__server_id",
        columns=["server_id"],
        ref_table="server",
        ref_columns=["id"],
        on_delete="SET NULL",
    )
    _add_fk_not_valid(
        conn=conn,
        table="tphotovote",
        constraint="fk_tphotovote_tphoto_id__tphoto_id",
        columns=["tphoto_id"],
        ref_table="tphoto",
        ref_columns=["id"],
        on_delete="SET NULL",
    )
    _add_fk_not_valid(
        conn=conn,
        table="tphotovote",
        constraint="fk_tphotovote_user_id__user_id",
        columns=["user_id"],
        ref_table="user",
        ref_columns=["id"],
        on_delete="SET NULL",
    )
    _add_fk_not_valid(
        conn=conn,
        table="trig",
        constraint="fk_trig_status_id__status_id",
        columns=["status_id"],
        ref_table="status",
        ref_columns=["id"],
        on_delete="SET NULL",
    )
    _add_fk_not_valid(
        conn=conn,
        table="trig",
        constraint="fk_trig_crt_user_id__user_id",
        columns=["crt_user_id"],
        ref_table="user",
        ref_columns=["id"],
        on_delete="SET NULL",
    )
    _add_fk_not_valid(
        conn=conn,
        table="trig",
        constraint="fk_trig_admin_user_id__user_id",
        columns=["admin_user_id"],
        ref_table="user",
        ref_columns=["id"],
        on_delete="SET NULL",
    )

    # Attr* tables: block deletes (RESTRICT/NO ACTION)
    _add_fk_not_valid(
        conn=conn,
        table="attr",
        constraint="fk_attr_attrsource_id__attrsource_id",
        columns=["attrsource_id"],
        ref_table="attrsource",
        ref_columns=["id"],
        on_delete="RESTRICT",
    )
    _add_fk_not_valid(
        conn=conn,
        table="attrset",
        constraint="fk_attrset_trig_id__trig_id",
        columns=["trig_id"],
        ref_table="trig",
        ref_columns=["id"],
        on_delete="RESTRICT",
    )
    _add_fk_not_valid(
        conn=conn,
        table="attrset",
        constraint="fk_attrset_attrsource_id__attrsource_id",
        columns=["attrsource_id"],
        ref_table="attrsource",
        ref_columns=["id"],
        on_delete="RESTRICT",
    )
    _add_fk_not_valid(
        conn=conn,
        table="attrval",
        constraint="fk_attrval_attr_id__attr_id",
        columns=["attr_id"],
        ref_table="attr",
        ref_columns=["id"],
        on_delete="RESTRICT",
    )
    _add_fk_not_valid(
        conn=conn,
        table="attrset_attrval",
        constraint="fk_attrset_attrval_attrset_id__attrset_id",
        columns=["attrset_id"],
        ref_table="attrset",
        ref_columns=["id"],
        on_delete="RESTRICT",
    )
    _add_fk_not_valid(
        conn=conn,
        table="attrset_attrval",
        constraint="fk_attrset_attrval_attrval_id__attrval_id",
        columns=["attrval_id"],
        ref_table="attrval",
        ref_columns=["id"],
        on_delete="RESTRICT",
    )

    # Trigstats exception: trig delete cascades to trigstats
    _add_fk_not_valid(
        conn=conn,
        table="trigstats",
        constraint="fk_trigstats_id__trig_id",
        columns=["id"],
        ref_table="trig",
        ref_columns=["id"],
        on_delete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Drop constraints first (use IF EXISTS for safety).
    for table, constraint in [
        ("trigstats", "fk_trigstats_id__trig_id"),
        ("attrset_attrval", "fk_attrset_attrval_attrval_id__attrval_id"),
        ("attrset_attrval", "fk_attrset_attrval_attrset_id__attrset_id"),
        ("attrval", "fk_attrval_attr_id__attr_id"),
        ("attrset", "fk_attrset_attrsource_id__attrsource_id"),
        ("attrset", "fk_attrset_trig_id__trig_id"),
        ("attr", "fk_attr_attrsource_id__attrsource_id"),
        ("trig", "fk_trig_admin_user_id__user_id"),
        ("trig", "fk_trig_crt_user_id__user_id"),
        ("trig", "fk_trig_status_id__status_id"),
        ("tphotovote", "fk_tphotovote_user_id__user_id"),
        ("tphotovote", "fk_tphotovote_tphoto_id__tphoto_id"),
        ("tphoto", "fk_tphoto_server_id__server_id"),
        ("tphoto", "fk_tphoto_tlog_id__tlog_id"),
        ("tlog", "fk_tlog_user_id__user_id"),
        ("tlog", "fk_tlog_trig_id__trig_id"),
    ]:
        op.execute(
            sa.text(
                f'ALTER TABLE "{table}" DROP CONSTRAINT IF EXISTS "{constraint}"'
            )
        )

    # Revert nullability (WARNING: will fail if NULLs exist).
    op.alter_column(
        "trig",
        "crt_user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "trig",
        "status_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "tphotovote",
        "user_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "tphotovote",
        "tphoto_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "tphoto",
        "server_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
    op.alter_column(
        "tphoto",
        "tlog_id",
        existing_type=sa.Integer(),
        nullable=False,
    )
