#!/usr/bin/env python3
"""
Import transformed CSV data into PostgreSQL database.

This script imports CSV files (transformed for PostGIS) into PostgreSQL,
handling:
- Table creation via SQLAlchemy models
- Batch imports for large tables
- PostGIS WKT to GEOGRAPHY conversion
- Foreign key dependency order
- Progress tracking

Usage:
    python scripts/import_postgres.py --input-dir /path/to/export

Environment variables required:
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (PostgreSQL)
"""

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import api modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.core.config import settings
from api.db.base import Base  # Import Base to get all models


class PostgreSQLImporter:
    """Import CSV data into PostgreSQL database."""

    def __init__(self, input_dir: str):
        """Initialize importer with input directory."""
        self.input_dir = Path(input_dir)

        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {self.input_dir}")

        # Connect to PostgreSQL
        pg_url = settings.DATABASE_URL
        if not pg_url.startswith("postgresql"):
            raise ValueError(
                f"DATABASE_URL must be PostgreSQL, got: {pg_url.split('://')[0]}"
            )

        self.engine = create_engine(pg_url)
        self.Session = sessionmaker(bind=self.engine)

        print(f"Connected to PostgreSQL: {settings.DB_HOST}/{settings.DB_NAME}")
        print(f"Input directory: {self.input_dir}")

    def create_tables(self):
        """Create all tables using SQLAlchemy models."""
        print("\nCreating database schema...")

        # Drop existing tables if they exist (for clean import)
        inspector = inspect(self.engine)
        existing_tables = inspector.get_table_names()

        if existing_tables:
            print(f"  Found {len(existing_tables)} existing tables")
            response = input("  Drop existing tables and recreate? (yes/N): ")
            if response.lower() == "yes":
                print("  Dropping existing tables...")
                Base.metadata.drop_all(bind=self.engine)
                print("  ✓ Tables dropped")

        # Create all tables
        print("  Creating tables from models...")
        Base.metadata.create_all(bind=self.engine)

        # Verify tables created
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        print(f"  ✓ Created {len(tables)} tables")

    def get_csv_files(self) -> List[Path]:
        """Get list of CSV files in dependency order."""
        # Tables in dependency order (reference tables first)
        priority_order = [
            "status",
            "county",
            "town",
            "server",
            "user",
            "trig",
            "tlog",
            "tphoto",
            "place",
            "postcode6",
        ]

        csv_files = []
        found_files = set()

        # Add priority files first
        for table_name in priority_order:
            csv_file = self.input_dir / f"{table_name}.csv"
            if csv_file.exists():
                csv_files.append(csv_file)
                found_files.add(table_name)

        # Add remaining files
        for csv_file in sorted(self.input_dir.glob("*.csv")):
            table_name = csv_file.stem
            if table_name not in found_files:
                csv_files.append(csv_file)

        return csv_files

    def get_row_count(self, csv_file: Path) -> int:
        """Get row count from CSV file."""
        with open(csv_file, "r", encoding="utf-8") as f:
            return sum(1 for _ in f) - 1  # Subtract header row

    def import_csv(
        self,
        csv_file: Path,
        batch_size: int = 5000,
        progress_interval: int = 25000,
    ):
        """
        Import a single CSV file to PostgreSQL.

        Args:
            csv_file: Path to CSV file
            batch_size: Number of rows to insert per batch
            progress_interval: How often to print progress updates
        """
        table_name = csv_file.stem
        total_rows = self.get_row_count(csv_file)

        print(f"\nImporting {table_name} ({total_rows:,} rows)...")

        if total_rows == 0:
            print("  ✓ Skipped (no rows)")
            return

        # Read CSV and prepare data
        rows_imported = 0
        batch = []

        with open(csv_file, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            columns = reader.fieldnames

            if not columns:
                print(f"  ✗ No columns found in {csv_file}")
                return

            # Build INSERT statement
            placeholders = ", ".join([f":{col}" for col in columns])
            insert_sql = (
                f"INSERT INTO {table_name} ({', '.join(columns)}) "
                f"VALUES ({placeholders})"
            )

            # Handle PostGIS location column conversion
            if "location" in columns:
                # Remove location from placeholders, add ST_GeogFromText
                cols_without_location = [c for c in columns if c != "location"]
                placeholders = ", ".join([f":{col}" for col in cols_without_location])
                placeholders += ", ST_GeogFromText(:location)"

                cols_str = ", ".join(cols_without_location) + ", location"
                insert_sql = (
                    f"INSERT INTO {table_name} ({cols_str}) " f"VALUES ({placeholders})"
                )

            with self.Session() as session:
                for row in reader:
                    # Convert empty strings to None for proper NULL handling
                    cleaned_row = {}
                    for key, value in row.items():
                        if value == "":
                            cleaned_row[key] = None
                        elif value == "NULL":
                            cleaned_row[key] = None
                        else:
                            cleaned_row[key] = value

                    batch.append(cleaned_row)

                    # Execute batch when full
                    if len(batch) >= batch_size:
                        try:
                            session.execute(text(insert_sql), batch)
                            session.commit()
                            rows_imported += len(batch)
                            batch = []

                            # Print progress
                            if rows_imported % progress_interval == 0:
                                pct = 100 * rows_imported / total_rows
                                print(
                                    f"  Progress: {rows_imported:,}/{total_rows:,} ({pct:.1f}%)"
                                )
                        except Exception as e:
                            session.rollback()
                            print(f"  ✗ Error inserting batch: {e}")
                            # Print first row of failed batch for debugging
                            if batch:
                                print(f"  First row: {batch[0]}")
                            raise

                # Insert remaining rows
                if batch:
                    try:
                        session.execute(text(insert_sql), batch)
                        session.commit()
                        rows_imported += len(batch)
                    except Exception as e:
                        session.rollback()
                        print(f"  ✗ Error inserting final batch: {e}")
                        if batch:
                            print(f"  First row: {batch[0]}")
                        raise

        print(f"  ✓ Imported {rows_imported:,} rows")

    def create_spatial_indexes(self):
        """Create spatial indexes on PostGIS columns."""
        print("\nCreating spatial indexes...")

        spatial_indexes = [
            ("trig", "location"),
            ("place", "location"),
            ("town", "location"),
            ("postcode6", "location"),
        ]

        with self.Session() as session:
            for table_name, column_name in spatial_indexes:
                try:
                    # Check if table exists
                    result = session.execute(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.tables "
                            f"WHERE table_name = '{table_name}')"
                        )
                    )
                    if not result.scalar():
                        continue

                    # Check if column exists
                    result = session.execute(
                        text(
                            "SELECT EXISTS (SELECT 1 FROM information_schema.columns "
                            f"WHERE table_name = '{table_name}' AND column_name = '{column_name}')"
                        )
                    )
                    if not result.scalar():
                        continue

                    # Create spatial index
                    index_name = f"idx_{table_name}_{column_name}_gist"
                    session.execute(
                        text(
                            f"CREATE INDEX IF NOT EXISTS {index_name} "
                            f"ON {table_name} USING GIST ({column_name})"
                        )
                    )
                    session.commit()
                    print(f"  ✓ Created index: {index_name}")
                except Exception as e:
                    session.rollback()
                    print(f"  ✗ Error creating index on {table_name}.{column_name}: {e}")

    def run_vacuum_analyze(self):
        """Run VACUUM ANALYZE to optimize database."""
        print("\nRunning VACUUM ANALYZE...")

        # VACUUM cannot run inside a transaction
        with self.engine.connect().execution_options(
            isolation_level="AUTOCOMMIT"
        ) as conn:
            conn.execute(text("VACUUM ANALYZE"))

        print("  ✓ VACUUM ANALYZE completed")

    def import_all(self):
        """Import all CSV files."""
        print("\n" + "=" * 60)
        print("PostgreSQL Import Process")
        print("=" * 60)

        # Create tables
        self.create_tables()

        # Get CSV files
        csv_files = self.get_csv_files()
        print(f"\nFound {len(csv_files)} CSV files to import")

        # Import each file
        start_time = datetime.now()

        for csv_file in csv_files:
            try:
                self.import_csv(csv_file)
            except Exception as e:
                print(f"\n✗ Failed to import {csv_file.name}: {e}")
                print("\nImport aborted. You may need to:")
                print("  1. Fix the data or schema issue")
                print("  2. Drop and recreate the database")
                print("  3. Re-run the import")
                return False

        # Create spatial indexes
        try:
            self.create_spatial_indexes()
        except Exception as e:
            print(f"\n⚠ Warning: Failed to create spatial indexes: {e}")

        # Run VACUUM ANALYZE
        try:
            self.run_vacuum_analyze()
        except Exception as e:
            print(f"\n⚠ Warning: Failed to run VACUUM ANALYZE: {e}")

        # Summary
        elapsed = datetime.now() - start_time
        print("\n" + "=" * 60)
        print("✅ Import completed successfully!")
        print("=" * 60)
        print(f"Elapsed time: {elapsed}")
        print()

        return True


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Import CSV data to PostgreSQL database"
    )
    parser.add_argument(
        "--input-dir",
        type=str,
        default="mysql_export",
        help="Directory containing CSV files (default: mysql_export)",
    )

    args = parser.parse_args()

    try:
        importer = PostgreSQLImporter(args.input_dir)
        success = importer.import_all()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
