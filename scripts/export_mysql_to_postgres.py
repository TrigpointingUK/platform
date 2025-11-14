#!/usr/bin/env python3
"""
Export data from MySQL database in preparation for PostgreSQL migration.

This script exports all tables from the MySQL database to CSV files,
handling large tables in batches and ensuring proper encoding.

Usage:
    python scripts/export_mysql_to_postgres.py --output-dir /path/to/export

Environment variables required:
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""

import argparse
import csv
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import api modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.core.config import settings


class MySQLExporter:
    """Export MySQL database to CSV files."""

    def __init__(self, output_dir: str):
        """Initialize exporter with output directory."""
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Connect to MySQL
        mysql_url = (
            f"mysql+pymysql://{settings.DB_USER}:{settings.DB_PASSWORD}"
            f"@{settings.DB_HOST}:{settings.DB_PORT}/{settings.DB_NAME}"
        )
        self.engine = create_engine(mysql_url)
        self.Session = sessionmaker(bind=self.engine)
        
        print(f"Connected to MySQL: {settings.DB_HOST}/{settings.DB_NAME}")
        print(f"Output directory: {self.output_dir}")

    def get_all_tables(self) -> List[str]:
        """Get list of all tables in the database."""
        inspector = inspect(self.engine)
        tables = inspector.get_table_names()
        return sorted(tables)

    def get_table_row_count(self, table_name: str) -> int:
        """Get row count for a table."""
        with self.Session() as session:
            result = session.execute(text(f"SELECT COUNT(*) FROM `{table_name}`"))
            return result.scalar() or 0

    def export_table(
        self,
        table_name: str,
        batch_size: int = 10000,
        progress_interval: int = 50000,
    ):
        """
        Export a single table to CSV.
        
        Args:
            table_name: Name of the table to export
            batch_size: Number of rows to fetch at a time
            progress_interval: How often to print progress updates
        """
        output_file = self.output_dir / f"{table_name}.csv"
        
        # Get total row count
        total_rows = self.get_table_row_count(table_name)
        print(f"\nExporting {table_name} ({total_rows:,} rows)...")
        
        if total_rows == 0:
            # Create empty CSV with headers
            with self.Session() as session:
                result = session.execute(text(f"SELECT * FROM `{table_name}` LIMIT 0"))
                df = pd.DataFrame(columns=result.keys())
                df.to_csv(output_file, index=False, encoding="utf-8")
            print(f"  ✓ Created empty CSV (no rows)")
            return
        
        # Export in batches
        rows_exported = 0
        first_batch = True
        
        with self.Session() as session:
            offset = 0
            while offset < total_rows:
                # Fetch batch
                query = text(
                    f"SELECT * FROM `{table_name}` LIMIT {batch_size} OFFSET {offset}"
                )
                result = session.execute(query)
                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                
                if df.empty:
                    break
                
                # Write to CSV (append mode after first batch)
                mode = "w" if first_batch else "a"
                header = first_batch
                df.to_csv(
                    output_file,
                    mode=mode,
                    header=header,
                    index=False,
                    encoding="utf-8",
                    quoting=csv.QUOTE_NONNUMERIC,
                )
                
                rows_exported += len(df)
                offset += batch_size
                first_batch = False
                
                # Print progress
                if rows_exported % progress_interval == 0 or rows_exported == total_rows:
                    pct = 100 * rows_exported / total_rows
                    print(
                        f"  Progress: {rows_exported:,}/{total_rows:,} ({pct:.1f}%)"
                    )
        
        print(f"  ✓ Exported {rows_exported:,} rows to {output_file.name}")

    def export_all_tables(self):
        """Export all tables to CSV files."""
        tables = self.get_all_tables()
        print(f"\nFound {len(tables)} tables to export")
        
        # Tables to export (in dependency order)
        priority_tables = [
            "status",
            "county",
            "town",
            "server",
            "user",
            "trig",
            "tlog",
            "tphoto",
            "trigstats",
        ]
        
        # Export priority tables first
        exported = set()
        for table in priority_tables:
            if table in tables:
                self.export_table(table)
                exported.add(table)
        
        # Export remaining tables
        for table in tables:
            if table not in exported:
                self.export_table(table)
        
        print(f"\n✅ Export complete! {len(tables)} tables exported.")
        print(f"Output directory: {self.output_dir}")

    def export_metadata(self):
        """Export metadata about the export."""
        metadata = {
            "export_date": datetime.utcnow().isoformat(),
            "source_host": settings.DB_HOST,
            "source_database": settings.DB_NAME,
            "tables_exported": len(self.get_all_tables()),
        }
        
        metadata_file = self.output_dir / "export_metadata.txt"
        with open(metadata_file, "w") as f:
            for key, value in metadata.items():
                f.write(f"{key}: {value}\n")
        
        print(f"\nMetadata written to {metadata_file}")


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Export MySQL database to CSV files")
    parser.add_argument(
        "--output-dir",
        default="./mysql_export",
        help="Output directory for CSV files (default: ./mysql_export)",
    )
    
    args = parser.parse_args()
    
    print("=" * 60)
    print("MySQL to PostgreSQL Migration - Data Export")
    print("=" * 60)
    
    exporter = MySQLExporter(args.output_dir)
    exporter.export_all_tables()
    exporter.export_metadata()
    
    print("\n" + "=" * 60)
    print("Next step: Run transform_coordinates_to_postgis.py")
    print("=" * 60)


if __name__ == "__main__":
    main()

