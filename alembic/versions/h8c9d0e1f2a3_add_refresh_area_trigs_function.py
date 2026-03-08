"""add refresh_area_trigs function and area boundary trigger

Revision ID: h8c9d0e1f2a3
Revises: 60e70b6b0b95
Create Date: 2026-03-08

Adds a complementary function refresh_area_trigs(area_id) that rebuilds
trig_area rows for a single area. This pairs with the existing
refresh_trig_areas(trig_id) which rebuilds from the trig side.

Also adds a trigger on area.boundary so that trig_area is automatically
updated when an area's boundary changes.

Together these provide incremental updates from both directions:
- trig location changes  -> refresh_trig_areas (existing)
- area boundary changes  -> refresh_area_trigs (new)
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "h8c9d0e1f2a3"
down_revision: Union[str, Sequence[str], None] = "60e70b6b0b95"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CREATE_REFRESH_AREA_FUNCTION = """
CREATE OR REPLACE FUNCTION refresh_area_trigs(p_area_id INTEGER)
RETURNS void AS $$
BEGIN
    DELETE FROM trig_area WHERE area_id = p_area_id;

    INSERT INTO trig_area (trig_id, area_id, area_type_id, area_type_code)
    SELECT
        t.id AS trig_id,
        a.id AS area_id,
        at.id AS area_type_id,
        at.code AS area_type_code
    FROM area a
    JOIN area_type at ON a.area_type_id = at.id
    CROSS JOIN trig t
    WHERE a.id = p_area_id
      AND t.location IS NOT NULL
      AND ST_Covers(a.boundary::geometry, t.location::geometry);
END;
$$ LANGUAGE plpgsql
"""

CREATE_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION area_boundary_changed()
RETURNS trigger AS $$
BEGIN
    IF (TG_OP = 'INSERT' AND NEW.boundary IS NOT NULL) OR
       (TG_OP = 'UPDATE' AND NEW.boundary IS DISTINCT FROM OLD.boundary) THEN
        PERFORM refresh_area_trigs(NEW.id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

CREATE_TRIGGER = """
CREATE TRIGGER area_boundary_update_trigs
AFTER INSERT OR UPDATE OF boundary ON area
FOR EACH ROW
EXECUTE FUNCTION area_boundary_changed()
"""


def upgrade() -> None:
    """Add refresh_area_trigs function and area boundary trigger."""
    logger.info("Creating refresh_area_trigs function...")
    op.execute(sa.text(CREATE_REFRESH_AREA_FUNCTION))

    logger.info("Creating area_boundary_changed trigger function...")
    op.execute(sa.text(CREATE_TRIGGER_FUNCTION))

    logger.info("Creating trigger on area.boundary...")
    op.execute(sa.text(CREATE_TRIGGER))

    logger.info("Migration complete: refresh_area_trigs and trigger created")


def downgrade() -> None:
    """Remove refresh_area_trigs function and area boundary trigger."""
    logger.info("Dropping area boundary trigger and functions...")
    op.execute(sa.text("DROP TRIGGER IF EXISTS area_boundary_update_trigs ON area"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS area_boundary_changed()"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS refresh_area_trigs(INTEGER)"))

    logger.info("Downgrade complete: refresh_area_trigs and trigger removed")
