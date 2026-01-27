"""convert trig_area_mv materialized view to regular table with triggers

Revision ID: f5a6b7c8d9e0
Revises: e9f5a7b34d02
Create Date: 2026-01-27

This migration converts the trig_area_mv materialized view to a regular table
with triggers for incremental updates. This allows instant updates when a
trig's location changes, rather than requiring a full materialized view refresh.

Benefits:
- Instant updates when trig location changes
- Can refresh areas for a single trig via refresh_trig_areas(trig_id)
- No pg_cron job needed for normal operations
- Supports the deprecation of trig.county column
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

logger = logging.getLogger(__name__)

# revision identifiers, used by Alembic.
revision: str = "f5a6b7c8d9e0"
down_revision: Union[str, Sequence[str], None] = "b5c6d7e8f901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# pg_cron job name from previous migration
PGCRON_JOB_NAME = "refresh_trig_area_mv_daily"

# SQL to create the trig_area table
# Note: Foreign keys are omitted because the legacy trig table lacks proper
# unique constraints. Data integrity is maintained by the trigger logic.
CREATE_TABLE = """
CREATE TABLE trig_area (
    trig_id INTEGER NOT NULL,
    area_id INTEGER NOT NULL,
    area_type_id INTEGER NOT NULL,
    area_type_code VARCHAR(50) NOT NULL,
    PRIMARY KEY (trig_id, area_id)
)
"""

# SQL to populate the table from the existing materialized view
POPULATE_FROM_MV = """
INSERT INTO trig_area (trig_id, area_id, area_type_id, area_type_code)
SELECT trig_id, area_id, area_type_id, area_type_code
FROM trig_area_mv
"""

# SQL to create indexes (matching the old matview indexes)
CREATE_TRIG_INDEX = """
CREATE INDEX ix_trig_area_trig_id ON trig_area (trig_id)
"""

CREATE_AREA_INDEX = """
CREATE INDEX ix_trig_area_area_id ON trig_area (area_id)
"""

CREATE_TYPE_INDEX = """
CREATE INDEX ix_trig_area_area_type_id ON trig_area (area_type_id)
"""

CREATE_TYPE_CODE_INDEX = """
CREATE INDEX ix_trig_area_area_type_code ON trig_area (area_type_code)
"""

# SQL to create the refresh function for a single trig
CREATE_REFRESH_FUNCTION = """
CREATE OR REPLACE FUNCTION refresh_trig_areas(p_trig_id INTEGER)
RETURNS void AS $$
BEGIN
    -- Delete existing entries for this trig
    DELETE FROM trig_area WHERE trig_id = p_trig_id;
    
    -- Insert new entries based on current location
    INSERT INTO trig_area (trig_id, area_id, area_type_id, area_type_code)
    SELECT 
        t.id AS trig_id,
        a.id AS area_id,
        at.id AS area_type_id,
        at.code AS area_type_code
    FROM trig t
    CROSS JOIN area a
    JOIN area_type at ON a.area_type_id = at.id
    WHERE t.id = p_trig_id
      AND t.location IS NOT NULL
      AND ST_Covers(a.boundary::geometry, t.location::geometry);
