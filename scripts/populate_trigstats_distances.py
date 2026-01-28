#!/usr/bin/env python3
"""
Populate trigstats distance columns for all trigpoints.

This script calculates and populates the dist_wgs_osgb and dist_osgb_osgb
columns in the trigstats table for all trigpoints. It can be run as a
one-off migration or incrementally.

Usage:
    # Dry run (default) - shows what would be updated
    python scripts/populate_trigstats_distances.py

    # Actually update
    python scripts/populate_trigstats_distances.py --execute

    # Connect to staging via tunnel on port 5433
    python scripts/populate_trigstats_distances.py --db-url "postgresql://user:pass@localhost:5433/dbname"

    # Only process trigs without existing distance values
    python scripts/populate_trigstats_distances.py --execute --only-missing

    # Adjust batch size
    python scripts/populate_trigstats_distances.py --execute --batch-size 50
"""

import argparse
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Optional, Tuple

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.models.trig import Trig
from api.models.trigstats import TrigStats


def get_attrval_osgb_coords(db: Session, trig_id: int) -> Optional[Tuple[float, float]]:
    """Get OSGB coordinates from attrval table for a trigpoint."""
    ATTR_ID_EASTINGS = 4
    ATTR_ID_NORTHINGS = 5

    result = db.execute(
        text("""
            SELECT av.attr_id, av.value_double
            FROM attrval av
            INNER JOIN attrset_attrval aa ON aa.attrval_id = av.id
            INNER JOIN attrset s ON aa.attrset_id = s.id
            WHERE s.trig_id = :trig_id
            AND av.attr_id IN (:attr_eastings, :attr_northings)
            """),
        {
            "trig_id": trig_id,
            "attr_eastings": ATTR_ID_EASTINGS,
            "attr_northings": ATTR_ID_NORTHINGS,
        },
    ).fetchall()

    if not result or len(result) < 2:
        return None

    eastings = None
    northings = None

    for row in result:
        attr_id = row[0]
        value = row[1]
        if value is None:
            continue
        try:
            coord_value = float(value)
            if attr_id == ATTR_ID_EASTINGS:
                eastings = coord_value
            elif attr_id == ATTR_ID_NORTHINGS:
                northings = coord_value
        except (ValueError, TypeError):
            continue

    if eastings is None or northings is None:
        return None

    return (eastings, northings)


def calculate_distances(
    db: Session, trig: Trig
) -> Tuple[Optional[Decimal], Optional[Decimal]]:
    """Calculate coordinate distances for a trigpoint."""
    import math

    dist_wgs_osgb: Optional[Decimal] = None
    dist_osgb_osgb: Optional[Decimal] = None

    # Get stored OSGB coords from trig table
    try:
        trig_eastings = float(trig.osgb_eastings)
        trig_northings = float(trig.osgb_northings)
    except (ValueError, TypeError):
        return (None, None)

    # Check if Irish grid
    gridref = str(trig.osgb_gridref) if trig.osgb_gridref else ""
    is_irish_grid = gridref and gridref[0] in ("I", "J")

    # Calculate dist_wgs_osgb
    if not is_irish_grid:
        try:
            from api.services.coordinate_service import convert_wgs84_to_osgb

            wgs_lat = float(trig.wgs_lat)
            wgs_lon = float(trig.wgs_long)

            transformed_e, transformed_n, _ = convert_wgs84_to_osgb(wgs_lon, wgs_lat)

            distance = math.sqrt(
                (transformed_e - trig_eastings) ** 2
                + (transformed_n - trig_northings) ** 2
            )
            dist_wgs_osgb = Decimal(str(round(distance, 4)))

        except Exception:
            pass

    # Calculate dist_osgb_osgb
    attrval_coords = get_attrval_osgb_coords(db, int(trig.id))
    if attrval_coords:
        attr_eastings, attr_northings = attrval_coords
        try:
            distance = math.sqrt(
                (trig_eastings - attr_eastings) ** 2
                + (trig_northings - attr_northings) ** 2
            )
            dist_osgb_osgb = Decimal(str(round(distance, 4)))
        except Exception:
            pass

    return (dist_wgs_osgb, dist_osgb_osgb)


