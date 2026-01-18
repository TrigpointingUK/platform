"""migrate status_max to default_groups

Revision ID: b1c2d3e4f5a6
Revises: 047ece94f471
Create Date: 2026-01-18

Data migration to convert user.status_max values to ui_prefs.default_groups lists.

The status_max integer represented the maximum status_id a user wanted to see.
This is now replaced by a list of trig_type_group.code values stored in ui_prefs.

Mapping:
- status_max = 10 → ["PILLAR"]
- status_max = 20 → ["PILLAR", "FBM"]
- status_max = 30 → ["PILLAR", "FBM", "SURVEY_MARK"]
- status_max = 40 → ["PILLAR", "FBM", "SURVEY_MARK", "INTERSECTED"]
- status_max = 50 → ["PILLAR", "FBM", "SURVEY_MARK", "INTERSECTED", "ACTIVE"]
- status_max = 60 → ["PILLAR", "FBM", "SURVEY_MARK", "INTERSECTED", "ACTIVE", "OTHER"]
- status_max = 0 or NULL → No change (will use application defaults)
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b1c2d3e4f5a6"
down_revision: Union[str, Sequence[str], None] = "047ece94f471"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger(__name__)


# Mapping from status_max to default_groups list
STATUS_MAX_TO_GROUPS = {
    10: ["PILLAR"],
    20: ["PILLAR", "FBM"],
    30: ["PILLAR", "FBM", "SURVEY_MARK"],
    40: ["PILLAR", "FBM", "SURVEY_MARK", "INTERSECTED"],
    50: ["PILLAR", "FBM", "SURVEY_MARK", "INTERSECTED", "ACTIVE"],
    60: ["PILLAR", "FBM", "SURVEY_MARK", "INTERSECTED", "ACTIVE", "OTHER"],
}


def upgrade() -> None:
    """Convert status_max values to default_groups in ui_prefs.

    For each status_max value, we update ui_prefs to include the corresponding
    default_groups list. We use PostgreSQL's jsonb_set function to merge into
    existing ui_prefs without overwriting other settings.

    Users with status_max = 0 or NULL are not updated (they will use application
    defaults which are ["PILLAR", "FBM"]).
    """
    conn = op.get_bind()

    for status_max, groups in STATUS_MAX_TO_GROUPS.items():
        # Convert Python list to PostgreSQL array literal for jsonb
        groups_json = str(groups).replace("'", '"')

        # Update users where:
        # - status_max matches
        # - ui_prefs doesn't already have default_groups set
        #
        # Uses COALESCE to handle NULL ui_prefs, and jsonb_set to merge
        result = conn.execute(
            sa.text(
                """
                UPDATE "user"
                SET ui_prefs = jsonb_set(
                    COALESCE(ui_prefs, '{}'::jsonb),
                    '{default_groups}',
                    :groups_json::jsonb,
                    true
                )
                WHERE status_max = :status_max
                AND (
                    ui_prefs IS NULL
                    OR NOT (ui_prefs ? 'default_groups')
                )
                """
            ),
            {"status_max": status_max, "groups_json": groups_json},
        )
        logger.info(
            "Updated %d users with status_max=%d to default_groups=%s",
            result.rowcount,
            status_max,
            groups,
        )


def downgrade() -> None:
    """Remove default_groups from ui_prefs.

    This removes the default_groups key from ui_prefs for all users,
    but does not restore the original status_max values (which are
    still present in the status_max column).
    """
    conn = op.get_bind()

    result = conn.execute(
        sa.text(
            """
            UPDATE "user"
            SET ui_prefs = ui_prefs - 'default_groups'
            WHERE ui_prefs ? 'default_groups'
            """
        )
    )
    logger.info(
        "Removed default_groups from ui_prefs for %d users",
        result.rowcount,
    )
