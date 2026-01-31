#!/usr/bin/env python3
"""
Populate trig.original_* columns from attrval OSGB data (IW source).

This script extracts the most recent OSGB coordinates from the attrval tables
(attr_id 4=eastings, 5=northings, 6=height, 9=date) and populates the
original_* columns in the trig table.

For each trig, if multiple attrsets exist, the one with the most recent date
is selected.

Uses OSTN15 to convert OSGB to WGS84 for the original_wgs_* columns.

Usage:
    # Dry run (default) - shows what would be updated
    python scripts/populate_original_osgb_from_attrval.py

    # Actually update
    python scripts/populate_original_osgb_from_attrval.py --execute

    # Connect to staging via tunnel on port 5433
    python scripts/populate_original_osgb_from_attrval.py --db-url "postgresql://user:pass@localhost:5433/dbname"

    # Process only specific trig IDs
    python scripts/populate_original_osgb_from_attrval.py --execute --trig-ids 4221,4222

    # Skip trigs that already have original_provenance='IW'
    python scripts/populate_original_osgb_from_attrval.py --execute --only-missing
"""

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


@dataclass
class AttrValData:
    """OSGB data extracted from attrval for a single attrset."""

    attrset_id: int
    eastings: Optional[float] = None
    northings: Optional[float] = None
    height: Optional[float] = None
    date: Optional[datetime] = None
    order: Optional[int] = None


def parse_date(date_str: str) -> Optional[datetime]:
    """
    Parse date from dd/mm/yyyy format.

    Args:
        date_str: Date string in dd/mm/yyyy format (may have quotes)

    Returns:
        Parsed datetime or None if invalid
    """
    if not date_str:
        return None

    # Remove surrounding quotes if present
    date_str = date_str.strip('"').strip("'").strip()

    if not date_str:
        return None

    try:
        # Parse dd/mm/yyyy format
        return datetime.strptime(date_str, "%d/%m/%Y")
    except ValueError:
        return None


def parse_float(value_str: str) -> Optional[float]:
    """
    Parse float from value_string.

    Args:
        value_str: Numeric string (may have quotes)

    Returns:
        Parsed float or None if invalid
    """
    if not value_str:
        return None

    # Remove surrounding quotes if present
    value_str = value_str.strip('"').strip("'").strip()

    if not value_str:
        return None

    try:
        return float(value_str)
    except ValueError:
        return None


