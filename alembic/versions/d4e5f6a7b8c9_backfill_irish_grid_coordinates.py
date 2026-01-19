"""backfill Irish Grid coordinates

Revision ID: d4e5f6a7b8c9
Revises: c2d3e4f5a6b7
Create Date: 2026-01-18

One-off bulk migration to compute Irish Grid (EPSG:29903) eastings, northings, and
grid references for all trigpoints located within the island of Ireland (ROI + NI).

This uses the country polygons in the area table (area_type_id=3) to identify
trigs in Ireland and Northern Ireland, then converts their WGS84 coordinates
to Irish Grid using pyproj.

The existing osgb_eastings, osgb_northings, and osgb_gridref columns are reused
to store Irish Grid values for trigs in Ireland. The grid_system is determined
at runtime based on the trig's location.

Per project rules, all DML operations log affected rowcounts.
"""

import logging
from typing import Sequence, Union

import sqlalchemy as sa
from pyproj import Transformer

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c2d3e4f5a6b7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

logger = logging.getLogger("alembic.runtime.migration")

# Irish Grid letter layout (single letter, 100km squares)
# The Irish Grid uses a single letter (A-Z excluding I) for 100km squares
# Letters are arranged in a 5x5 grid covering 0-500km E × 0-500km N
IRISH_GRID_LETTERS = [
    ["A", "B", "C", "D", "E"],  # Row 4 (N 400-500km)
    ["F", "G", "H", "J", "K"],  # Row 3 (N 300-400km) - note: no I
    ["L", "M", "N", "O", "P"],  # Row 2 (N 200-300km)
    ["Q", "R", "S", "T", "U"],  # Row 1 (N 100-200km)
    ["V", "W", "X", "Y", "Z"],  # Row 0 (N 0-100km)
]


def eastings_northings_to_irish_gridref(e: int, n: int) -> str:
    """Convert Irish Grid eastings/northings to grid reference string."""
    # Calculate 100km square indices
    e100km = e // 100000  # 0-4
    n100km = n // 100000  # 0-4

    if e100km < 0 or e100km > 4 or n100km < 0 or n100km > 4:
        raise ValueError(f"Coordinates ({e}, {n}) are outside the Irish Grid")

    # Get letter from grid (row index is inverted: 0=north, 4=south)
    row = 4 - n100km
    col = e100km
    letter = IRISH_GRID_LETTERS[row][col]

    # Get numeric part (within 100km square)
    e_within = e % 100000
    n_within = n % 100000

    # Format as 5-digit strings with leading zeros
    e_str = str(e_within).zfill(5)
    n_str = str(n_within).zfill(5)

    return f"{letter} {e_str} {n_str}"


def upgrade() -> None:
    """Convert WGS84 coordinates to Irish Grid for trigs in Ireland/NI.

    1. Query all trigs that fall within Ireland (code='IE') or Northern Ireland
       (code='N92000002') country polygons
    2. For each trig, convert WGS84 lat/lon to Irish Grid (EPSG:29903)
    3. Update osgb_eastings, osgb_northings, osgb_gridref with Irish Grid values
    """
    conn = op.get_bind()

    # Create the pyproj transformer for WGS84 -> Irish Grid
    # EPSG:4326 is WGS84, EPSG:29903 is TM65 Irish Grid
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:29903", always_xy=True)

    # Find all trigs in Ireland and Northern Ireland
    # Uses PostGIS ST_Covers to check if trig.location falls within country polygon
    result = conn.execute(
        sa.text(
            """
            SELECT t.id, t.wgs_lat, t.wgs_long, a.name as country_name
            FROM trig t
            JOIN area a ON ST_Covers(a.boundary, t.location)
            WHERE a.area_type_id = 3  -- Countries
            AND a.code IN ('IE', 'N92000002')  -- Ireland and Northern Ireland
            AND t.wgs_lat IS NOT NULL
            AND t.wgs_long IS NOT NULL
            """
        )
    )

    irish_trigs = result.fetchall()
    logger.info("Found %d trigs in Ireland/Northern Ireland to update", len(irish_trigs))

    if len(irish_trigs) == 0:
        logger.info("No trigs found in Ireland - nothing to do")
        return

    # Process in batches to avoid memory issues
    batch_size = 100
    total_updated = 0
    roi_count = 0
    ni_count = 0

    for i in range(0, len(irish_trigs), batch_size):
        batch = irish_trigs[i : i + batch_size]

        for trig in batch:
            trig_id = trig[0]
            wgs_lat = float(trig[1])
            wgs_long = float(trig[2])
            country_name = trig[3]

            try:
                # Convert WGS84 to Irish Grid
                # pyproj expects (lon, lat) order with always_xy=True
                irish_e, irish_n = transformer.transform(wgs_long, wgs_lat)

                # Round to integers (metres)
                irish_e_int = round(irish_e)
                irish_n_int = round(irish_n)

                # Generate Irish grid reference
                irish_gridref = eastings_northings_to_irish_gridref(
                    irish_e_int, irish_n_int
                )

                # Update the trig record
                update_result = conn.execute(
                    sa.text(
                        """
                        UPDATE trig
                        SET osgb_eastings = :e,
                            osgb_northings = :n,
                            osgb_gridref = :gridref
                        WHERE id = :trig_id
                        """
                    ),
                    {
                        "e": irish_e_int,
                        "n": irish_n_int,
                        "gridref": irish_gridref,
                        "trig_id": trig_id,
                    },
                )

                if update_result.rowcount > 0:
                    total_updated += 1
                    if country_name == "Ireland":
                        roi_count += 1
                    else:
                        ni_count += 1

            except Exception as exc:
                logger.warning(
                    "Failed to convert trig %d (lat=%s, lon=%s): %s",
                    trig_id,
                    wgs_lat,
                    wgs_long,
                    str(exc),
                )

        logger.info(
            "Processed batch %d-%d, updated %d trigs so far",
            i + 1,
            min(i + batch_size, len(irish_trigs)),
            total_updated,
        )

    logger.info(
        "Completed Irish Grid backfill: updated %d trigs total (ROI: %d, NI: %d)",
        total_updated,
        roi_count,
        ni_count,
    )


