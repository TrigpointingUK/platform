"""add trig_area materialized view

Revision ID: d7e4f8a23c91
Revises: c8a3f2e91b47
Create Date: 2025-12-02

This migration creates a materialized view that precomputes which areas
contain each trigpoint. This dramatically speeds up queries like:
- "Which counties/regions does this trigpoint fall within?"
- "Which trigpoints are in this area?"

The view should be refreshed periodically (e.g., nightly via pg_cron)
or after bulk updates to trig locations or area boundaries.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d7e4f8a23c91"
down_revision: Union[str, Sequence[str], None] = "c8a3f2e91b47"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# SQL statements for creating the materialized view
CREATE_MATERIALIZED_VIEW = """
CREATE MATERIALIZED VIEW trig_area_mv AS
SELECT 
    t.id AS trig_id,
    a.id AS area_id,
    at.id AS area_type_id,
    at.code AS area_type_code
FROM trig t
CROSS JOIN area a
JOIN area_type at ON a.area_type_id = at.id
WHERE t.location IS NOT NULL
  AND ST_Covers(a.boundary::geometry, t.location::geometry)
WITH DATA
"""

# Unique index is required for REFRESH CONCURRENTLY
CREATE_UNIQUE_INDEX = """
CREATE UNIQUE INDEX ix_trig_area_mv_pk 
ON trig_area_mv (trig_id, area_id)
"""

# Additional indexes for common query patterns
CREATE_TRIG_INDEX = """
CREATE INDEX ix_trig_area_mv_trig_id 
ON trig_area_mv (trig_id)
"""

CREATE_AREA_INDEX = """
CREATE INDEX ix_trig_area_mv_area_id 
ON trig_area_mv (area_id)
"""

CREATE_TYPE_INDEX = """
CREATE INDEX ix_trig_area_mv_area_type_id 
ON trig_area_mv (area_type_id)
"""

CREATE_TYPE_CODE_INDEX = """
CREATE INDEX ix_trig_area_mv_area_type_code 
ON trig_area_mv (area_type_code)
"""


def upgrade() -> None:
    """Create the trig_area materialized view with indexes."""
    # Create the materialized view
    op.execute(sa.text(CREATE_MATERIALIZED_VIEW))
    
    # Create indexes
    op.execute(sa.text(CREATE_UNIQUE_INDEX))
    op.execute(sa.text(CREATE_TRIG_INDEX))
    op.execute(sa.text(CREATE_AREA_INDEX))
    op.execute(sa.text(CREATE_TYPE_INDEX))
    op.execute(sa.text(CREATE_TYPE_CODE_INDEX))


def downgrade() -> None:
    """Drop the trig_area materialized view."""
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS trig_area_mv CASCADE"))
