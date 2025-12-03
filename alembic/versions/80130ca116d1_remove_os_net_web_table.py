"""remove os_net_web table

Revision ID: 80130ca116d1
Revises: a4dd9c096762
Create Date: 2025-12-02

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "80130ca116d1"
down_revision: Union[str, Sequence[str], None] = "a4dd9c096762"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Remove the os_net_web table and related column from trig.

    This migration removes:
    - os_net_web table (844 rows) - OS Net Web station lookup, not used in application code
    - trig.os_net_web_id column - Foreign key reference to os_net_web table

    Date: 2025-12-02
    """
    # Drop the os_net_web_id column from trig table first
    op.drop_column("trig", "os_net_web_id")

    # Drop the os_net_web table
    op.drop_table("os_net_web")


def downgrade() -> None:
    """
    Restore the os_net_web table and trig column.

    WARNING: This will recreate the table structure but NOT restore any data.
    Historical data (844 rows) will be permanently lost.
    """
    # Recreate the os_net_web table
    op.create_table(
        "os_net_web",
        sa.Column("stn_number", sa.String(14), nullable=True),
        sa.Column("os_net_web_id", sa.Integer, nullable=True),
    )

    # Recreate the os_net_web_id column on trig table
    op.add_column("trig", sa.Column("os_net_web_id", sa.Integer, nullable=True))
