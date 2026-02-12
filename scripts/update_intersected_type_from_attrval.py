#!/usr/bin/env python3
"""
Update intersected station trig.type_id from attrval TYPE OF MARK data.

This script finds trigs with trig_type.code='INTERSECTED_STATION' and updates their
type_id based on the TYPE OF MARK value (attr_id=8) from the attrval tables.

For each trig, if multiple attrsets exist, the one with the best priority is selected:
1. Most recent date
2. Lowest order value (if dates match)
3. Greatest height (if orders match)
4. Highest attrset_id (if heights match)

The TYPE OF MARK value is matched against trig_type.legacy_physical_type for types
in the INTERSECTED category.

Usage:
    # Dry run (default) - shows what would be updated
    python scripts/update_intersected_type_from_attrval.py

    # Actually update
    python scripts/update_intersected_type_from_attrval.py --execute

    # Connect to staging via tunnel on port 5433
    python scripts/update_intersected_type_from_attrval.py --db-url "postgresql://user:pass@localhost:5433/dbname"

    # Process only specific trig IDs
    python scripts/update_intersected_type_from_attrval.py --execute --trig-ids 4221,4222

    # Skip trigs that have already been processed (type is no longer INTERSECTED_STATION)
    python scripts/update_intersected_type_from_attrval.py --execute --only-generic
"""

import argparse
import sys
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


@dataclass
class AttrValData:
    """Data extracted from attrval for a single attrset."""

    attrset_id: int
    type_of_mark: Optional[str] = None
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


