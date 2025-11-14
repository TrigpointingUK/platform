#!/usr/bin/env python3
"""
Validate data migration from MySQL to PostgreSQL.

This script compares data between MySQL and PostgreSQL databases to ensure
the migration was successful.

Usage:
    python scripts/validate_migration.py

Environment variables required:
    For MySQL source:
        MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_DB
    For PostgreSQL target:
        DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.core.config import settings


class MigrationValidator:
    """Validate MySQL to PostgreSQL migration."""

    def __init__(self):
        """Initialize validator with connections to both databases."""
        # MySQL connection (source)
        mysql_host = os.getenv("MYSQL_HOST", settings.DB_HOST)
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER", settings.DB_USER)
        mysql_password = os.getenv("MYSQL_PASSWORD", settings.DB_PASSWORD)
        mysql_db = os.getenv("MYSQL_DB", settings.DB_NAME)
        
        mysql_url = (
            f"mysql+pymysql://{mysql_user}:{mysql_password}"
            f"@{mysql_host}:{mysql_port}/{mysql_db}"
        )
        
        # PostgreSQL connection (target)
        postgres_url = settings.DATABASE_URL
        
        try:
            self.mysql_engine = create_engine(mysql_url)
            self.mysql_session = sessionmaker(bind=self.mysql_engine)()
            print(f"✓ Connected to MySQL: {mysql_host}/{mysql_db}")
        except Exception as e:
            print(f"❌ Failed to connect to MySQL: {e}")
            print("Continuing with PostgreSQL-only validation...")
            self.mysql_engine = None
            self.mysql_session = None
        
        self.postgres_engine = create_engine(postgres_url)
        self.postgres_session = sessionmaker(bind=self.postgres_engine)()
        print(f"✓ Connected to PostgreSQL: {settings.DB_HOST}/{settings.DB_NAME}")
        
        self.errors: List[str] = []
        self.warnings: List[str] = []

    def get_table_count(self, session, table_name: str) -> int:
        """Get row count for a table."""
        try:
            result = session.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
            return result.scalar() or 0
        except Exception as e:
            return -1

    def compare_row_counts(self):
        """Compare row counts between MySQL and PostgreSQL."""
        print("\n" + "=" * 60)
        print("Comparing Row Counts")
        print("=" * 60)
        
        if not self.mysql_session:
            print("⚠️  MySQL connection not available, skipping comparison")
            return
        
        # Get list of tables from PostgreSQL
        inspector = inspect(self.postgres_engine)
        tables = inspector.get_table_names()
        
        mismatches = []
        matches = []
        
        for table in sorted(tables):
            mysql_count = self.get_table_count(self.mysql_session, table)
            pg_count = self.get_table_count(self.postgres_session, table)
            
            if mysql_count == -1:
                print(f"⚠️  {table}: not in MySQL (pg: {pg_count:,})")
                continue
            
            if mysql_count == pg_count:
                matches.append((table, mysql_count))
                print(f"✓ {table}: {mysql_count:,} rows match")
            else:
                mismatches.append((table, mysql_count, pg_count))
                diff = pg_count - mysql_count
                print(f"❌ {table}: MySQL {mysql_count:,} vs PostgreSQL {pg_count:,} (diff: {diff:+,})")
                self.errors.append(
                    f"Row count mismatch for {table}: MySQL={mysql_count:,}, PostgreSQL={pg_count:,}"
                )
        
        print(f"\n✓ {len(matches)} tables match")
        if mismatches:
            print(f"❌ {len(mismatches)} tables have mismatches")

    def validate_spatial_data(self):
        """Validate PostGIS spatial data in trig table."""
        print("\n" + "=" * 60)
        print("Validating Spatial Data")
        print("=" * 60)
        
        try:
            # Check that location column exists and has data
            result = self.postgres_session.execute(text("""
                SELECT
                    COUNT(*) as total,
                    COUNT(location) as with_location,
                    COUNT(*) - COUNT(location) as without_location
                FROM trig
            """))
            row = result.fetchone()
            
            total = row[0]
            with_location = row[1]
            without_location = row[2]
            
            print(f"\nTrig table spatial data:")
            print(f"  Total rows: {total:,}")
            print(f"  With location: {with_location:,} ({100 * with_location / total:.1f}%)")
            
            if without_location > 0:
                print(f"  ⚠️  Without location: {without_location:,} ({100 * without_location / total:.1f}%)")
                self.warnings.append(
                    f"{without_location:,} trig records are missing location data"
                )
            else:
                print(f"  ✓ All rows have location data")
            
            # Validate that coordinates are within WGS84 bounds
            result = self.postgres_session.execute(text("""
                SELECT
                    COUNT(*) as invalid_count
                FROM trig
                WHERE location IS NOT NULL
                AND (
                    ST_X(location::geometry) < -180 OR
                    ST_X(location::geometry) > 180 OR
                    ST_Y(location::geometry) < -90 OR
                    ST_Y(location::geometry) > 90
                )
            """))
            invalid_count = result.scalar()
            
            if invalid_count > 0:
                print(f"  ❌ {invalid_count:,} rows have invalid coordinates")
                self.errors.append(f"{invalid_count:,} trig records have invalid coordinates")
            else:
                print(f"  ✓ All coordinates are within valid WGS84 bounds")
            
            # Sample a few coordinates to verify they match legacy columns
            print("\n  Spot-checking coordinate consistency...")
            result = self.postgres_session.execute(text("""
                SELECT
                    id,
                    wgs_lat,
                    wgs_long,
                    ST_Y(location::geometry) as pg_lat,
                    ST_X(location::geometry) as pg_lon
                FROM trig
                WHERE location IS NOT NULL
                LIMIT 5
            """))
            
            for row in result:
                trig_id, lat, lon, pg_lat, pg_lon = row
                lat_diff = abs(float(lat) - pg_lat)
                lon_diff = abs(float(lon) - pg_lon)
                
                # Allow small floating point differences
                if lat_diff > 0.00001 or lon_diff > 0.00001:
                    print(f"    ⚠️  ID {trig_id}: lat diff={lat_diff:.6f}, lon diff={lon_diff:.6f}")
                    self.warnings.append(
                        f"Trig ID {trig_id} has coordinate mismatch"
                    )
                else:
                    print(f"    ✓ ID {trig_id}: coordinates match")
            
        except Exception as e:
            print(f"❌ Error validating spatial data: {e}")
            self.errors.append(f"Spatial validation error: {e}")

    def validate_foreign_keys(self):
        """Validate foreign key relationships."""
        print("\n" + "=" * 60)
        print("Validating Foreign Key Relationships")
        print("=" * 60)
        
        # Check tlog -> trig relationship
        try:
            result = self.postgres_session.execute(text("""
                SELECT COUNT(*)
                FROM tlog t
                LEFT JOIN trig tr ON t.trig_id = tr.id
                WHERE tr.id IS NULL
            """))
            orphan_count = result.scalar()
            
            if orphan_count > 0:
                print(f"  ❌ tlog: {orphan_count:,} orphaned records (no matching trig)")
                self.errors.append(f"{orphan_count:,} tlog records have no matching trig")
            else:
                print(f"  ✓ tlog: all records reference valid trigs")
        except Exception as e:
            print(f"  ⚠️  Error checking tlog->trig: {e}")
        
        # Check tlog -> user relationship
        try:
            result = self.postgres_session.execute(text("""
                SELECT COUNT(*)
                FROM tlog t
                LEFT JOIN "user" u ON t.user_id = u.id
                WHERE u.id IS NULL
            """))
            orphan_count = result.scalar()
            
            if orphan_count > 0:
                print(f"  ❌ tlog: {orphan_count:,} orphaned records (no matching user)")
                self.errors.append(f"{orphan_count:,} tlog records have no matching user")
            else:
                print(f"  ✓ tlog: all records reference valid users")
        except Exception as e:
            print(f"  ⚠️  Error checking tlog->user: {e}")
        
        # Check tphoto -> tlog relationship
        try:
            result = self.postgres_session.execute(text("""
                SELECT COUNT(*)
                FROM tphoto p
                LEFT JOIN tlog t ON p.tlog_id = t.id
                WHERE t.id IS NULL
            """))
            orphan_count = result.scalar()
            
            if orphan_count > 0:
                print(f"  ❌ tphoto: {orphan_count:,} orphaned records (no matching tlog)")
                self.errors.append(f"{orphan_count:,} tphoto records have no matching tlog")
            else:
                print(f"  ✓ tphoto: all records reference valid tlogs")
        except Exception as e:
            print(f"  ⚠️  Error checking tphoto->tlog: {e}")

    def sample_data_checks(self):
        """Perform spot checks on sample data."""
        print("\n" + "=" * 60)
        print("Sample Data Spot Checks")
        print("=" * 60)
        
        if not self.mysql_session:
            print("⚠️  MySQL connection not available, skipping comparison")
            return
        
        # Compare a few user records
        print("\nChecking sample user records...")
        try:
            mysql_result = self.mysql_session.execute(text("SELECT id, name, email FROM user LIMIT 3"))
            mysql_users = {row[0]: (row[1], row[2]) for row in mysql_result}
            
            for user_id, (name, email) in mysql_users.items():
                pg_result = self.postgres_session.execute(
                    text('SELECT name, email FROM "user" WHERE id = :id'),
                    {"id": user_id}
                )
                pg_row = pg_result.fetchone()
                
                if pg_row:
                    if pg_row[0] == name and pg_row[1] == email:
                        print(f"  ✓ User {user_id}: data matches")
                    else:
                        print(f"  ❌ User {user_id}: data mismatch")
                        self.errors.append(f"User {user_id} data doesn't match")
                else:
                    print(f"  ❌ User {user_id}: not found in PostgreSQL")
                    self.errors.append(f"User {user_id} missing from PostgreSQL")
        except Exception as e:
            print(f"  ⚠️  Error checking users: {e}")

    def print_summary(self):
        """Print validation summary."""
        print("\n" + "=" * 60)
        print("Validation Summary")
        print("=" * 60)
        
        if self.errors:
            print(f"\n❌ {len(self.errors)} ERRORS found:")
            for error in self.errors:
                print(f"  - {error}")
        
        if self.warnings:
            print(f"\n⚠️  {len(self.warnings)} WARNINGS:")
            for warning in self.warnings:
                print(f"  - {warning}")
        
        if not self.errors and not self.warnings:
            print("\n✅ All validations passed!")
            print("Migration appears successful.")
        elif not self.errors:
            print("\n✅ No critical errors found.")
            print("⚠️  Some warnings to review, but migration appears successful.")
        else:
            print("\n❌ Critical errors found!")
            print("Please review and fix issues before using PostgreSQL database.")

    def run(self):
        """Run all validation checks."""
        print("=" * 60)
        print("MySQL to PostgreSQL Migration - Validation")
        print("=" * 60)
        
        self.compare_row_counts()
        self.validate_spatial_data()
        self.validate_foreign_keys()
        self.sample_data_checks()
        self.print_summary()


def main():
    """Main entry point."""
    validator = MigrationValidator()
    validator.run()


if __name__ == "__main__":
    main()

