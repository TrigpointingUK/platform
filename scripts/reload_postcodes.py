#!/usr/bin/env python3
"""
Reload the postcodes table with filtered NSPL data.

This script:
1. Sets all trig.postcode values to NULL (to satisfy FK constraint)
2. Deletes all existing postcodes
3. Loads only active postcodes from the NSPL CSV (DOTERM blank, USRTYPIND = 0)

Filters:
- DOTERM: Must be blank (postcode has not been terminated)
- USRTYPIND: Must be 0 (small user - standard postcode, not large user like businesses)

Usage:
    python scripts/reload_postcodes.py [csv_path]

Default CSV path: res/NSPL_Online_latest_Centroids_.csv

Requirements:
    - Database connection via environment variables (DB_HOST, DB_PORT, etc.)
    - Or run with SSM tunnel active (make postgres-tunnel)
"""

import csv
import sys
from decimal import Decimal
from pathlib import Path

# Add api directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text  # noqa: E402

from api.db.database import get_session_local  # noqa: E402


def reload_postcodes(csv_path: Path, batch_size: int = 5000) -> None:
    """
    Reload the postcodes table with filtered NSPL data.

    Args:
        csv_path: Path to the NSPL CSV file
        batch_size: Number of rows to insert per batch
    """
    SessionLocal = get_session_local()
    db = SessionLocal()

    try:
        print(f"Reading from: {csv_path}")
        print(f"Batch size: {batch_size:,}")
        print()

        # Step 1: Set all trig.postcode to NULL
        print("Step 1: Setting all trig.postcode values to NULL...")
        result = db.execute(
            text("UPDATE trig SET postcode = NULL WHERE postcode IS NOT NULL")
        )
        db.commit()
        print(f"  Updated {result.rowcount:,} trig records")

        # Step 2: Truncate all existing postcodes (much faster than DELETE for large tables)
        print("\nStep 2: Truncating postcodes table...")
        # TRUNCATE is much faster than DELETE for large tables
        # CASCADE handles any remaining FK references (though we already nullified trig.postcode)
        db.execute(text("TRUNCATE TABLE postcodes CASCADE"))
        db.commit()
        print("  Truncated postcodes table")

        # Step 3: Read CSV and insert filtered postcodes
        print("\nStep 3: Loading filtered postcodes from CSV...")
        print("  Filters: DOTERM = '' (blank) AND USRTYPIND = 0")

        with open(csv_path, "r", encoding="utf-8") as csv_file:
            reader = csv.DictReader(csv_file)

            batch = []
            total_rows = 0
            skipped_terminated = 0
            skipped_large_user = 0
            skipped_missing_data = 0

            for row in reader:
                try:
                    # Filter: DOTERM must be blank (not terminated)
                    doterm = row.get("DOTERM", "").strip()
                    if doterm:
                        skipped_terminated += 1
                        continue

                    # Filter: USRTYPIND must be 0 (small user)
                    usrtypind = row.get("USRTYPIND", "").strip()
                    if usrtypind != "0":
                        skipped_large_user += 1
                        continue

                    # Extract required fields
                    code = row["PCDS"].strip()
                    lat = row["LAT"].strip()
                    long_val = row["LONG"].strip()

                    # Skip rows with missing data
                    if not code or not lat or not long_val:
                        skipped_missing_data += 1
                        continue

                    # Add to batch
                    batch.append(
                        {
                            "code": code,
                            "lat": Decimal(lat),
                            "long": Decimal(long_val),
                        }
                    )
                    total_rows += 1

                    # Insert batch when it reaches batch_size
                    if len(batch) >= batch_size:
                        db.execute(
                            text(
                                """
                                INSERT INTO postcodes (code, lat, long)
                                VALUES (:code, :lat, :long)
                                """
                            ),
                            batch,
                        )
                        db.commit()
                        batch = []

                        # Progress indicator
                        if total_rows % 100000 == 0:
                            print(f"  Inserted {total_rows:,} rows...")

                except KeyError as e:
                    print(f"  Warning: Missing column {e}")
                    skipped_missing_data += 1
                    continue
                except Exception as e:
                    print(f"  Warning: Error processing row: {e}")
                    skipped_missing_data += 1
                    continue

            # Insert any remaining rows
            if batch:
                db.execute(
                    text(
                        """
                        INSERT INTO postcodes (code, lat, long)
                        VALUES (:code, :lat, :long)
                        """
                    ),
                    batch,
                )
                db.commit()

        # Print summary
        print("\n" + "=" * 60)
        print("RELOAD COMPLETE")
        print("=" * 60)
        print(f"  Total postcodes loaded:     {total_rows:,}")
        print(f"  Skipped (terminated):       {skipped_terminated:,}")
        print(f"  Skipped (large user):       {skipped_large_user:,}")
        print(f"  Skipped (missing data):     {skipped_missing_data:,}")
        print()

        # Verify count in database
        result = db.execute(text("SELECT COUNT(*) FROM postcodes"))
        db_count = result.scalar()
        print(f"  Postcodes in database:      {db_count:,}")

    except Exception as e:
        db.rollback()
        print(f"\n✗ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
    finally:
        db.close()


def main():
    """Main entry point."""
    # Determine project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Default CSV path
    default_csv = project_root / "res" / "NSPL_Online_latest_Centroids_.csv"

    # Parse command line arguments
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = default_csv

    # Check if input file exists
    if not csv_path.exists():
        print(f"Error: Input file not found: {csv_path}")
        print()
        print("Usage: python scripts/reload_postcodes.py [csv_path]")
        print()
        print("Download the NSPL CSV from:")
        print(
            "  https://geoportal.statistics.gov.uk/datasets/national-statistics-postcode-lookup-latest-centroids"
        )
        sys.exit(1)

    # Reload postcodes
    reload_postcodes(csv_path)


if __name__ == "__main__":
    main()
