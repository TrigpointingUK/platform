"""trigstats nullable dates and remove area_osgb_height

Revision ID: d408a5e6b274
Revises: a8b2c4d6e8f0
Create Date: 2025-12-07 22:12:45.621145

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "d408a5e6b274"
down_revision: Union[str, Sequence[str], None] = "a8b2c4d6e8f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Make date columns nullable and remove unused area_osgb_height column.

    The date columns were using epoch (1970-01-01) as a NULL sentinel,
    which is fragile and causes bugs. Making them properly nullable is cleaner.
    """
    # Make date columns nullable
    op.alter_column(
        "trigstats",
        "logged_first",
        existing_type=sa.DATE(),
        nullable=True,
    )
    op.alter_column(
        "trigstats",
        "logged_last",
        existing_type=sa.DATE(),
        nullable=True,
    )
    op.alter_column(
        "trigstats",
        "found_last",
        existing_type=sa.DATE(),
        nullable=True,
    )

    # Convert existing epoch dates to NULL
    op.execute(
        "UPDATE trigstats SET logged_first = NULL WHERE logged_first = '1970-01-01'"
    )
    op.execute(
        "UPDATE trigstats SET logged_last = NULL WHERE logged_last = '1970-01-01'"
    )
    op.execute("UPDATE trigstats SET found_last = NULL WHERE found_last = '1970-01-01'")

    # Remove unused column
    op.drop_column("trigstats", "area_osgb_height")


def downgrade() -> None:
    """Reverse the changes - restore NOT NULL and add back area_osgb_height."""
    # Add back the column
    op.add_column(
        "trigstats",
        sa.Column(
            "area_osgb_height",
            sa.SMALLINT(),
            nullable=False,
            server_default="0",
        ),
    )

    # Convert NULLs back to epoch dates
    op.execute(
        "UPDATE trigstats SET logged_first = '1970-01-01' WHERE logged_first IS NULL"
    )
    op.execute(
        "UPDATE trigstats SET logged_last = '1970-01-01' WHERE logged_last IS NULL"
    )
    op.execute(
        "UPDATE trigstats SET found_last = '1970-01-01' WHERE found_last IS NULL"
    )

    # Restore NOT NULL constraints
    op.alter_column(
        "trigstats",
        "logged_first",
        existing_type=sa.DATE(),
        nullable=False,
    )
    op.alter_column(
        "trigstats",
        "logged_last",
        existing_type=sa.DATE(),
        nullable=False,
    )
    op.alter_column(
        "trigstats",
        "found_last",
        existing_type=sa.DATE(),
        nullable=False,
    )