def downgrade() -> None:
    """Revert Irish Grid coordinates back to OSGB36 for trigs in Ireland/NI.

    This is a lossy operation - we convert the WGS84 coordinates to OSGB36
    even though the trigs are in Ireland. This will produce invalid OSGB36
    coordinates but allows the schema to be consistent if rolling back.

    Note: In practice, you probably don't want to downgrade this migration
    as the OSGB36 coordinates for Irish trigs were likely invalid before anyway.
    """
    conn = op.get_bind()

    # Create the pyproj transformer for WGS84 -> OSGB36
    transformer = Transformer.from_crs("EPSG:4326", "EPSG:27700", always_xy=True)

    # OSGB36 grid letter lookup
    # This is a simplified version - full implementation in coordinate_service.py
    def eastings_northings_to_osgb_gridref(e: int, n: int) -> str:
        """Generate OSGB grid reference (will be invalid for Irish coords)."""
        # For downgrade, just mark as invalid
        return f"** {str(e).zfill(6)[:5]} {str(n).zfill(6)[:5]}"

    # Find all trigs in Ireland and Northern Ireland
    result = conn.execute(
        sa.text(
            """
            SELECT t.id, t.wgs_lat, t.wgs_long
            FROM trig t
            JOIN area a ON ST_Covers(a.boundary, t.location)
            WHERE a.area_type_id = 3
            AND a.code IN ('IE', 'N92000002')
            AND t.wgs_lat IS NOT NULL
            AND t.wgs_long IS NOT NULL
            """
        )
    )

    irish_trigs = result.fetchall()
    logger.info(
        "Found %d trigs in Ireland/Northern Ireland to revert", len(irish_trigs)
    )

    if len(irish_trigs) == 0:
        logger.info("No trigs found in Ireland - nothing to do")
        return

    total_updated = 0

    for trig in irish_trigs:
        trig_id = trig[0]
        wgs_lat = float(trig[1])
        wgs_long = float(trig[2])

        try:
            # Convert WGS84 to OSGB36 (will be invalid for Irish coords)
            osgb_e, osgb_n = transformer.transform(wgs_long, wgs_lat)

            # Round to integers
            osgb_e_int = round(osgb_e)
            osgb_n_int = round(osgb_n)

            # Generate placeholder grid reference (invalid for Irish coords)
            osgb_gridref = eastings_northings_to_osgb_gridref(osgb_e_int, osgb_n_int)

            # Update the trig record
            update_result = conn.execute(
                sa.text(
                    """
                    UPDATE trig
                    SET osgb_eastings = :e,
                        osgb_northings = :n,
                        osgb_gridref = :gridref
                    WHERE id = :trig_id
                    """
                ),
                {
                    "e": osgb_e_int,
                    "n": osgb_n_int,
                    "gridref": osgb_gridref,
                    "trig_id": trig_id,
                },
            )

            if update_result.rowcount > 0:
                total_updated += 1

        except Exception as exc:
            logger.warning(
                "Failed to revert trig %d: %s",
                trig_id,
                str(exc),
            )

    logger.info(
        "Completed Irish Grid revert: updated %d trigs back to (invalid) OSGB36",
        total_updated,
    )