def get_attrval_type_of_mark(
    db: Session, trig_id: int, verbose: bool = False
) -> Optional[AttrValData]:
    """
    Get TYPE OF MARK data from attrval for a trig, selecting the best attrset.

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
        AttrValData with the best TYPE OF MARK value, or None if no data found
    """
    ATTR_ID_EASTINGS = 4
    ATTR_ID_NORTHINGS = 5
    ATTR_ID_HEIGHT = 6
    ATTR_ID_ORDER = 7
    ATTR_ID_TYPE_OF_MARK = 8
    ATTR_ID_DATE = 9

    # Query all relevant attrval rows for this trig
    result = db.execute(
        text("""
            SELECT s.id as attrset_id, av.attr_id, av.value_string
            FROM attrval av
            INNER JOIN attrset_attrval aa ON aa.attrval_id = av.id
            INNER JOIN attrset s ON aa.attrset_id = s.id
            WHERE s.trig_id = :trig_id
            AND av.attr_id IN (:attr_eastings, :attr_northings, :attr_height, :attr_order, :attr_type_of_mark, :attr_date)
            ORDER BY s.id
        """),
        {
            "trig_id": trig_id,
            "attr_eastings": ATTR_ID_EASTINGS,
            "attr_northings": ATTR_ID_NORTHINGS,
            "attr_height": ATTR_ID_HEIGHT,
            "attr_order": ATTR_ID_ORDER,
            "attr_type_of_mark": ATTR_ID_TYPE_OF_MARK,
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
        elif attr_id == ATTR_ID_TYPE_OF_MARK:
            # Store the TYPE OF MARK value, stripping quotes
            if value_str:
                data.type_of_mark = value_str.strip('"').strip("'").strip()
        elif attr_id == ATTR_ID_DATE:
            data.date = parse_date(value_str)

    # Filter to attrsets that have a TYPE OF MARK value
    valid_attrsets = [
        data for data in attrsets.values() if data.type_of_mark is not None
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
        """Compare two attrsets. Returns negative if a should come first."""
        # 1. Compare dates (most recent first = descending)
        a_date = a.date if a.date else datetime.min
        b_date = b.date if b.date else datetime.min
        if a_date != b_date:
            # More recent date should come first (negative return)
            return -1 if a_date > b_date else 1

        # 2. Compare order (lowest first = ascending)
        a_order = a.order if a.order is not None else float("inf")
        b_order = b.order if b.order is not None else float("inf")
        if a_order != b_order:
            # Lower order should come first (negative return)
            return -1 if a_order < b_order else 1

        # 3. Compare height (greatest first = descending)
        a_height = a.height if a.height is not None else float("-inf")
        b_height = b.height if b.height is not None else float("-inf")
        if a_height != b_height:
            # Greater height should come first (negative return)
            return -1 if a_height > b_height else 1

        # 4. All match - will use attrset_id as final tie-breaker
        return 0

    from functools import cmp_to_key

    valid_attrsets.sort(key=cmp_to_key(compare_attrsets))

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
        description="Update intersected station trig.type_id from attrval TYPE OF MARK"
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
        "--only-generic",
        action="store_true",
        help="Only process trigs that still have type_id=INTERSECTED_STATION",
    )
    parser.add_argument(
        "--trig-ids",
        type=str,
        help="Comma-separated list of trig IDs to process (default: all INTERSECTED_STATION)",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Show details for each trig processed",
    )
    args = parser.parse_args()

    if args.db_url:
        engine = create_engine(args.db_url)
    else:
        from api.db.database import get_engine

        engine = get_engine()

    with Session(engine) as db:
        # First, get the INTERSECTED category ID and build a mapping of
        # legacy_physical_type -> trig_type.id for INTERSECTED types
        print("\n=== Loading INTERSECTED trig types ===")
        result = db.execute(text("""
                SELECT tt.id, tt.code, tt.legacy_physical_type
                FROM trig_type tt
                INNER JOIN trig_category tc ON tt.category_id = tc.id
                WHERE tc.code = 'INTERSECTED'
            """)).fetchall()

        # Build mapping: legacy_physical_type (uppercase) -> (trig_type_id, code)
        type_mapping: dict[str, tuple[int, str]] = {}
        intersected_station_type_id = None
        for row in result:
            type_id, code, legacy_physical_type = row
            if legacy_physical_type:
                type_mapping[legacy_physical_type.upper()] = (type_id, code)
            if code == "INTERSECTED_STATION":
                intersected_station_type_id = type_id

        if intersected_station_type_id is None:
            print("ERROR: Could not find INTERSECTED_STATION type in database")
            sys.exit(1)

        print(f"Found {len(type_mapping)} INTERSECTED type mappings")
        print(f"INTERSECTED_STATION type_id = {intersected_station_type_id}")

        # Get trig IDs to process
        if args.trig_ids:
            trig_ids = [int(x.strip()) for x in args.trig_ids.split(",")]
        elif args.only_generic:
            # Get trigs where type_id is INTERSECTED_STATION
            result = db.execute(
                text("""
                    SELECT id FROM trig
                    WHERE type_id = :intersected_station_type_id
                    ORDER BY id
                """),
                {"intersected_station_type_id": intersected_station_type_id},
            ).fetchall()
            trig_ids = [row[0] for row in result]
        else:
            # Get all trigs with type_id = INTERSECTED_STATION
            result = db.execute(
                text("""
                    SELECT id FROM trig
                    WHERE type_id = :intersected_station_type_id
                    ORDER BY id
                """),
                {"intersected_station_type_id": intersected_station_type_id},
            ).fetchall()
            trig_ids = [row[0] for row in result]

        total_trigs = len(trig_ids)

        print(f"\n=== Update Intersected Type from AttrVal ===")
        print(f"Total trigs to process: {total_trigs}")
        print(f"Batch size: {args.batch_size}")
        print(f"Only generic: {args.only_generic}")
        print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")

        if not args.execute:
            print("\n*** DRY RUN - No changes will be made ***")
            print("Run with --execute to actually update trigs.")

        # Counters for different outcomes
        updated_count = 0
        no_data_count = 0
        no_match_count = 0
        error_count = 0

        # Track TYPE OF MARK values that didn't match
        unmatched_types: dict[str, int] = {}

        start_time = time.time()

        for batch_start in range(0, total_trigs, args.batch_size):
            batch_end = min(batch_start + args.batch_size, total_trigs)
            batch = trig_ids[batch_start:batch_end]
            batch_num = batch_start // args.batch_size + 1
            total_batches = (total_trigs + args.batch_size - 1) // args.batch_size

            batch_updated = 0
            batch_no_data = 0
            batch_no_match = 0
            batch_errors = 0

            for trig_id in batch:
                try:
                    # Get attrval data
                    data = get_attrval_type_of_mark(db, trig_id, verbose=args.verbose)

                    if data is None or data.type_of_mark is None:
                        batch_no_data += 1
                        if args.verbose:
                            print(f"  trig_id={trig_id}: No TYPE OF MARK data found")
                        continue

                    type_of_mark = data.type_of_mark.upper()

                    # Look up the matching trig_type
                    if type_of_mark not in type_mapping:
                        batch_no_match += 1
                        unmatched_types[data.type_of_mark] = (
                            unmatched_types.get(data.type_of_mark, 0) + 1
                        )
                        if args.verbose:
                            print(
                                f"  trig_id={trig_id}: TYPE OF MARK '{data.type_of_mark}' "
                                f"not found in INTERSECTED types"
                            )
                        continue

                    new_type_id, new_type_code = type_mapping[type_of_mark]

                    # Don't update if it would be the same type
                    if new_type_id == intersected_station_type_id:
                        if args.verbose:
                            print(
                                f"  trig_id={trig_id}: TYPE OF MARK '{data.type_of_mark}' "
                                f"maps to INTERSECTED_STATION (no change needed)"
                            )
                        batch_no_match += 1
                        continue

                    if args.verbose:
                        date_str = (
                            data.date.strftime("%Y-%m-%d") if data.date else "None"
                        )
                        print(
                            f"  trig_id={trig_id}: TYPE OF MARK='{data.type_of_mark}' "
                            f"(date={date_str}, order={data.order}, "
                            f"attrset={data.attrset_id}) -> {new_type_code} (id={new_type_id})"
                        )

                    if args.execute:
                        # Update trig with new type_id
                        db.execute(
                            text("""
                                UPDATE trig SET type_id = :new_type_id
                                WHERE id = :trig_id
                            """),
                            {
                                "trig_id": trig_id,
                                "new_type_id": new_type_id,
                            },
                        )

                    batch_updated += 1

                except Exception as e:
                    batch_errors += 1
                    print(f"  ERROR trig_id={trig_id}: {e}")

            if args.execute and batch_updated > 0:
                db.commit()

            updated_count += batch_updated
            no_data_count += batch_no_data
            no_match_count += batch_no_match
            error_count += batch_errors

            elapsed = time.time() - start_time
            rate = (batch_end) / elapsed if elapsed > 0 else 0
            eta = (total_trigs - batch_end) / rate if rate > 0 else 0

            print(
                f"  Batch {batch_num}/{total_batches}: "
                f"updated {batch_updated}, no_data {batch_no_data}, "
                f"no_match {batch_no_match}, errors {batch_errors}, "
                f"progress {batch_end}/{total_trigs} "
                f"({100 * batch_end / total_trigs:.1f}%) "
                f"[{rate:.1f}/s, ETA {eta:.0f}s]"
            )

        # Summary
        elapsed = time.time() - start_time
        print(f"\n=== Summary ===")
        print(f"Updated: {updated_count}")
        print(f"No attrval data: {no_data_count}")
        print(f"No match (kept as INTERSECTED_STATION): {no_match_count}")
        print(f"Errors: {error_count}")
        print(f"Time: {elapsed:.1f}s")

        if unmatched_types:
            print(f"\n=== Unmatched TYPE OF MARK values ===")
            for type_val, count in sorted(unmatched_types.items(), key=lambda x: -x[1]):
                print(f"  '{type_val}': {count} trigs")

        if not args.execute:
            print("\n*** DRY RUN - No changes were made ***")
            print("Run with --execute to actually update trigs.")


if __name__ == "__main__":
    main()
