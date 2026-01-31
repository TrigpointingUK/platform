#!/usr/bin/env python3
"""
Update WGS84 coordinates from OSGB using OSTN15 transformation.

Finds trigpoints where the stored WGS coords disagree with OSTN15-converted
OSGB coords by more than a threshold, and updates them.

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
from api.services.coordinate_service import convert_osgb_to_wgs84

logger = get_logger(__name__)


def calculate_distance_metres(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Calculate approximate distance between two WGS84 points in metres.
    
    Uses simple Pythagorean approximation which is accurate enough for
    small distances (< 10km).
    """
    # 1 degree latitude ≈ 111km
    # 1 degree longitude ≈ 111km * cos(latitude)
    lat_diff_m = (lat2 - lat1) * 111000
    lon_diff_m = (lon2 - lon1) * 111000 * math.cos(math.radians(lat1))
    return math.sqrt(lat_diff_m**2 + lon_diff_m**2)


def main():
    parser = argparse.ArgumentParser(
        description="Update WGS84 coordinates from OSGB using OSTN15"
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

    # Find trigpoints with OSGB coordinates (GB grid only)
    # that have WGS coordinates to compare
    query = text("""
        SELECT 
            id, waypoint, name,
            osgb_eastings, osgb_northings, osgb_height,
            wgs_lat, wgs_long, wgs_height
        FROM trig
        WHERE osgb_eastings IS NOT NULL 
          AND osgb_northings IS NOT NULL
          AND wgs_lat IS NOT NULL
          AND wgs_long IS NOT NULL
          AND (original_grid_system = 'OS' OR original_grid_system IS NULL)
        ORDER BY id
    """)

    results = session.execute(query).fetchall()
    print(f"Checking {len(results)} trigpoints with OSGB coordinates...")

    updates = []
    skipped_outside_grid = 0

    for row in results:
        trig_id = row.id
        eastings = float(row.osgb_eastings)
        northings = float(row.osgb_northings)
        osgb_height = float(row.osgb_height) if row.osgb_height else None

        stored_lat = float(row.wgs_lat)
        stored_lon = float(row.wgs_long)

        # Skip coordinates outside GB grid bounds
        if eastings < 0 or eastings > 700000 or northings < 0 or northings > 1300000:
            skipped_outside_grid += 1
            continue

        try:
            # Convert OSGB to WGS using OSTN15
            new_lon, new_lat, new_height = convert_osgb_to_wgs84(
                eastings, northings, osgb_height
            )
        except Exception as e:
            logger.warning(f"Failed to convert {row.waypoint}: {e}")
            continue

        # Calculate distance between stored and calculated WGS coordinates
        distance = calculate_distance_metres(stored_lat, stored_lon, new_lat, new_lon)

        if distance > threshold_metres:
            updates.append({
                "id": trig_id,
                "waypoint": row.waypoint,
                "name": row.name,
                "old_lat": stored_lat,
                "old_lon": stored_lon,
                "old_height": float(row.wgs_height) if row.wgs_height else None,
                "new_lat": new_lat,
                "new_lon": new_lon,
                "new_height": new_height,
                "distance": distance,
            })

    if skipped_outside_grid > 0:
        print(f"Skipped {skipped_outside_grid} trigpoints outside GB grid bounds")

    print(
        f"\nFound {len(updates)} trigpoints needing update "
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
    updates.sort(key=lambda x: x["distance"], reverse=True)

    # Show summary
    print("\nTop 20 discrepancies:")
    print("-" * 80)
    for u in updates[:20]:
        print(f"{u['waypoint']:8} {u['name'][:30]:30} {u['distance']:8.2f}m")
        print(f"         Old: ({u['old_lat']:.8f}, {u['old_lon']:.8f})")
        print(f"         New: ({u['new_lat']:.8f}, {u['new_lon']:.8f})")

    if len(updates) > 20:
        print(f"... and {len(updates) - 20} more")

    # Statistics
    distances = [u["distance"] for u in updates]
    print(f"\nStatistics:")
    print(f"  Min discrepancy:  {min(distances):.2f}m")
    print(f"  Max discrepancy:  {max(distances):.2f}m")
    print(f"  Mean discrepancy: {sum(distances) / len(distances):.2f}m")

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
                SET wgs_lat = :lat,
                    wgs_long = :lon,
                    wgs_height = :height,
                    location = ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
                WHERE id = :id
            """)
            session.execute(
                update_sql,
                {
                    "id": u["id"],
                    "lat": round(u["new_lat"], 8),
                    "lon": round(u["new_lon"], 8),
                    "height": round(u["new_height"], 3) if u["new_height"] else None,
                },
            )
            updated_count += 1

            if updated_count % 100 == 0:
                print(f"  Updated {updated_count}/{len(updates)}...")

        session.commit()
        print(f"\nSuccessfully updated {updated_count} trigpoints")
        logger.info(f"Updated {updated_count} trigpoint WGS coordinates from OSGB via OSTN15")

    session.close()


if __name__ == "__main__":
    main()

