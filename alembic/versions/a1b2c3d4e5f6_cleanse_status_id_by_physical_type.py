"""cleanse status_id by physical_type

Revision ID: a1b2c3d4e5f6
Revises: e58c1c44b2a6
Create Date: 2025-12-14

Data cleansing migration to ensure trig.status_id is consistent with trig.physical_type.

For records with status_id < 50:
- physical_type in ['Pillar'] -> status_id = 10
- physical_type in ['FBM', 'Curry Stool', 'Cannon'] -> status_id = 20
- physical_type in ['Intersected', 'Intersected Station'] -> status_id = 40
- physical_type in ['Unknown - user added'] -> status_id = 50
- All other physical_types -> status_id = 30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a1b2c3d4e5f6"
down_revision: Union[str, Sequence[str], None] = "e58c1c44b2a6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Cleanse status_id based on physical_type for records where status_id < 50.
    
    Each UPDATE targets mutually exclusive physical_type values, so order doesn't matter.
    The final UPDATE catches any physical_type not explicitly listed and sets status_id = 30.
    """
    # Update status_id = 10 for Pillar
    op.execute(
        sa.text(
            "UPDATE trig "
            "SET status_id = 10 "
            "WHERE status_id < 50 AND LOWER(physical_type) = 'pillar'"
        )
    )
    
    # Update status_id = 20 for FBM, Curry Stool, Cannon
    op.execute(
        sa.text(
            "UPDATE trig "
            "SET status_id = 20 "
            "WHERE status_id < 50 AND LOWER(physical_type) IN ('fbm', 'curry stool', 'cannon')"
        )
    )
    
    # Update status_id = 40 for Intersected, Intersected Station
    op.execute(
        sa.text(
            "UPDATE trig "
            "SET status_id = 40 "
            "WHERE status_id < 50 AND LOWER(physical_type) IN ('intersected', 'intersected station')"
        )
    )
    
    # Update status_id = 50 for Unknown - user added
    op.execute(
        sa.text(
            "UPDATE trig "
            "SET status_id = 50 "
            "WHERE status_id < 50 AND LOWER(physical_type) = 'unknown - user added'"
        )
    )
    
    # Update status_id = 30 for all other physical_types not yet updated
    # These are records where status_id is still < 50 after the above updates
    op.execute(
        sa.text(
            "UPDATE trig "
            "SET status_id = 30 "
            "WHERE status_id < 50 AND LOWER(physical_type) NOT IN "
            "('pillar', 'fbm', 'curry stool', 'cannon', 'intersected', 'intersected station', 'unknown - user added')"
        )
    )


def downgrade() -> None:
    """Downgrade is not possible for this data cleansing migration.
    
    WARNING: This migration cannot be reverted as we do not store the original
    status_id values. The original data would need to be restored from a backup.
    """
    # Cannot reliably revert this migration
    # The original status_id values are not preserved
    pass