def get_attrval_osgb_data(
    db: Session, trig_id: int, verbose: bool = False
) -> Optional[AttrValData]:
    """
    Get OSGB data from attrval for a trig, selecting the best attrset.

    Selection priority (when multiple attrsets exist):
    1. Most recent date
    2. Lowest order value (if dates match)
    3. Greatest height (if orders match)
    4. Highest attrset_id (if heights match - with warning message)

    Args:
        db: Database session
        trig_id: Trig ID to query
        verbose: Whether to print tie-breaker messages

    Returns:
        AttrValData with the best coordinates, or None if no data found
    """
    ATTR_ID_EASTINGS = 4
    ATTR_ID_NORTHINGS = 5
    ATTR_ID_HEIGHT = 6
    ATTR_ID_ORDER = 7
    ATTR_ID_DATE = 9

    # Query all relevant attrval rows for this trig
    result = db.execute(
        text("""
            SELECT s.id as attrset_id, av.attr_id, av.value_string
            FROM attrval av
            INNER JOIN attrset_attrval aa ON aa.attrval_id = av.id
            INNER JOIN attrset s ON aa.attrset_id = s.id
            WHERE s.trig_id = :trig_id
            AND av.attr_id IN (:attr_eastings, :attr_northings, :attr_height, :attr_order, :attr_date)
            ORDER BY s.id
        """),
        {
            "trig_id": trig_id,
            "attr_eastings": ATTR_ID_EASTINGS,
            "attr_northings": ATTR_ID_NORTHINGS,
            "attr_height": ATTR_ID_HEIGHT,
            "attr_order": ATTR_ID_ORDER,
            "attr_date": ATTR_ID_DATE,
        },
    ).fetchall()

    if not result:
        return None

    # Group by attrset_id
    attrsets: dict[int, AttrValData] = {}

    for row in result:
        attrset_id = row[0]
        attr_id = row[1]
        value_str = row[2]

        if attrset_id not in attrsets:
            attrsets[attrset_id] = AttrValData(attrset_id=attrset_id)

        data = attrsets[attrset_id]

        if attr_id == ATTR_ID_EASTINGS:
            data.eastings = parse_float(value_str)
        elif attr_id == ATTR_ID_NORTHINGS:
            data.northings = parse_float(value_str)
        elif attr_id == ATTR_ID_HEIGHT:
            data.height = parse_float(value_str)
        elif attr_id == ATTR_ID_ORDER:
            parsed = parse_float(value_str)
            data.order = int(parsed) if parsed is not None else None
        elif attr_id == ATTR_ID_DATE:
            data.date = parse_date(value_str)

    # Filter to attrsets that have at least eastings and northings
    valid_attrsets = [
        data
        for data in attrsets.values()
        if data.eastings is not None and data.northings is not None
    ]

    if not valid_attrsets:
        return None

    if len(valid_attrsets) == 1:
        return valid_attrsets[0]

    # Sort by priority:
    # 1. Most recent date (descending, None sorted last)
    # 2. Lowest order (ascending, None sorted last)
    # 3. Greatest height (descending, None sorted last)
    # 4. Highest attrset_id (descending) - handled after sort for ties
    def compare_attrsets(a: AttrValData, b: AttrValData) -> int:
        """Compare two attrsets. Returns negative if a < b, positive if a > b."""
        # 1. Compare dates (most recent first = descending)
        a_date = a.date if a.date else datetime.min
        b_date = b.date if b.date else datetime.min
        if a_date != b_date:
            return 1 if a_date > b_date else -1

        # 2. Compare order (lowest first = ascending)
        a_order = a.order if a.order is not None else float("inf")
        b_order = b.order if b.order is not None else float("inf")
        if a_order != b_order:
            return -1 if a_order < b_order else 1

        # 3. Compare height (greatest first = descending)
        a_height = a.height if a.height is not None else float("-inf")
        b_height = b.height if b.height is not None else float("-inf")
        if a_height != b_height:
            return 1 if a_height > b_height else -1

        # 4. All match - will use attrset_id as final tie-breaker
        return 0

    from functools import cmp_to_key

    valid_attrsets.sort(key=cmp_to_key(compare_attrsets), reverse=True)

    # Check if top candidates have identical date, order, and height
    best = valid_attrsets[0]
    best_date = best.date if best.date else datetime.min
    best_order = best.order if best.order is not None else float("inf")
    best_height = best.height if best.height is not None else float("-inf")

    # Find all attrsets that tie with the best on date/order/height
    tied_attrsets = [best]
    for candidate in valid_attrsets[1:]:
        c_date = candidate.date if candidate.date else datetime.min
        c_order = candidate.order if candidate.order is not None else float("inf")
        c_height = candidate.height if candidate.height is not None else float("-inf")

        if c_date == best_date and c_order == best_order and c_height == best_height:
            tied_attrsets.append(candidate)
        else:
            # Since sorted, no more ties possible
            break

    if len(tied_attrsets) > 1:
        # Multiple ties - choose highest attrset_id
        tied_ids = [a.attrset_id for a in tied_attrsets]
        best = max(tied_attrsets, key=lambda a: a.attrset_id)
        if verbose:
            print(
                f"    WARNING trig_id={trig_id}: {len(tied_attrsets)} attrsets with "
                f"identical date/order/height. Choosing attrset_id={best.attrset_id} "
                f"(highest of {sorted(tied_ids)})"
            )

    return best