END;
$$ LANGUAGE plpgsql
"""

# SQL to create the trigger function
CREATE_TRIGGER_FUNCTION = """
CREATE OR REPLACE FUNCTION trig_location_changed()
RETURNS trigger AS $$
BEGIN
    -- Only refresh if location actually changed (or is new)
    IF (TG_OP = 'INSERT' AND NEW.location IS NOT NULL) OR
       (TG_OP = 'UPDATE' AND NEW.location IS DISTINCT FROM OLD.location) THEN
        PERFORM refresh_trig_areas(NEW.id);
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql
"""

# SQL to create the trigger
CREATE_TRIGGER = """
CREATE TRIGGER trig_location_update_areas
AFTER INSERT OR UPDATE OF location ON trig
FOR EACH ROW
EXECUTE FUNCTION trig_location_changed()
"""


def _cron_available(connection) -> bool:
    """Check if pg_cron extension is installed."""
    check_stmt = sa.text(
        "SELECT EXISTS (SELECT 1 FROM pg_namespace WHERE nspname = 'cron')"
    )
    return bool(connection.execute(check_stmt).scalar())


def _unschedule_pgcron_job(connection) -> None:
    """Remove the pg_cron job for materialized view refresh."""
    if not _cron_available(connection):
        logger.info("pg_cron not available, skipping job removal")
        return

    stmt = sa.text(
        """
        SELECT cron.unschedule(jobid)
        FROM cron.job
        WHERE jobname = :jobname
        """
    ).bindparams(jobname=PGCRON_JOB_NAME)
    connection.execute(stmt)
    logger.info(f"Removed pg_cron job: {PGCRON_JOB_NAME}")


def _schedule_pgcron_job(connection) -> None:
    """Re-schedule the pg_cron job (for downgrade)."""
    if not _cron_available(connection):
        logger.warning("pg_cron not available, cannot reschedule job")
        return

    stmt = sa.text("SELECT cron.schedule(:jobname, :cron, :command)").bindparams(
        jobname=PGCRON_JOB_NAME,
        cron="0 3 * * *",
        command="REFRESH MATERIALIZED VIEW CONCURRENTLY trig_area_mv",
    )
    connection.execute(stmt)
    logger.info(f"Re-scheduled pg_cron job: {PGCRON_JOB_NAME}")


def upgrade() -> None:
    """Convert trig_area_mv materialized view to trig_area table with triggers."""
    connection = op.get_bind()

    # 1. Create the new table
    logger.info("Creating trig_area table...")
    op.execute(sa.text(CREATE_TABLE))

    # 2. Populate from existing materialized view
    logger.info("Populating trig_area from trig_area_mv...")
    result = connection.execute(sa.text(POPULATE_FROM_MV))
    logger.info(f"Inserted {result.rowcount} rows into trig_area")

    # 3. Create indexes
    logger.info("Creating indexes...")
    op.execute(sa.text(CREATE_TRIG_INDEX))
    op.execute(sa.text(CREATE_AREA_INDEX))
    op.execute(sa.text(CREATE_TYPE_INDEX))
    op.execute(sa.text(CREATE_TYPE_CODE_INDEX))

    # 4. Create the refresh function
    logger.info("Creating refresh_trig_areas function...")
    op.execute(sa.text(CREATE_REFRESH_FUNCTION))

    # 5. Create the trigger function and trigger
    logger.info("Creating trigger for trig location changes...")
    op.execute(sa.text(CREATE_TRIGGER_FUNCTION))
    op.execute(sa.text(CREATE_TRIGGER))

    # 6. Remove the pg_cron job (no longer needed)
    logger.info("Removing pg_cron refresh job...")
    _unschedule_pgcron_job(connection)

    # 7. Drop the old materialized view
    logger.info("Dropping trig_area_mv materialized view...")
    op.execute(sa.text("DROP MATERIALIZED VIEW IF EXISTS trig_area_mv CASCADE"))

    # 8. Grant permissions to backups role (matching original matview permissions)
    logger.info("Granting SELECT to backups role...")
    op.execute(sa.text("GRANT SELECT ON trig_area TO backups"))

    logger.info("Migration complete: trig_area_mv converted to trig_area table")


def downgrade() -> None:
    """Revert to trig_area_mv materialized view."""
    connection = op.get_bind()

    # 1. Drop the trigger and functions
    logger.info("Dropping trigger and functions...")
    op.execute(sa.text("DROP TRIGGER IF EXISTS trig_location_update_areas ON trig"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS trig_location_changed()"))
    op.execute(sa.text("DROP FUNCTION IF EXISTS refresh_trig_areas(INTEGER)"))

    # 2. Recreate the materialized view from the table data
    logger.info("Recreating trig_area_mv materialized view...")
    op.execute(
        sa.text(
            """
        CREATE MATERIALIZED VIEW trig_area_mv AS
        SELECT trig_id, area_id, area_type_id, area_type_code
        FROM trig_area
        WITH DATA
        """
        )
    )

    # 3. Create indexes on the materialized view
    logger.info("Creating indexes on materialized view...")
    op.execute(
        sa.text(
            "CREATE UNIQUE INDEX ix_trig_area_mv_pk ON trig_area_mv (trig_id, area_id)"
        )
    )
    op.execute(
        sa.text("CREATE INDEX ix_trig_area_mv_trig_id ON trig_area_mv (trig_id)")
    )
    op.execute(
        sa.text("CREATE INDEX ix_trig_area_mv_area_id ON trig_area_mv (area_id)")
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_trig_area_mv_area_type_id ON trig_area_mv (area_type_id)"
        )
    )
    op.execute(
        sa.text(
            "CREATE INDEX ix_trig_area_mv_area_type_code ON trig_area_mv (area_type_code)"
        )
    )

    # 4. Grant permissions
    op.execute(sa.text("GRANT SELECT ON trig_area_mv TO backups"))

    # 5. Re-schedule the pg_cron job
    logger.info("Re-scheduling pg_cron refresh job...")
    _schedule_pgcron_job(connection)

    # 6. Drop the table
    logger.info("Dropping trig_area table...")
    op.execute(sa.text("DROP TABLE IF EXISTS trig_area CASCADE"))

    logger.info("Downgrade complete: reverted to trig_area_mv materialized view")

