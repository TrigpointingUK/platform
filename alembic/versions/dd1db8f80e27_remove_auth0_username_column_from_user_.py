"""remove auth0_username column from user table

Revision ID: dd1db8f80e27
Revises: 6b9cf6a8d304
Create Date: 2025-12-01 17:11:51.041714

This migration removes the auth0_username column from the user table.
This field was used temporarily during the legacy user migration process
to store the Auth0 username separately from the database username.

Now that migration is complete, this field is no longer needed:
- Auth0 nicknames are managed via the Auth0 Management API
- The user.name field stores the display username
- The auth0_user_id field provides the Auth0 linkage

Date: 2025-12-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "dd1db8f80e27"
down_revision: Union[str, Sequence[str], None] = "6b9cf6a8d304"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove auth0_username column from user table."""
    op.drop_column("user", "auth0_username")


def downgrade() -> None:
    """Restore auth0_username column to user table."""
    op.add_column(
        "user",
        sa.Column("auth0_username", sa.String(255), nullable=True),
    )
