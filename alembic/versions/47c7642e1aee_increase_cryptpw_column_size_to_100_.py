"""increase cryptpw column size to 100 characters

Revision ID: 47c7642e1aee
Revises: dd1db8f80e27
Create Date: 2025-12-01 17:39:31.981877

This migration increases the size of the cryptpw column from VARCHAR(34) to VARCHAR(100).

The original size of 34 characters was sufficient for legacy bcrypt hashes.
However, the user creation process now generates random tokens using
secrets.token_urlsafe(32) which produces 43-character strings.

The model already specifies VARCHAR(100), so this migration brings the
database schema in line with the model definition.

Date: 2025-12-01
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "47c7642e1aee"
down_revision: Union[str, Sequence[str], None] = "dd1db8f80e27"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Increase cryptpw column size from 34 to 100 characters."""
    op.alter_column(
        "user",
        "cryptpw",
        type_=sa.String(100),
        existing_type=sa.String(34),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert cryptpw column size back to 34 characters.
    
    WARNING: This may truncate data if any passwords are longer than 34 characters.
    """
    op.alter_column(
        "user",
        "cryptpw",
        type_=sa.String(34),
        existing_type=sa.String(100),
        existing_nullable=True,
    )
