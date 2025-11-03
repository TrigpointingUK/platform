#!/usr/bin/env python3
"""
Convert NSPL UK Postcode CSV to SQL for importing into postcodes table.

This script reads the NSPL (National Statistics Postcode Lookup) CSV file
and generates SQL statements to:
1. Drop any existing postcodes table
2. Create a new postcodes table with code, lat, long columns
3. Insert all postcode data from the CSV

Usage:
    python scripts/convert_postcodes_to_sql.py [input_csv] [output_sql]

Default paths:
    input: res/NSPL_Online_latest_Centroids_.csv
    output: init-db/postcodes.sql
"""

import csv
import sys
from pathlib import Path
from typing import TextIO


def write_table_creation(f: TextIO) -> None:
    """Write SQL to drop old table and create new postcodes table."""
    sql = """-- Drop postcodes table if it exists
DROP TABLE IF EXISTS postcodes;

-- Create new postcodes table
CREATE TABLE postcodes (
    code VARCHAR(10) NOT NULL,
    lat DECIMAL(10, 7) NOT NULL,
    `long` DECIMAL(11, 7) NOT NULL,
    PRIMARY KEY (code),
    INDEX idx_code_prefix (code(4))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert postcode data
"""
    f.write(sql)


def escape_sql_string(value: str) -> str:
    """Escape a string for SQL insertion."""
    return value.replace("\\", "\\\\").replace("'", "\\'")


def write_inserts_batch(
    f: TextIO, batch: list[tuple[str, str, str]], batch_size: int = 1000
) -> None:
    """Write a batch of INSERT statements."""
    if not batch:
        return

    f.write("INSERT INTO postcodes (code, lat, `long`) VALUES\n")

    for i, (code, lat, long) in enumerate(batch):
        # Escape values for SQL
        code_escaped = escape_sql_string(code)
        lat_escaped = escape_sql_string(lat)
        long_escaped = escape_sql_string(long)

        # Write value tuple
        f.write(f"  ('{code_escaped}', {lat_escaped}, {long_escaped})")

        # Add comma or semicolon
        if i < len(batch) - 1:
            f.write(",\n")
        else:
            f.write(";\n\n")


def convert_csv_to_sql(csv_path: Path, sql_path: Path, batch_size: int = 1000) -> None:
    """
    Convert the NSPL CSV file to SQL.

    Args:
        csv_path: Path to the input CSV file
        sql_path: Path to the output SQL file
        batch_size: Number of rows per INSERT statement
    """
    print(f"Reading from: {csv_path}")
    print(f"Writing to: {sql_path}")

    # Ensure output directory exists
    sql_path.parent.mkdir(parents=True, exist_ok=True)

    with open(csv_path, "r", encoding="utf-8") as csv_file, open(
        sql_path, "w", encoding="utf-8"
    ) as sql_file:

        # Write table creation SQL
        write_table_creation(sql_file)

        # Read CSV and write INSERT statements
        reader = csv.DictReader(csv_file)
        batch = []
        total_rows = 0
        skipped_rows = 0

        for row in reader:
            try:
                code = row["PCDS"].strip()
                lat = row["LAT"].strip()
                long = row["LONG"].strip()

                # Skip rows with missing data
                if not code or not lat or not long:
                    skipped_rows += 1
                    continue

                batch.append((code, lat, long))
                total_rows += 1

                # Write batch when it reaches batch_size
                if len(batch) >= batch_size:
                    write_inserts_batch(sql_file, batch, batch_size)
                    batch = []

                    # Progress indicator
                    if total_rows % 10000 == 0:
                        print(f"Processed {total_rows:,} rows...")

            except KeyError as e:
                print(
                    f"Warning: Missing column {e} in row {total_rows + skipped_rows + 1}"
                )
                skipped_rows += 1
                continue
            except Exception as e:
                print(
                    f"Warning: Error processing row {total_rows + skipped_rows + 1}: {e}"
                )
                skipped_rows += 1
                continue

        # Write any remaining rows in the final batch
        if batch:
            write_inserts_batch(sql_file, batch, batch_size)

        print(f"\nConversion complete!")
        print(f"Total rows processed: {total_rows:,}")
        print(f"Rows skipped: {skipped_rows:,}")
        print(f"Output written to: {sql_path}")


def main():
    """Main entry point."""
    # Determine project root (parent of scripts directory)
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Default paths
    default_csv = project_root / "res" / "NSPL_Online_latest_Centroids_.csv"
    default_sql = project_root / "init-db" / "postcodes.sql"

    # Parse command line arguments
    if len(sys.argv) > 1:
        csv_path = Path(sys.argv[1])
    else:
        csv_path = default_csv

    if len(sys.argv) > 2:
        sql_path = Path(sys.argv[2])
    else:
        sql_path = default_sql

    # Check if input file exists
    if not csv_path.exists():
        print(f"Error: Input file not found: {csv_path}")
        sys.exit(1)

    # Convert CSV to SQL
    try:
        convert_csv_to_sql(csv_path, sql_path)
    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
