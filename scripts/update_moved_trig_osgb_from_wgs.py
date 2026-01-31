#!/usr/bin/env python3
"""
Update OSGB coordinates from WGS84 using OSTN15 transformation for moved trigs.

For trigpoints with condition='M' (moved), recalculates the OSGB coordinates
from the WGS84 coordinates using OSTN15 transformation.

Usage:
    python scripts/update_trig_wgs_from_osgb.py [--apply] [--threshold METRES]

Options:
    --apply         Actually apply the updates (default is dry-run)
    --threshold     Distance threshold in metres (default: 0.5)
    --limit N       Only process first N trigpoints needing update
"""

import argparse
import math
import sys
from pathlib import Path

# Add the project root to the path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from api.core.config import settings
from api.core.logging import get_logger
from api.services.coordinate_service import (
    convert_wgs84_to_osgb,
    eastings_northings_to_gridref,
)

logger = get_logger(__name__)


def calculate_osgb_distance_metres(e1: float, n1: float, e2: float, n2: float) -> float:
    """
    Calculate distance between two OSGB coordinates in metres.
    
    Simple Pythagorean distance - accurate for OSGB as it's a projected CRS.
    """
    return math.sqrt((e2 - e1) ** 2 + (n2 - n1) ** 2)


def main():
    parser = argparse.ArgumentParser(
        description="Update OSGB coordinates from WGS84 using OSTN15 for moved trigs"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Actually apply updates (default is dry-run)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=0.5,
        help="Distance threshold in metres (default: 0.5)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Only process first N trigpoints needing update",
    )
    args = parser.parse_args()

    dry_run = not args.apply
    threshold_metres = args.threshold

    engine = create_engine(str(settings.DATABASE_URL))
    Session = sessionmaker(bind=engine)
    session = Session()

    # Find moved trigpoints (condition='M') with WGS coordinates
    # Only GB grid (not Irish)
    query = text("""
        SELECT 
            id, waypoint, name,
            osgb_eastings, osgb_northings, osgb_height, osgb_gridref,
            wgs_lat, wgs_long, wgs_height
        FROM trig
        WHERE condition = 'M'
          AND wgs_lat IS NOT NULL
          AND wgs_long IS NOT NULL
          AND (original_grid_system = 'OS' OR original_grid_system IS NULL)
        ORDER BY id
    """)

    results = session.execute(query).fetchall()
    print(f"Checking {len(results)} moved trigpoints (condition='M')...")

    updates = []
    skipped_outside_grid = 0

    for row in results:
        trig_id = row.id
        stored_lat = float(row.wgs_lat)
        stored_lon = float(row.wgs_long)
        wgs_height = float(row.wgs_height) if row.wgs_height else None

        stored_eastings = float(row.osgb_eastings) if row.osgb_eastings else None
        stored_northings = float(row.osgb_northings) if row.osgb_northings else None

        try:
            # Convert WGS to OSGB using OSTN15
            new_eastings, new_northings, new_osgb_height = convert_wgs84_to_osgb(
                stored_lon, stored_lat, wgs_height
            )
        except Exception as e:
            logger.warning(f"Failed to convert {row.waypoint}: {e}")
            continue

        # Check if new coordinates are within GB grid bounds
        if (
            new_eastings < 0
            or new_eastings > 700000
            or new_northings < 0
            or new_northings > 1300000
        ):
            skipped_outside_grid += 1
            continue

        # Generate grid reference
        try:
            new_gridref = eastings_northings_to_gridref(new_eastings, new_northings)
        except ValueError:
            skipped_outside_grid += 1
            continue

        # Calculate distance between stored and calculated OSGB coordinates
        if stored_eastings is not None and stored_northings is not None:
            distance = calculate_osgb_distance_metres(
                stored_eastings, stored_northings, new_eastings, new_northings
            )
        else:
            # No existing OSGB coords - definitely needs update
            distance = float("inf")

        if distance > threshold_metres:
            updates.append({
                "id": trig_id,
                "waypoint": row.waypoint,
                "name": row.name,
                "old_eastings": stored_eastings,
                "old_northings": stored_northings,
                "old_gridref": row.osgb_gridref,
                "new_eastings": new_eastings,
                "new_northings": new_northings,
                "new_osgb_height": new_osgb_height,
                "new_gridref": new_gridref,
                "distance": distance if distance != float("inf") else None,
            })

    if skipped_outside_grid > 0:
        print(f"Skipped {skipped_outside_grid} trigpoints outside GB grid bounds")

    print(
        f"\nFound {len(updates)} moved trigpoints needing OSGB update "
        f"(>{threshold_metres}m discrepancy)"
    )

    if not updates:
        print("Nothing to update!")
        session.close()
        return

    # Apply limit if specified
    if args.limit and len(updates) > args.limit:
        print(f"Limiting to first {args.limit} updates")
        updates = updates[: args.limit]

    # Sort by distance descending to show largest discrepancies first
    # Put None distances (no existing coords) at the end
    updates.sort(key=lambda x: x["distance"] if x["distance"] is not None else -1, reverse=True)

    # Show summary
    print("\nTop 20 updates:")
    print("-" * 90)
    for u in updates[:20]:
        dist_str = f"{u['distance']:.2f}m" if u["distance"] is not None else "N/A"
        print(f"{u['waypoint']:8} {u['name'][:30]:30} {dist_str:>10}")
        if u["old_eastings"] is not None:
            print(f"         Old OSGB: {u['old_eastings']:.2f}, {u['old_northings']:.2f} ({u['old_gridref']})")
        else:
            print(f"         Old OSGB: None")
        print(f"         New OSGB: {u['new_eastings']:.2f}, {u['new_northings']:.2f} ({u['new_gridref']})")

    if len(updates) > 20:
        print(f"... and {len(updates) - 20} more")

    # Statistics (only for those with existing coords)
    distances = [u["distance"] for u in updates if u["distance"] is not None]
    if distances:
        print(f"\nStatistics (for {len(distances)} trigs with existing OSGB):")
        print(f"  Min discrepancy:  {min(distances):.2f}m")
        print(f"  Max discrepancy:  {max(distances):.2f}m")
        print(f"  Mean discrepancy: {sum(distances) / len(distances):.2f}m")

    no_existing = len([u for u in updates if u["distance"] is None])
    if no_existing:
        print(f"\n{no_existing} trigpoints have no existing OSGB coordinates")

    if dry_run:
        print("\n" + "=" * 80)
        print("*** DRY RUN - no changes made ***")
        print("Run with --apply to actually update the database")
        print("=" * 80)
    else:
        print("\nApplying updates...")
        updated_count = 0

        for u in updates:
            update_sql = text("""
                UPDATE trig 
                SET osgb_eastings = :eastings,
                    osgb_northings = :northings,
                    osgb_height = :height,
                    osgb_gridref = :gridref
                WHERE id = :id
            """)
            session.execute(
                update_sql,
                {
                    "id": u["id"],
                    "eastings": round(u["new_eastings"], 4),
                    "northings": round(u["new_northings"], 4),
                    "height": round(u["new_osgb_height"], 3) if u["new_osgb_height"] else None,
                    "gridref": u["new_gridref"],
                },
            )
            updated_count += 1

            if updated_count % 100 == 0:
                print(f"  Updated {updated_count}/{len(updates)}...")

        session.commit()
        print(f"\nSuccessfully updated {updated_count} moved trigpoints")
        logger.info(f"Updated {updated_count} moved trigpoint OSGB coordinates from WGS via OSTN15")

    session.close()


if __name__ == "__main__":
    main()