def main():
    parser = argparse.ArgumentParser(
        description="Populate trig.original_* columns from attrval OSGB data"
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
        help="Only process trigs that don't have original_provenance='IW' yet",
    )
    parser.add_argument(
        "--trig-ids",
        type=str,
        help="Comma-separated list of trig IDs to process (default: all)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show details for each trig processed",
    )
    args = parser.parse_args()

    # Import coordinate service here to allow --help without full app init
    from api.services.coordinate_service import (
        convert_osgb_to_wgs84,
        eastings_northings_to_gridref,
    )

    if args.db_url:
        engine = create_engine(args.db_url)
    else:
        from api.db.database import get_engine

        engine = get_engine()

    with Session(engine) as db:
        # Get trig IDs to process
        if args.trig_ids:
            trig_ids = [int(x.strip()) for x in args.trig_ids.split(",")]
        elif args.only_missing:
            # Get trigs where original_provenance is not 'IW'
            result = db.execute(
                text("""
                    SELECT id FROM trig
                    WHERE original_provenance IS NULL OR original_provenance != 'IW'
                    ORDER BY id
                """)
            ).fetchall()
            trig_ids = [row[0] for row in result]
        else:
            # Get all trig IDs
            result = db.execute(text("SELECT id FROM trig ORDER BY id")).fetchall()
            trig_ids = [row[0] for row in result]

        total_trigs = len(trig_ids)

        print(f"\n=== Populate Original OSGB from AttrVal ===")
        print(f"Total trigs to process: {total_trigs}")
        print(f"Batch size: {args.batch_size}")
        print(f"Only missing: {args.only_missing}")
        print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")

        if not args.execute:
            print("\n*** DRY RUN - No changes will be made ***")
            print("Run with --execute to actually update trigs.")

        # Process in batches
        updated_count = 0
        skipped_count = 0
        no_data_count = 0
        error_count = 0
        start_time = time.time()

        for batch_start in range(0, total_trigs, args.batch_size):
            batch_end = min(batch_start + args.batch_size, total_trigs)
            batch = trig_ids[batch_start:batch_end]
            batch_num = batch_start // args.batch_size + 1
            total_batches = (total_trigs + args.batch_size - 1) // args.batch_size

            batch_updated = 0
            batch_skipped = 0
            batch_no_data = 0
            batch_errors = 0

            for trig_id in batch:
                try:
                    # Get attrval data
                    data = get_attrval_osgb_data(db, trig_id, verbose=args.verbose)

                    if data is None:
                        batch_no_data += 1
                        if args.verbose:
                            print(f"  trig_id={trig_id}: No attrval data found")
                        continue

                    # Convert to WGS84 using OSTN15
                    try:
                        wgs_lon, wgs_lat, wgs_height = convert_osgb_to_wgs84(
                            data.eastings, data.northings, data.height
                        )
                    except Exception as e:
                        batch_errors += 1
                        print(
                            f"  ERROR trig_id={trig_id}: OSTN15 conversion failed: {e}"
                        )
                        continue

                    # Generate grid reference
                    try:
                        gridref = eastings_northings_to_gridref(
                            data.eastings, data.northings
                        )
                    except ValueError as e:
                        batch_errors += 1
                        print(
                            f"  ERROR trig_id={trig_id}: Grid reference failed: {e}"
                        )
                        continue

                    if args.verbose:
                        height_str = f"{data.height:.3f}" if data.height else "None"
                        date_str = data.date.strftime("%Y-%m-%d") if data.date else "None"
                        print(
                            f"  trig_id={trig_id}: "
                            f"E={data.eastings:.2f} N={data.northings:.2f} "
                            f"H={height_str} "
                            f"Date={date_str} "
                            f"-> {gridref}"
                        )

                    if args.execute:
                        # Update trig with original data
                        db.execute(
                            text("""
                                UPDATE trig SET
                                    original_osgb_eastings = :eastings,
                                    original_osgb_northings = :northings,
                                    original_osgb_height = :osgb_height,
                                    original_osgb_gridref = :gridref,
                                    original_wgs_lat = :wgs_lat,
                                    original_wgs_long = :wgs_lon,
                                    original_wgs_height = :wgs_height,
                                    original_grid_system = 'gb',
                                    original_location = ST_SetSRID(
                                        ST_MakePoint(:wgs_lon, :wgs_lat), 4326
                                    )::geography,
                                    original_provenance = 'IW'
                                WHERE id = :trig_id
                            """),
                            {
                                "trig_id": trig_id,
                                "eastings": Decimal(str(round(data.eastings, 4))),
                                "northings": Decimal(str(round(data.northings, 4))),
                                "osgb_height": (
                                    Decimal(str(round(data.height, 4)))
                                    if data.height is not None
                                    else None
                                ),
                                "gridref": gridref,
                                "wgs_lat": Decimal(str(round(wgs_lat, 8))),
                                "wgs_lon": Decimal(str(round(wgs_lon, 8))),
                                "wgs_height": (
                                    Decimal(str(round(wgs_height, 4)))
                                    if wgs_height is not None
                                    else None
                                ),
                            },
                        )

                    batch_updated += 1

                except Exception as e:
                    batch_errors += 1
                    print(f"  ERROR trig_id={trig_id}: {e}")

            if args.execute and batch_updated > 0:
                db.commit()

            updated_count += batch_updated
            skipped_count += batch_skipped
            no_data_count += batch_no_data
            error_count += batch_errors

            elapsed = time.time() - start_time
            rate = (batch_end) / elapsed if elapsed > 0 else 0
            eta = (total_trigs - batch_end) / rate if rate > 0 else 0

            print(
                f"  Batch {batch_num}/{total_batches}: "
                f"updated {batch_updated}, no_data {batch_no_data}, errors {batch_errors}, "
                f"progress {batch_end}/{total_trigs} "
                f"({100 * batch_end / total_trigs:.1f}%) "
                f"[{rate:.1f}/s, ETA {eta:.0f}s]"
            )

        # Summary
        elapsed = time.time() - start_time
        print(f"\n=== Summary ===")
        print(f"Updated: {updated_count}")
        print(f"Skipped (no attrval data): {no_data_count}")
        print(f"Errors: {error_count}")
        print(f"Time: {elapsed:.1f}s")

        if not args.execute:
            print("\n*** DRY RUN - No changes were made ***")
            print("Run with --execute to actually update trigs.")


if __name__ == "__main__":
    main()

