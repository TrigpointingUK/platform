"""add unique index on tphotovote for photo rating upsert

Revision ID: 93d5edf1b17b
Revises: 59f588e86161
Create Date: 2026-04-06 23:40:33.055011

"""

import logging
from typing import Sequence, Union

from alembic import op

logger = logging.getLogger("alembic.runtime.migration")

# revision identifiers, used by Alembic.
revision: str = "93d5edf1b17b"
down_revision: Union[str, Sequence[str], None] = "59f588e86161"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add unique constraint on (tphoto_id, user_id) to support upsert ratings."""
    op.create_unique_constraint(
        "uq_tphotovote_photo_user",
        "tphotovote",
        ["tphoto_id", "user_id"],
    )


def downgrade() -> None:
    """Remove the unique constraint."""
    op.drop_constraint("uq_tphotovote_photo_user", "tphotovote", type_="unique")
