"""rename trig_type_group to trig_category

Revision ID: 2560d7a0ad69
Revises: d4e5f6a7b8c9
Create Date: 2026-01-19

Renames the trig_type_group table to trig_category and changes
the group_id column in trig_type to category_id. This is a naming
refactor only - the data and structure remain the same.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2560d7a0ad69"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    """Rename trig_type_group to trig_category and group_id to category_id."""

    # 1. Drop the foreign key constraint on trig_type.group_id
    logger.info("Dropping foreign key constraint on trig_type.group_id...")
    op.drop_constraint(
        "trig_type_group_id_fkey", "trig_type", type_="foreignkey"
    )

    # 2. Drop the unique constraint on (group_id, sort_order)
    logger.info("Dropping unique constraint uq_trig_type_group_sort...")
    op.drop_constraint("uq_trig_type_group_sort", "trig_type", type_="unique")

    # 3. Rename the table trig_type_group -> trig_category
    logger.info("Renaming table trig_type_group to trig_category...")
    op.rename_table("trig_type_group", "trig_category")

    # 4. Rename the column group_id -> category_id in trig_type
    logger.info("Renaming column group_id to category_id in trig_type...")
    op.alter_column(
        "trig_type",
        "group_id",
        new_column_name="category_id",
    )

    # 5. Recreate the foreign key constraint with new names
    logger.info("Creating foreign key constraint on trig_type.category_id...")
    op.create_foreign_key(
        "trig_type_category_id_fkey",
        "trig_type",
        "trig_category",
        ["category_id"],
        ["id"],
    )

    # 6. Recreate the unique constraint with new name
    logger.info("Creating unique constraint uq_trig_type_category_sort...")
    op.create_unique_constraint(
        "uq_trig_type_category_sort",
        "trig_type",
        ["category_id", "sort_order"],
    )

    # 7. Create index on category_id (was not present before, but model expects it)
    logger.info("Creating index ix_trig_type_category_id...")
    op.create_index("ix_trig_type_category_id", "trig_type", ["category_id"])

    logger.info("Rename complete: trig_type_group -> trig_category")


def downgrade() -> None:
    """Revert trig_category back to trig_type_group."""

    # 1. Drop the index on category_id
    op.drop_index("ix_trig_type_category_id", table_name="trig_type")

    # 2. Drop the foreign key constraint on trig_type.category_id
    op.drop_constraint(
        "trig_type_category_id_fkey", "trig_type", type_="foreignkey"
    )

    # 3. Drop the unique constraint
    op.drop_constraint("uq_trig_type_category_sort", "trig_type", type_="unique")

    # 4. Rename the table back: trig_category -> trig_type_group
    op.rename_table("trig_category", "trig_type_group")

    # 5. Rename the column back: category_id -> group_id
    op.alter_column(
        "trig_type",
        "category_id",
        new_column_name="group_id",
    )

    # 6. Recreate the original foreign key constraint
    op.create_foreign_key(
        "trig_type_group_id_fkey",
        "trig_type",
        "trig_type_group",
        ["group_id"],
        ["id"],
    )

    # 7. Recreate the original unique constraint
    op.create_unique_constraint(
        "uq_trig_type_group_sort",
        "trig_type",
        ["group_id", "sort_order"],
    )
