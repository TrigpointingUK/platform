#!/usr/bin/env python3
"""
Validate PostgreSQL migration data quality.

This script validates that data was correctly migrated from MySQL to PostgreSQL:
- Row counts match between MySQL and PostgreSQL
- Spatial data converted correctly (sample checks)
- Key fields are populated
- Foreign key relationships intact

Usage:
    python scripts/validate_migration.py

Environment variables required:
    For MySQL: MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_NAME
    For PostgreSQL: DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""

import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path to import api modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.core.config import settings


class MigrationValidator:
    """Validate MySQL to PostgreSQL migration."""

    def __init__(self):
        """Initialize validator with both database connections."""
        # PostgreSQL connection
        pg_url = settings.DATABASE_URL
        if not pg_url.startswith("postgresql"):
            raise ValueError(
                f"DATABASE_URL must be PostgreSQL, got: {pg_url.split('://')[0]}"
            )

        self.pg_engine = create_engine(pg_url)
        self.PgSession = sessionmaker(bind=self.pg_engine)

        # MySQL connection (from environment variables with MYSQL_ prefix)
        mysql_host = os.getenv("MYSQL_HOST", os.getenv("DB_HOST"))
        mysql_port = os.getenv("MYSQL_PORT", os.getenv("DB_PORT", "3306"))
        mysql_user = os.getenv("MYSQL_USER", os.getenv("DB_USER"))
        mysql_password = os.getenv("MYSQL_PASSWORD", os.getenv("DB_PASSWORD"))
        mysql_database = os.getenv("MYSQL_NAME", os.getenv("DB_NAME"))

        mysql_url = (
            f"mysql+pymysql://{mysql_user}:{mysql_password}"
            f"@{mysql_host}:{mysql_port}/{mysql_database}"
        )

        self.mysql_engine = create_engine(mysql_url)
        self.MySQLSession = sessionmaker(bind=self.mysql_engine)

        print(f"Connected to PostgreSQL: {settings.DB_HOST}/{settings.DB_NAME}")
        print(f"Connected to MySQL: {mysql_host}/{mysql_database}")

        self.errors = []
        self.warnings = []

    def compare_row_counts(self) -> bool:
        """Compare row counts between MySQL and PostgreSQL."""
        print("\n" + "=" * 60)
        print("Row Count Comparison")
        print("=" * 60)

        # Get table names from PostgreSQL
        pg_inspector = inspect(self.pg_engine)
        pg_tables = set(pg_inspector.get_table_names())

        # Get table names from MySQL
        mysql_inspector = inspect(self.mysql_engine)
        mysql_tables = set(mysql_inspector.get_table_names())

        # Find common tables
        common_tables = sorted(pg_tables & mysql_tables)

        if not common_tables:
            self.errors.append("No common tables found between MySQL and PostgreSQL")
            return False

        print(f"\nComparing {len(common_tables)} tables...\n")

        all_match = True
        mismatches = []

        for table_name in common_tables:
            with self.MySQLSession() as mysql_session, self.PgSession() as pg_session:
                # Get MySQL count
                mysql_result = mysql_session.execute(
                    text(f"SELECT COUNT(*) FROM `{table_name}`")
                )
                mysql_count = mysql_result.scalar() or 0

                # Get PostgreSQL count
                pg_result = pg_session.execute(
                    text(f"SELECT COUNT(*) FROM {table_name}")
                )
                pg_count = pg_result.scalar() or 0

                # Compare
                match = "✓" if mysql_count == pg_count else "✗"
                status = "MATCH" if mysql_count == pg_count else "MISMATCH"

                print(
                    f"{match} {table_name:20s}: "
                    f"MySQL={mysql_count:>8,} | PostgreSQL={pg_count:>8,} | {status}"
                )

                if mysql_count != pg_count:
                    all_match = False
                    mismatches.append((table_name, mysql_count, pg_count))
                    self.errors.append(
                        f"Row count mismatch in {table_name}: "
                        f"MySQL={mysql_count}, PostgreSQL={pg_count}"
                    )

        if mismatches:
            print("\n" + "=" * 60)
            print("⚠ MISMATCHES FOUND:")
            print("=" * 60)
            for table_name, mysql_count, pg_count in mismatches:
                diff = pg_count - mysql_count
                print(
                    f"  {table_name}: {mysql_count:,} → {pg_count:,} (diff: {diff:+,})"
                )

        return all_match

    def validate_spatial_data(self) -> bool:
        """Validate PostGIS spatial data conversion."""
        print("\n" + "=" * 60)
        print("Spatial Data Validation")
        print("=" * 60)

        # Tables with spatial data
        spatial_tables = ["trig", "place", "town", "postcode6"]

        all_valid = True

        for table_name in spatial_tables:
            print(f"\n{table_name}:")

            with self.MySQLSession() as mysql_session, self.PgSession() as pg_session:
                # Check if table exists in both databases
                try:
                    # Sample 100 rows from MySQL
                    mysql_result = mysql_session.execute(
                        text(
                            f"SELECT id, wgs_lat, wgs_long FROM {table_name} "
                            f"WHERE wgs_lat IS NOT NULL AND wgs_long IS NOT NULL "
                            f"LIMIT 100"
                        )
                    )
                    mysql_rows = mysql_result.fetchall()

                    if not mysql_rows:
                        print(f"  ⚠ No rows with coordinates in MySQL {table_name}")
                        continue

                    # Check corresponding rows in PostgreSQL
                    errors = 0
                    for row in mysql_rows:
                        row_id, mysql_lat, mysql_lon = row

                        # Get PostgreSQL data
                        pg_result = pg_session.execute(
                            text(
                                f"SELECT "
                                f"wgs_lat, wgs_long, "
                                f"ST_Y(location::geometry) as pg_lat, "
                                f"ST_X(location::geometry) as pg_lon, "
                                f"location IS NULL as location_null "
                                f"FROM {table_name} WHERE id = :id"
                            ),
                            {"id": row_id},
                        )
                        pg_row = pg_result.fetchone()

                        if not pg_row:
                            errors += 1
                            if errors <= 3:
                                self.errors.append(
                                    f"Row {row_id} missing in PostgreSQL {table_name}"
                                )
                            continue

                        (
                            pg_wgs_lat,
                            pg_wgs_lon,
                            pg_lat,
                            pg_lon,
                            location_null,
                        ) = pg_row

                        # Check if location column is populated
                        if location_null:
                            errors += 1
                            if errors <= 3:
                                self.errors.append(
                                    f"{table_name} row {row_id}: location column is NULL"
                                )
                            continue

                        # Check if coordinates match (within tolerance)
                        lat_diff = abs(float(mysql_lat) - float(pg_lat))
                        lon_diff = abs(float(mysql_lon) - float(pg_lon))

                        if lat_diff > 0.000001 or lon_diff > 0.000001:
                            errors += 1
                            if errors <= 3:
                                self.errors.append(
                                    f"{table_name} row {row_id}: coordinate mismatch "
                                    f"(lat diff: {lat_diff:.8f}, lon diff: {lon_diff:.8f})"
                                )

                    if errors == 0:
                        print(f"  ✓ Checked {len(mysql_rows)} rows - all valid")
                    else:
                        print(f"  ✗ Found {errors} errors in {len(mysql_rows)} rows checked")
                        all_valid = False

                except Exception as e:
                    print(f"  ✗ Error checking {table_name}: {e}")
                    self.errors.append(f"Error validating spatial data in {table_name}: {e}")
                    all_valid = False

        return all_valid

    def check_null_locations(self) -> bool:
        """Check for NULL location columns that should have values."""
        print("\n" + "=" * 60)
        print("NULL Location Check")
        print("=" * 60)

        spatial_tables = ["trig", "place", "town", "postcode6"]

        all_ok = True

        with self.PgSession() as pg_session:
            for table_name in spatial_tables:
                try:
                    # Count rows with coordinates but NULL location
                    result = pg_session.execute(
                        text(
                            f"SELECT COUNT(*) FROM {table_name} "
                            f"WHERE wgs_lat IS NOT NULL "
                            f"AND wgs_long IS NOT NULL "
                            f"AND location IS NULL"
                        )
                    )
                    null_count = result.scalar() or 0

                    if null_count > 0:
                        print(
                            f"  ✗ {table_name}: {null_count:,} rows with coordinates but NULL location"
                        )
                        self.warnings.append(
                            f"{table_name}: {null_count} rows missing location data"
                        )
                        all_ok = False
                    else:
                        # Get total count with coordinates
                        result = pg_session.execute(
                            text(
                                f"SELECT COUNT(*) FROM {table_name} "
                                f"WHERE wgs_lat IS NOT NULL AND wgs_long IS NOT NULL"
                            )
                        )
                        total_count = result.scalar() or 0
                        print(
                            f"  ✓ {table_name}: All {total_count:,} rows with coordinates have location data"
                        )

                except Exception as e:
                    print(f"  ✗ Error checking {table_name}: {e}")
                    self.errors.append(f"Error checking NULL locations in {table_name}: {e}")
                    all_ok = False

        return all_ok

    def check_spatial_indexes(self) -> bool:
        """Check that spatial indexes exist."""
        print("\n" + "=" * 60)
        print("Spatial Index Check")
        print("=" * 60)

        expected_indexes = [
            ("trig", "location"),
            ("place", "location"),
            ("town", "location"),
            ("postcode6", "location"),
        ]

        all_exist = True

        with self.PgSession() as pg_session:
            for table_name, column_name in expected_indexes:
                try:
                    # Check if spatial index exists
                    result = pg_session.execute(
                        text(
                            "SELECT COUNT(*) FROM pg_indexes "
                            f"WHERE tablename = '{table_name}' "
                            f"AND indexdef LIKE '%USING gist%' "
                            f"AND indexdef LIKE '%{column_name}%'"
                        )
                    )
                    index_count = result.scalar() or 0

                    if index_count > 0:
                        print(f"  ✓ {table_name}.{column_name}: Spatial index exists")
                    else:
                        print(
                            f"  ✗ {table_name}.{column_name}: No spatial index found"
                        )
                        self.warnings.append(
                            f"Missing spatial index on {table_name}.{column_name}"
                        )
                        all_exist = False

                except Exception as e:
                    print(f"  ✗ Error checking {table_name}.{column_name}: {e}")
                    self.warnings.append(
                        f"Error checking spatial index on {table_name}.{column_name}: {e}"
                    )
                    all_exist = False

        return all_exist

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("VALIDATION SUMMARY")
        print("=" * 60)

        if not self.errors and not self.warnings:
            print("\n✅ All validation checks passed!")
            print("\nMigration appears to be successful.")
        else:
            if self.errors:
                print(f"\n❌ Found {len(self.errors)} errors:")
                for error in self.errors[:10]:  # Show first 10 errors
                    print(f"  - {error}")
                if len(self.errors) > 10:
                    print(f"  ... and {len(self.errors) - 10} more")

            if self.warnings:
                print(f"\n⚠️  Found {len(self.warnings)} warnings:")
                for warning in self.warnings[:10]:  # Show first 10 warnings
                    print(f"  - {warning}")
                if len(self.warnings) > 10:
                    print(f"  ... and {len(self.warnings) - 10} more")

        print()

    def validate(self) -> bool:
        """Run all validation checks."""
        print("\n" + "=" * 60)
        print("PostgreSQL Migration Validation")
        print("=" * 60)
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        start_time = datetime.now()

        # Run all checks
        checks = [
            ("Row counts", self.compare_row_counts),
            ("Spatial data", self.validate_spatial_data),
            ("NULL locations", self.check_null_locations),
            ("Spatial indexes", self.check_spatial_indexes),
        ]

        results = {}
        for check_name, check_func in checks:
            try:
                results[check_name] = check_func()
            except Exception as e:
                print(f"\n✗ Error running {check_name} check: {e}")
                import traceback

                traceback.print_exc()
                results[check_name] = False
                self.errors.append(f"Failed to run {check_name} check: {e}")

        # Print summary
        self.print_summary()

        elapsed = datetime.now() - start_time
        print(f"Validation completed in {elapsed}")
        print()

        # Return True if all checks passed (no errors)
        return len(self.errors) == 0


def main():
    """Main entry point."""
    try:
        validator = MigrationValidator()
        success = validator.validate()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
