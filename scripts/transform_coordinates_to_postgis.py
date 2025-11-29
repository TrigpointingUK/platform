#!/usr/bin/env python3
"""
Transform coordinate data in preparation for PostGIS import.

This script reads exported CSV files, validates and transforms coordinate data
to WKT (Well-Known Text) format for PostGIS GEOGRAPHY columns.

Usage:
    python scripts/transform_coordinates_to_postgis.py --input-dir /path/to/export

This processes:
- trig table: wgs_lat/wgs_long → location (GEOGRAPHY)
- tlog table: coordinates if present
- Other tables with spatial data
"""

import argparse
import csv
import sys
from pathlib import Path
from typing import Optional

import pandas as pd

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))


class CoordinateTransformer:
    """Transform coordinates to PostGIS-compatible WKT format."""

    def __init__(self, input_dir: str):
        """Initialize transformer with input directory."""
        self.input_dir = Path(input_dir)
        if not self.input_dir.exists():
            raise ValueError(f"Input directory does not exist: {input_dir}")
        
        print(f"Input directory: {self.input_dir}")

    @staticmethod
    def create_point_wkt(lon: float, lat: float) -> Optional[str]:
        """
        Create WKT POINT from lon/lat coordinates.
        
        Args:
            lon: Longitude (WGS84)
            lat: Latitude (WGS84)
            
        Returns:
            WKT string like "POINT(lon lat)" or None if invalid
        """
        # Validate coordinates
        if pd.isna(lon) or pd.isna(lat):
            return None
        
        try:
            lon_f = float(lon)
            lat_f = float(lat)
            
            # Basic validation (WGS84 bounds)
            if not (-180 <= lon_f <= 180):
                print(f"  ⚠️  Invalid longitude: {lon_f}")
                return None
            if not (-90 <= lat_f <= 90):
                print(f"  ⚠️  Invalid latitude: {lat_f}")
                return None
            
            # Return WKT format
            return f"POINT({lon_f} {lat_f})"
        except (ValueError, TypeError) as e:
            print(f"  ⚠️  Error converting coordinates: {e}")
            return None

    def transform_trig_table(self):
        """Transform trig table coordinates to PostGIS WKT format."""
        input_file = self.input_dir / "trig.csv"
        if not input_file.exists():
            print(f"⚠️  trig.csv not found, skipping")
            return
        
        print("\nTransforming trig table...")
        
        # Read CSV
        df = pd.read_csv(input_file)
        initial_count = len(df)
        print(f"  Loaded {initial_count:,} rows")
        
        # Create location column from wgs_long and wgs_lat
        df["location"] = df.apply(
            lambda row: self.create_point_wkt(row["wgs_long"], row["wgs_lat"]),
            axis=1,
        )
        
        # Count valid locations
        valid_count = df["location"].notna().sum()
        print(f"  Created {valid_count:,} valid PostGIS points")
        
        if valid_count < initial_count:
            invalid_count = initial_count - valid_count
            print(f"  ⚠️  {invalid_count} rows have invalid coordinates")
        
        # Save transformed data
        output_file = self.input_dir / "trig_transformed.csv"
        df.to_csv(output_file, index=False, encoding="utf-8", quoting=csv.QUOTE_NONNUMERIC)
        print(f"  ✓ Saved to {output_file.name}")

    def transform_tlog_table(self):
        """Transform tlog table if it has coordinates."""
        input_file = self.input_dir / "tlog.csv"
        if not input_file.exists():
            print(f"⚠️  tlog.csv not found, skipping")
            return
        
        print("\nTransforming tlog table...")
        
        # Read CSV
        df = pd.read_csv(input_file)
        print(f"  Loaded {len(df):,} rows")
        
        # TLog doesn't have lat/lon, only OSGB coordinates
        # We'll leave it as-is for now
        print(f"  ✓ No transformation needed (OSGB coordinates only)")

    def transform_location_tables(self):
        """Transform other location tables (place, town, etc.)."""
        location_tables = ["place", "town", "postcode6"]
        
        for table_name in location_tables:
            input_file = self.input_dir / f"{table_name}.csv"
            if not input_file.exists():
                continue
            
            print(f"\nTransforming {table_name} table...")
            
            df = pd.read_csv(input_file)
            initial_count = len(df)
            print(f"  Loaded {initial_count:,} rows")
            
            # Check if table has wgs_lat and wgs_long columns
            if "wgs_lat" in df.columns and "wgs_long" in df.columns:
                df["location"] = df.apply(
                    lambda row: self.create_point_wkt(row["wgs_long"], row["wgs_lat"]),
                    axis=1,
                )
                
                valid_count = df["location"].notna().sum()
                print(f"  Created {valid_count:,} valid PostGIS points")
                
                # Save transformed data
                output_file = self.input_dir / f"{table_name}_transformed.csv"
                df.to_csv(
                    output_file, index=False, encoding="utf-8", quoting=csv.QUOTE_NONNUMERIC
                )
                print(f"  ✓ Saved to {output_file.name}")
            else:
                print(f"  ✓ No coordinate columns found, skipping")

    def validate_coordinates(self):
        """Validate that coordinate transformation was successful."""
        print("\n" + "=" * 60)
        print("Validation Summary")
        print("=" * 60)
        
        # Check trig table
        trig_file = self.input_dir / "trig_transformed.csv"
        if trig_file.exists():
            df = pd.read_csv(trig_file)
            total = len(df)
            valid = df["location"].notna().sum()
            invalid = total - valid
            
            print(f"\nTrig table:")
            print(f"  Total rows: {total:,}")
            print(f"  Valid PostGIS points: {valid:,} ({100 * valid / total:.1f}%)")
            if invalid > 0:
                print(f"  ⚠️  Invalid coordinates: {invalid:,} ({100 * invalid / total:.1f}%)")
        
        print("\n✅ Transformation complete!")
        print(f"Transformed files saved in: {self.input_dir}")

    def run(self):
        """Run all transformations."""
        print("=" * 60)
        print("MySQL to PostgreSQL Migration - Coordinate Transformation")
        print("=" * 60)
        
        self.transform_trig_table()
        self.transform_tlog_table()
        self.transform_location_tables()
        self.validate_coordinates()
        
        print("\n" + "=" * 60)
        print("Next step: Run import_postgres.py")
        print("=" * 60)


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="Transform coordinates for PostGIS import"
    )
    parser.add_argument(
        "--input-dir",
        default="./mysql_export",
        help="Input directory with exported CSV files (default: ./mysql_export)",
    )
    
    args = parser.parse_args()
    
    transformer = CoordinateTransformer(args.input_dir)
    transformer.run()


if __name__ == "__main__":
    main()

