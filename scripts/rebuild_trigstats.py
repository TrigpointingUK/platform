#!/usr/bin/env python3
"""
Rebuild trigstats for all trigpoints with logs.

This script recalculates statistics (logged_count, found_count, photo_count,
score_mean, score_baysian, etc.) for all trigpoints that have at least one log.

Processes in batches of 100 and commits after each batch to avoid timeouts.

Usage:
    # Dry run (default) - shows what would be updated
    python scripts/rebuild_trigstats.py

    # Actually update
    python scripts/rebuild_trigstats.py --execute

    # Connect to staging via tunnel on port 5433
    python scripts/rebuild_trigstats.py --db-url "postgresql://user:pass@localhost:5433/dbname"

    # Adjust batch size
    python scripts/rebuild_trigstats.py --execute --batch-size 50
"""

import argparse
import sys
import time
from decimal import Decimal
from pathlib import Path
from typing import Optional

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import case, create_engine, func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from api.crud.condition import get_found_condition_codes
from api.models.tphoto import TPhoto
from api.models.trig import Trig
from api.models.trigstats import TrigStats
from api.models.user import TLog

# Minimum votes for Bayesian calculation
BAYESIAN_MIN_VOTES = 1


def get_global_mean_score(db: Session) -> Decimal:
    """Calculate the global mean score across all logs."""
    result = (
        db.query(
            func.sum(TLog.score),
            func.count(TLog.score),
        )
        .filter(TLog.score.isnot(None))
        .first()
    )

    if result is None:
        return Decimal("0")

    total_score = result[0] if result[0] is not None else 0
    total_count = result[1] if result[1] is not None else 0

    if total_count == 0:
        return Decimal("0")

    return Decimal(str(total_score)) / Decimal(str(total_count))


def calculate_trigstats_for_trig(
    db: Session, trig_id: int, global_mean: Decimal, found_conditions: set[str]
) -> Optional[dict]:
    """
    Calculate trigstats values for a single trig without committing.

    Returns None if there are no logs for this trig.
    """
    # Use SQL aggregates for efficient calculation
    log_stats = (
        db.query(
            func.count(TLog.id).label("logged_count"),
            func.min(TLog.date).label("logged_first"),
            func.max(TLog.date).label("logged_last"),
            func.sum(TLog.score).label("total_score"),
            func.count(TLog.score).label("score_count"),
            # Found stats: count and last date for conditions with green/yellow log_colour
            func.count(
                case((TLog.condition.in_(found_conditions), TLog.id), else_=None)
            ).label("found_count"),
            func.max(
                case((TLog.condition.in_(found_conditions), TLog.date), else_=None)
            ).label("found_last"),
        )
        .filter(TLog.trig_id == trig_id)
        .first()
    )

    if log_stats is None:
        return None

    logged_count = log_stats.logged_count or 0

    if logged_count == 0:
        return None

    logged_first = log_stats.logged_first
    logged_last = log_stats.logged_last
    total_score = log_stats.total_score or 0
    score_count = log_stats.score_count or 0
    found_count = log_stats.found_count or 0
    found_last = log_stats.found_last

    # Query photo count
    photo_count = (
        db.query(func.count(TPhoto.id))
        .join(TLog, TPhoto.tlog_id == TLog.id)
        .filter(TLog.trig_id == trig_id, TPhoto.deleted_ind != "Y")
        .scalar()
        or 0
    )

    # Calculate mean score
    if score_count > 0:
        score_mean = Decimal(str(total_score)) / Decimal(str(score_count))
    else:
        score_mean = Decimal("0")

    # Calculate Bayesian weighted score
    wv = Decimal(str(logged_count))
    wm = Decimal(str(BAYESIAN_MIN_VOTES))
    wR = score_mean
    wC = global_mean

    if wv + wm > 0:
        score_baysian = (wv / (wv + wm)) * wR + (wm / (wv + wm)) * wC
    else:
        score_baysian = Decimal("0")

    return {
        "id": trig_id,
        "logged_first": logged_first,
        "logged_last": logged_last,
        "logged_count": logged_count,
        "found_last": found_last,
        "found_count": found_count,
        "photo_count": photo_count,
        "score_mean": round(score_mean, 2),
        "score_baysian": round(score_baysian, 2),
    }


def upsert_trigstats(db: Session, values: dict) -> None:
    """Insert or update a trigstats row (without committing)."""
    stmt = pg_insert(TrigStats).values(**values)

    stmt = stmt.on_conflict_do_update(
        index_elements=["id"],
        set_={
            "logged_first": stmt.excluded.logged_first,
            "logged_last": stmt.excluded.logged_last,
            "logged_count": stmt.excluded.logged_count,
            "found_last": stmt.excluded.found_last,
            "found_count": stmt.excluded.found_count,
            "photo_count": stmt.excluded.photo_count,
            "score_mean": stmt.excluded.score_mean,
            "score_baysian": stmt.excluded.score_baysian,
        },
    )

    db.execute(stmt)


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild trigstats for all trigpoints with logs"
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
    args = parser.parse_args()

    if args.db_url:
        engine = create_engine(args.db_url)
    else:
        from api.db.database import get_engine

        engine = get_engine()

    with Session(engine) as db:
        # Get count of trigs with logs
        trig_ids = (
            db.query(TLog.trig_id).distinct().filter(TLog.trig_id.isnot(None)).all()
        )
        trig_ids = [t[0] for t in trig_ids]
        total_trigs = len(trig_ids)

        print(f"\n=== Trigstats Rebuild ===")
        print(f"Total trigs with logs: {total_trigs}")
        print(f"Batch size: {args.batch_size}")
        print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")

        if not args.execute:
            print("\n*** DRY RUN - No changes will be made ***")
            print("Run with --execute to actually update trigstats.")

        # Calculate global mean once at the start
        print("\nCalculating global mean score...")
        global_mean = get_global_mean_score(db)
        print(f"Global mean score: {global_mean}")

        # Get "found" condition codes from condition table
        found_conditions = get_found_condition_codes(db)
        print(f"Found conditions (green/yellow log_colour): {sorted(found_conditions)}")

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
                    values = calculate_trigstats_for_trig(
                        db, int(trig_id), global_mean, found_conditions
                    )
                    if values is None:
                        skipped_count += 1
                        continue

                    if args.execute:
                        upsert_trigstats(db, values)

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
        print(f"Skipped (no logs): {skipped_count}")
        print(f"Errors: {error_count}")
        print(f"Time: {elapsed:.1f}s")

        if not args.execute:
            print("\n*** DRY RUN - No changes were made ***")
            print("Run with --execute to actually update trigstats.")


if __name__ == "__main__":
    main()
