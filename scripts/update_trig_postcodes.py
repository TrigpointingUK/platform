#!/usr/bin/env python3
"""
Batch update trig.postcode values from nearest postcode in postcodes table.

For each trig record:
- Find nearest postcode using PostGIS KNN spatial query
- If distance <= 5000m (5km): set trig.postcode = postcodes.code
- If distance > 5000m: set trig.postcode = NULL

Usage:
    python scripts/update_trig_postcodes.py
"""

import sys
from pathlib import Path

# Add api directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.crud import location as location_crud  # noqa: E402
from api.db.database import get_session_local  # noqa: E402
from api.models.trig import Trig  # noqa: E402

# Maximum distance in metres to assign a postcode (5km)
MAX_DISTANCE_M = 5000.0


def update_trig_postcodes():
    """Update all trig postcodes based on nearest postcode using PostGIS."""
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        # Get all trigs
        trigs = db.query(Trig).all()
        total = len(trigs)
        print(f"Found {total:,} trig records to process.\n")

        # Process each trig
        updated_count = 0
        set_null_count = 0

        for i, trig in enumerate(trigs, 1):
            result = location_crud.find_nearest_postcode(
                db, float(trig.wgs_lat), float(trig.wgs_long), max_distance_m=MAX_DISTANCE_M
            )

            if result:
                postcode_code, distance = result
                trig.postcode = postcode_code
                updated_count += 1
            else:
                # No postcodes found within max distance
                trig.postcode = None
                set_null_count += 1

            # Commit every 100 rows
            if i % 100 == 0:
                db.commit()
                print(
                    f"Progress: {i:,}/{total:,} ({100 * i / total:.1f}%) - "
                    f"Updated: {updated_count:,}, Set NULL: {set_null_count:,}"
                )

        # Final commit
        db.commit()

        print("\n✓ Update complete!")
        print(f"  Total processed: {total:,}")
        print(f"  Updated with postcode: {updated_count:,}")
        print(f"  Set to NULL (>{MAX_DISTANCE_M/1000:.0f}km): {set_null_count:,}")

    except Exception as e:
        db.rollback()
        print(f"✗ Error: {e}")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    update_trig_postcodes()
