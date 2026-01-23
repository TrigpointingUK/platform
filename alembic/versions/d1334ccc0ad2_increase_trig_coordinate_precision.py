"""increase_trig_coordinate_precision

Revision ID: d1334ccc0ad2
Revises: 08ed5fe3d3e8
Create Date: 2026-01-23 19:21:00.876826

Increase coordinate precision in the trig table:
- wgs_lat/wgs_long: from NUMERIC(7,5) to NUMERIC(11,8) / NUMERIC(12,8) for ~1mm precision
- wgs_height: from INTEGER to NUMERIC(8,4) for 0.1mm precision
- osgb_eastings/northings: from INTEGER to NUMERIC(10,4) for 0.1mm precision
- osgb_height: from INTEGER to NUMERIC(8,4) for 0.1mm precision

This supports storing high-precision source data (6 decimal places of seconds accuracy).
Existing integer values are preserved with .0000 decimal places.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "d1334ccc0ad2"
down_revision: Union[str, Sequence[str], None] = "08ed5fe3d3e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Increase coordinate precision in trig table."""
    # WGS84 latitude: expand from NUMERIC(7,5) to NUMERIC(11,8)
    # Allows values like -90.12345678 (8 decimal places)
    op.alter_column(
        "trig",
        "wgs_lat",
        existing_type=sa.NUMERIC(7, 5),
        type_=sa.NUMERIC(11, 8),
        existing_nullable=False,
    )

    # WGS84 longitude: expand from NUMERIC(7,5) to NUMERIC(12,8)
    # Allows values like -180.12345678 (8 decimal places)
    op.alter_column(
        "trig",
        "wgs_long",
        existing_type=sa.NUMERIC(7, 5),
        type_=sa.NUMERIC(12, 8),
        existing_nullable=False,
    )

    # WGS84 height: change from INTEGER to NUMERIC(8,4)
    # Allows values like 9999.1234 metres with 0.1mm precision
    op.alter_column(
        "trig",
        "wgs_height",
        existing_type=sa.INTEGER(),
        type_=sa.NUMERIC(8, 4),
        existing_nullable=True,
    )

    # OSGB eastings: change from INTEGER to NUMERIC(10,4)
    # Allows values like 999999.1234 metres with 0.1mm precision
    op.alter_column(
        "trig",
        "osgb_eastings",
        existing_type=sa.INTEGER(),
        type_=sa.NUMERIC(10, 4),
        existing_nullable=False,
    )

    # OSGB northings: change from INTEGER to NUMERIC(11,4)
    # Allows values like 1234567.1234 metres (UK northings can exceed 1,000,000m in Scotland)
    op.alter_column(
        "trig",
        "osgb_northings",
        existing_type=sa.INTEGER(),
        type_=sa.NUMERIC(11, 4),
        existing_nullable=False,
    )

    # OSGB height: change from INTEGER to NUMERIC(8,4)
    # Allows values like 9999.1234 metres with 0.1mm precision
    op.alter_column(
        "trig",
        "osgb_height",
        existing_type=sa.INTEGER(),
        type_=sa.NUMERIC(8, 4),
        existing_nullable=True,
    )


def downgrade() -> None:
    """Revert coordinate precision to original types."""
    # Note: Downgrade will truncate decimal places and may lose precision

    op.alter_column(
        "trig",
        "wgs_lat",
        existing_type=sa.NUMERIC(11, 8),
        type_=sa.NUMERIC(7, 5),
        existing_nullable=False,
    )

    op.alter_column(
        "trig",
        "wgs_long",
        existing_type=sa.NUMERIC(12, 8),
        type_=sa.NUMERIC(7, 5),
        existing_nullable=False,
    )

    op.alter_column(
        "trig",
        "wgs_height",
        existing_type=sa.NUMERIC(8, 4),
        type_=sa.INTEGER(),
        existing_nullable=True,
    )

    op.alter_column(
        "trig",
        "osgb_eastings",
        existing_type=sa.NUMERIC(10, 4),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )

    op.alter_column(
        "trig",
        "osgb_northings",
        existing_type=sa.NUMERIC(11, 4),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )

    op.alter_column(
        "trig",
        "osgb_height",
        existing_type=sa.NUMERIC(8, 4),
        type_=sa.INTEGER(),
        existing_nullable=True,
    )