def main():
    parser = argparse.ArgumentParser(
        description="Populate trigstats distance columns for all trigpoints"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the update (default is dry-run)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Number of trigs to process per batch/commit (default: 100)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Database URL (default: uses get_engine() from app config)",
    )
    parser.add_argument(
        "--only-missing",
        action="store_true",
        help="Only process trigs that don't have distance values yet",
    )
    args = parser.parse_args()

    if args.db_url:
        engine = create_engine(args.db_url)
    else:
        from api.db.database import get_engine

        engine = get_engine()

    with Session(engine) as db:
        # Get all trig IDs
        if args.only_missing:
            # Only get trigs where distances are NULL
            trig_ids = (
                db.query(Trig.id)
                .outerjoin(TrigStats, Trig.id == TrigStats.id)
                .filter(
                    (TrigStats.dist_wgs_osgb.is_(None))
                    | (TrigStats.dist_osgb_osgb.is_(None))
                    | (TrigStats.id.is_(None))
                )
                .all()
            )
        else:
            trig_ids = db.query(Trig.id).all()

        trig_ids = [t[0] for t in trig_ids]
        total_trigs = len(trig_ids)

        print(f"\n=== Trigstats Distance Population ===")
        print(f"Total trigs to process: {total_trigs}")
        print(f"Batch size: {args.batch_size}")
        print(f"Only missing: {args.only_missing}")
        print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")

        if not args.execute:
            print("\n*** DRY RUN - No changes will be made ***")
            print("Run with --execute to actually update trigstats.")

        # Process in batches
        updated_count = 0
        skipped_count = 0
        error_count = 0
        start_time = time.time()

        for batch_start in range(0, total_trigs, args.batch_size):
            batch_end = min(batch_start + args.batch_size, total_trigs)
            batch = trig_ids[batch_start:batch_end]
            batch_num = batch_start // args.batch_size + 1
            total_batches = (total_trigs + args.batch_size - 1) // args.batch_size

            batch_updated = 0
            batch_errors = 0

            for trig_id in batch:
                try:
                    trig = db.query(Trig).filter(Trig.id == trig_id).first()
                    if not trig:
                        skipped_count += 1
                        continue

                    dist_wgs_osgb, dist_osgb_osgb = calculate_distances(db, trig)

                    if args.execute:
                        # Upsert trigstats with distances
                        stmt = pg_insert(TrigStats).values(
                            id=trig_id,
                            logged_first=None,
                            logged_last=None,
                            logged_count=0,
                            found_last=None,
                            found_count=0,
                            photo_count=0,
                            score_mean=Decimal("0"),
                            score_baysian=Decimal("0"),
                            dist_wgs_osgb=dist_wgs_osgb,
                            dist_osgb_osgb=dist_osgb_osgb,
                        )
                        stmt = stmt.on_conflict_do_update(
                            index_elements=["id"],
                            set_={
                                "dist_wgs_osgb": stmt.excluded.dist_wgs_osgb,
                                "dist_osgb_osgb": stmt.excluded.dist_osgb_osgb,
                            },
                        )
                        db.execute(stmt)

                    batch_updated += 1

                except Exception as e:
                    batch_errors += 1
                    print(f"  ERROR trig_id={trig_id}: {e}")

            if args.execute and batch_updated > 0:
                db.commit()

            updated_count += batch_updated
            error_count += batch_errors

            elapsed = time.time() - start_time
            rate = updated_count / elapsed if elapsed > 0 else 0
            eta = (total_trigs - batch_end) / rate if rate > 0 else 0

            print(
                f"  Batch {batch_num}/{total_batches}: "
                f"processed {batch_updated}, errors {batch_errors}, "
                f"total {updated_count}/{total_trigs} "
                f"({100 * batch_end / total_trigs:.1f}%) "
                f"[{rate:.1f}/s, ETA {eta:.0f}s]"
            )

        # Summary
        elapsed = time.time() - start_time
        print(f"\n=== Summary ===")
        print(f"Updated: {updated_count}")
        print(f"Skipped: {skipped_count}")
        print(f"Errors: {error_count}")
        print(f"Time: {elapsed:.1f}s")

        if not args.execute:
            print("\n*** DRY RUN - No changes were made ***")
            print("Run with --execute to actually update trigstats.")


if __name__ == "__main__":
    main()
