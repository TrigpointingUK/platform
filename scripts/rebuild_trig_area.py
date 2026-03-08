#!/usr/bin/env python3
"""
Rebuild trig_area rows by calling refresh_area_trigs() per area.

Each area is processed in its own transaction, avoiding the need for a
single long-running transaction that locks the table for over an hour.

Supports three modes:
    Full rebuild     - all areas
    By area type     - all areas of a given area_type_id
    Single area      - one area by area.id

Usage:
    # Dry run (default) - shows what would be rebuilt
    python scripts/rebuild_trig_area.py

    # Full rebuild
    python scripts/rebuild_trig_area.py --execute

    # Rebuild a single area type (e.g. county_1991 = 7)
    python scripts/rebuild_trig_area.py --execute --area-type-id 7

    # Rebuild a single area
    python scripts/rebuild_trig_area.py --execute --area-id 439

    # Connect to staging via tunnel on port 5433
    python scripts/rebuild_trig_area.py --execute \\
        --db-url "postgresql://user:pass@localhost:5433/dbname"

    # Run 4 areas concurrently
    python scripts/rebuild_trig_area.py --execute --workers 4
"""

import argparse
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session


def _engine_from_env():
    """Build an engine from DB_* environment variables if present."""
    db_host = os.environ.get("DB_HOST")
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")
    db_name = os.environ.get("DB_NAME")

    if not all([db_host, db_user, db_password, db_name]):
        return None

    db_port = os.environ.get("DB_PORT", "5432")
    encoded_user = quote_plus(db_user)
    encoded_password = quote_plus(db_password)
    sslmode = "require" if db_host != "localhost" else "prefer"
    url = (
        f"postgresql+psycopg2://{encoded_user}:{encoded_password}"
        f"@{db_host}:{db_port}/{db_name}?sslmode={sslmode}"
    )
    return create_engine(url)


def get_area_ids(
    db: Session, area_type_id: int | None, area_id: int | None
) -> list[tuple[int, str]]:
    """Return list of (area_id, area_name) tuples to rebuild."""
    if area_id is not None:
        row = db.execute(
            text("SELECT id, name FROM area WHERE id = :id"),
            {"id": area_id},
        ).first()
        if row is None:
            print(f"ERROR: area.id = {area_id} not found")
            sys.exit(1)
        return [(row[0], row[1])]

    if area_type_id is not None:
        rows = db.execute(
            text(
                "SELECT a.id, a.name FROM area a "
                "WHERE a.area_type_id = :atid ORDER BY a.id"
            ),
            {"atid": area_type_id},
        ).fetchall()
        if not rows:
            print(f"ERROR: no areas found for area_type_id = {area_type_id}")
            sys.exit(1)
        return [(r[0], r[1]) for r in rows]

    rows = db.execute(text("SELECT a.id, a.name FROM area a ORDER BY a.id")).fetchall()
    return [(r[0], r[1]) for r in rows]


def rebuild_one_area(engine, area_id: int) -> int:
    """
    Rebuild trig_area for a single area in its own transaction.

    Returns the number of rows inserted.
    """
    with Session(engine) as db:
        db.execute(text("SELECT refresh_area_trigs(:aid)"), {"aid": area_id})
        row_count = db.execute(
            text("SELECT count(*) FROM trig_area WHERE area_id = :aid"),
            {"aid": area_id},
        ).scalar()
        db.commit()
    return row_count or 0


def main():
    parser = argparse.ArgumentParser(
        description="Rebuild trig_area by calling refresh_area_trigs() per area"
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually perform the rebuild (default is dry-run)",
    )
    parser.add_argument(
        "--area-id",
        type=int,
        help="Rebuild a single area by area.id",
    )
    parser.add_argument(
        "--area-type-id",
        type=int,
        help="Rebuild all areas of a given area_type_id",
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=1,
        help="Number of concurrent workers (default: 1)",
    )
    parser.add_argument(
        "--db-url",
        type=str,
        help="Database URL (default: uses get_engine() from app config)",
    )
    args = parser.parse_args()

    if args.area_id is not None and args.area_type_id is not None:
        print("ERROR: --area-id and --area-type-id are mutually exclusive")
        sys.exit(1)

    if args.db_url:
        engine = create_engine(args.db_url)
    else:
        engine = _engine_from_env()
        if engine is None:
            from api.db.database import get_engine

            engine = get_engine()

    with Session(engine) as db:
        areas = get_area_ids(db, args.area_type_id, args.area_id)

    scope = "all areas"
    if args.area_id is not None:
        scope = f"area.id = {args.area_id}"
    elif args.area_type_id is not None:
        scope = f"area_type_id = {args.area_type_id}"

    print(f"\n=== trig_area Rebuild ===")
    print(f"Scope: {scope}")
    print(f"Areas to process: {len(areas)}")
    print(f"Workers: {args.workers}")
    print(f"Mode: {'EXECUTE' if args.execute else 'DRY RUN'}")

    if not args.execute:
        print("\n*** DRY RUN - No changes will be made ***")
        print("Run with --execute to actually rebuild trig_area.\n")
        for aid, name in areas:
            print(f"  Would rebuild area {aid}: {name}")
        return

    total = len(areas)
    completed = 0
    total_rows = 0
    error_count = 0
    start_time = time.time()

    def process_area(area_tuple):
        aid, name = area_tuple
        try:
            rows = rebuild_one_area(engine, aid)
            return aid, name, rows, None
        except Exception as e:
            return aid, name, 0, str(e)

    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(process_area, a): a for a in areas}

        for future in as_completed(futures):
            aid, name, rows, error = future.result()
            completed += 1

            if error:
                error_count += 1
                print(f"  ERROR area {aid} ({name}): {error}")
            else:
                total_rows += rows
                elapsed = time.time() - start_time
                rate = completed / elapsed if elapsed > 0 else 0
                remaining = total - completed
                eta = remaining / rate if rate > 0 else 0
                print(
                    f"  Area {aid:>5} ({name}): {rows} trigs  "
                    f"[{completed}/{total} "
                    f"({100 * completed / total:.1f}%) "
                    f"{rate:.1f}/s, ETA {eta:.0f}s]"
                )

    elapsed = time.time() - start_time
    print(f"\n=== Summary ===")
    print(f"Areas processed: {completed}")
    print(f"Total trig_area rows: {total_rows}")
    print(f"Errors: {error_count}")
    print(f"Time: {elapsed:.1f}s")


if __name__ == "__main__":
    main()
