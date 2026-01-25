"""add primary key to trigstats table

Revision ID: b5c6d7e8f901
Revises: a5b6c7d8e9f0
Create Date: 2026-01-25 11:20:00.000000

The trigstats table in the legacy database was missing a primary key constraint
on the id column. This is required for PostgreSQL's ON CONFLICT upsert syntax
used by update_trigstats().
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "b5c6d7e8f901"
down_revision: Union[str, Sequence[str], None] = "a5b6c7d8e9f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add primary key constraint to trigstats.id column."""
    connection = op.get_bind()

    # Check if primary key already exists
    check_pk = sa.text("""
        SELECT COUNT(*)
        FROM pg_constraint c
        JOIN pg_class t ON c.conrelid = t.oid
        WHERE t.relname = 'trigstats'
        AND c.contype = 'p'
    """)
    pk_exists = connection.execute(check_pk).scalar() > 0

    if pk_exists:
        logger.info("Primary key already exists on trigstats table, skipping")
        return

    # Add primary key constraint
    op.create_primary_key("trigstats_pkey", "trigstats", ["id"])
    logger.info("Added primary key constraint to trigstats.id")


def downgrade() -> None:
    """Remove primary key constraint from trigstats table."""
    op.drop_constraint("trigstats_pkey", "trigstats", type_="primary")
    logger.info("Removed primary key constraint from trigstats table")

