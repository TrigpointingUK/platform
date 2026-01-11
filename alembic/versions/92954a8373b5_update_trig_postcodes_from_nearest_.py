"""update trig postcodes from nearest postcode

Revision ID: 92954a8373b5
Revises: fa4e26eab380
Create Date: 2026-01-11 15:33:18.989848

This migration updates all trig.postcode values to the nearest postcode
within 5km using PostGIS spatial queries. Trigs with no postcode within
5km will have their postcode set to NULL.
"""

import logging
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "92954a8373b5"
down_revision: Union[str, Sequence[str], None] = "fa4e26eab380"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")


def upgrade() -> None:
    """Update trig.postcode to nearest postcode within 5km using PostGIS."""
    conn = op.get_bind()

    logger.info("Updating trig.postcode to nearest postcode within 5km...")
    result = conn.execute(
        sa.text(
            """
            UPDATE trig t
            SET postcode = nearest.code
            FROM (
                SELECT t2.id,
                       (SELECT p.code
                        FROM postcodes p
                        WHERE ST_DWithin(p.location, t2.location, 5000)
                        ORDER BY p.location <-> t2.location
                        LIMIT 1
                       ) AS code
                FROM trig t2
            ) nearest
            WHERE t.id = nearest.id
            """
        )
    )
    logger.info("Updated postcode for %d trig records", result.rowcount)


def downgrade() -> None:
    """No downgrade - postcode values cannot be restored to previous state."""
    logger.info("Downgrade not supported: previous postcode values were not preserved")
