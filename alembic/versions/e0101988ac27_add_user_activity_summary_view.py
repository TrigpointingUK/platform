"""add user activity summary view

Revision ID: e0101988ac27
Revises: 0e59c3885358
Create Date: 2025-11-23 21:18:59.418564

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

from api.db.user_activity_summary_view import (
    CREATE_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS,
    DROP_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS,
)


# revision identifiers, used by Alembic.
revision: str = "e0101988ac27"
down_revision: Union[str, Sequence[str], None] = "0e59c3885358"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create materialised view summarising user activity for browse endpoint."""
    for statement in CREATE_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS:
        op.execute(sa.text(statement))


def downgrade() -> None:
    """Drop the user activity summary view and related indexes."""
    for statement in DROP_USER_ACTIVITY_SUMMARY_VIEW_STATEMENTS:
        op.execute(sa.text(statement))
