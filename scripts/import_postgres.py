#!/usr/bin/env python3
"""
Import transformed data into PostgreSQL database.

This script imports CSV data exported from MySQL into PostgreSQL,
creating tables via SQLAlchemy models and handling PostGIS geography columns.

Usage:
    python scripts/import_postgres.py --input-dir /path/to/export

Environment variables required:
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (PostgreSQL)
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import List

import pandas as pd
from geoalchemy2.functions import ST_GeographyFromText
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import api modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.core.config import settings
from api.db.database import Base


class PostgreSQLImporter:
    """Import data into PostgreSQL database."""

    def __init__(self, input_dir: str):
        """Initialize importer with input directory."""
        self.input_dir = Path(input_dir)
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {input_dir}")
        
        # Connect to PostgreSQL
        self.engine = create_engine(settings.DATABASE_URL)
        self.Session = sessionmaker(bind=self.engine)
        
        print(f"Connected to PostgreSQL: {settings.DB_HOST}/{settings.DB_NAME}")
        print(f"Input directory: {self.input_dir}")

    def create_tables(self):
        """Create all tables from SQLAlchemy models."""
        print("\nCreating database tables...")
        Base.metadata.create_all(self.engine)
        print("✓ Tables created successfully")

    def import_table_from_csv(
        self,
        table_name: str,
        csv_file: Path,
        batch_size: int = 5000,
        progress_interval: int = 25000,
        geography_columns: List[str] = None,
    ):
        """
        Import data from CSV file into a table.
        
        Args:
            table_name: Name of the table to import into
            csv_file: Path to CSV file
            batch_size: Number of rows to insert at once
            progress_interval: How often to print progress
            geography_columns: List of columns containing WKT geography data
        """
        if not csv_file.exists():
            print(f"⚠️  {csv_file.name} not found, skipping")
            return
        
        geography_columns = geography_columns or []
        
        print(f"\nImporting {table_name}...")
        
        # Read CSV in chunks
        total_rows = sum(1 for _ in open(csv_file)) - 1  # -1 for header
        print(f"  Total rows to import: {total_rows:,}")
        
        if total_rows == 0:
            print(f"  ✓ No data to import")
            return
        
        rows_imported = 0
        
        with self.Session() as session:
            try:
                # Process in chunks
                for chunk in pd.read_csv(csv_file, chunksize=batch_size):
                    # Replace NaN with None for SQL NULL
                    chunk = chunk.where(pd.notna(chunk), None)
                    
                    # Convert WKT geography columns to PostGIS format
                    for col in geography_columns:
                        if col in chunk.columns:
                            # Replace WKT strings with SQL function calls
                            # This will be handled in the SQL statement
                            pass
                    
                    # Convert DataFrame to list of dicts
                    records = chunk.to_dict("records")
                    
                    # Prepare insert statement
                    if geography_columns and records:
                        # Use raw SQL for geography columns
                        columns = list(records[0].keys())
                        
                        # Build column list and values placeholders
                        col_list = ", ".join([f'"{c}"' for c in columns])
                        
                        # For geography columns, use ST_GeographyFromText
                        value_placeholders = []
                        for col in columns:
                            if col in geography_columns:
                                value_placeholders.append(f"ST_GeographyFromText(:{col})")
                            else:
                                value_placeholders.append(f":{col}")
                        
                        values_str = ", ".join(value_placeholders)
                        
                        insert_sql = f"""
                            INSERT INTO {table_name} ({col_list})
                            VALUES ({values_str})
                        """
                        
                        # Execute batch insert
                        for record in records:
                            session.execute(text(insert_sql), record)
                    else:
                        # Simple insert without geography columns
                        session.execute(
                            text(f"INSERT INTO {table_name} VALUES ({','.join([':' + k for k in records[0].keys()])})"),
                            records
                        )
                    
                    session.commit()
                    
                    rows_imported += len(chunk)
                    
                    # Print progress
                    if rows_imported % progress_interval == 0 or rows_imported >= total_rows:
                        pct = 100 * rows_imported / total_rows
                        print(f"  Progress: {rows_imported:,}/{total_rows:,} ({pct:.1f}%)")
                
                print(f"  ✓ Imported {rows_imported:,} rows")
                
            except Exception as e:
                session.rollback()
                print(f"  ❌ Error importing {table_name}: {e}")
                raise

    def import_reference_tables(self):
        """Import reference/lookup tables first."""
        print("\n" + "=" * 60)
        print("Importing Reference Tables")
        print("=" * 60)
        
        reference_tables = [
            "status",
            "county",
            "server",
            "attr",
            "attrsource",
        ]
        
        for table in reference_tables:
            csv_file = self.input_dir / f"{table}.csv"
            self.import_table_from_csv(table, csv_file)

    def import_core_tables(self):
        """Import core entity tables."""
        print("\n" + "=" * 60)
        print("Importing Core Tables")
        print("=" * 60)
        
        # Import user table
        self.import_table_from_csv(
            "user",
            self.input_dir / "user.csv",
            batch_size=2000,
        )
        
        # Import trig table with PostGIS location column
        trig_file = self.input_dir / "trig_transformed.csv"
        if trig_file.exists():
            self.import_table_from_csv(
                "trig",
                trig_file,
                batch_size=2000,
                geography_columns=["location"],
            )
        else:
            print("⚠️  trig_transformed.csv not found, trying trig.csv")
            self.import_table_from_csv(
                "trig",
                self.input_dir / "trig.csv",
                batch_size=2000,
            )

    def import_relationship_tables(self):
        """Import tables with foreign key relationships."""
        print("\n" + "=" * 60)
        print("Importing Relationship Tables")
        print("=" * 60)
        
        # Tables with foreign keys (import after parent tables)
        relationship_tables = [
            ("trigstats", 2000),
            ("tlog", 5000),
            ("tphoto", 5000),
            ("tphotovote", 5000),
            ("tphotoclass", 2000),
        ]
        
        for table, batch_size in relationship_tables:
            csv_file = self.input_dir / f"{table}.csv"
            self.import_table_from_csv(table, csv_file, batch_size=batch_size)

    def import_large_tables(self):
        """Import very large tables last."""
        print("\n" + "=" * 60)
        print("Importing Large Tables")
        print("=" * 60)
        
        large_tables = [
            ("tquery", 10000),
            ("attrval", 10000),
            ("attrset_attrval", 10000),
        ]
        
        for table, batch_size in large_tables:
            csv_file = self.input_dir / f"{table}.csv"
            self.import_table_from_csv(
                table,
                csv_file,
                batch_size=batch_size,
                progress_interval=100000,
            )

    def import_remaining_tables(self):
        """Import any remaining tables."""
        print("\n" + "=" * 60)
        print("Importing Remaining Tables")
        print("=" * 60)
        
        # Get list of all CSV files
        csv_files = list(self.input_dir.glob("*.csv"))
        imported_tables = {
            "status", "county", "server", "attr", "attrsource",
            "user", "trig", "trig_transformed",
            "trigstats", "tlog", "tphoto", "tphotovote", "tphotoclass",
            "tquery", "attrval", "attrset_attrval",
            "export_metadata",
        }
        
        for csv_file in csv_files:
            table = csv_file.stem
            if table not in imported_tables and not table.endswith("_transformed"):
                self.import_table_from_csv(table, csv_file, batch_size=5000)

    def create_spatial_indexes(self):
        """Create spatial indexes on geography columns."""
        print("\n" + "=" * 60)
        print("Creating Spatial Indexes")
        print("=" * 60)
        
        with self.Session() as session:
            try:
                # Create spatial index on trig.location
                print("\nCreating spatial index on trig.location...")
                session.execute(text("""
                    CREATE INDEX IF NOT EXISTS idx_trig_location
                    ON trig USING GIST (location)
                """))
                session.commit()
                print("  ✓ Created idx_trig_location")
                
            except Exception as e:
                print(f"  ⚠️  Error creating indexes: {e}")

    def analyze_tables(self):
        """Run ANALYZE on all tables to update statistics."""
        print("\n" + "=" * 60)
        print("Analyzing Tables (updating statistics)")
        print("=" * 60)
        
        with self.Session() as session:
            try:
                session.execute(text("ANALYZE"))
                session.commit()
                print("  ✓ Analysis complete")
            except Exception as e:
                print(f"  ⚠️  Error analyzing tables: {e}")

    def run(self):
        """Run the complete import process."""
        print("=" * 60)
        print("MySQL to PostgreSQL Migration - Data Import")
        print("=" * 60)
        
        self.create_tables()
        self.import_reference_tables()
        self.import_core_tables()
        self.import_relationship_tables()
        self.import_large_tables()
        self.import_remaining_tables()
        self.create_spatial_indexes()
        self.analyze_tables()
        
        print("\n" + "=" * 60)
        print("✅ Import Complete!")
        print("=" * 60)
        print("\nNext step: Run validate_migration.py to verify data integrity")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Import data into PostgreSQL")
    parser.add_argument(
        "--input-dir",
        default="./mysql_export",
        help="Input directory with CSV files (default: ./mysql_export)",
    )
    
    args = parser.parse_args()
    
    importer = PostgreSQLImporter(args.input_dir)
    importer.run()


if __name__ == "__main__":
    main()

