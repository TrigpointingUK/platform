#!/usr/bin/env python3
"""
Create PostgreSQL tables from MySQL schema.

This script connects to MySQL, reads all table structures, and creates
equivalent tables in PostgreSQL with appropriate type conversions.

Usage:
    python scripts/create_postgres_schema.py

Environment variables required:
    MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_NAME (source)
    DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME (target)
"""

import os
import sys
from pathlib import Path
from urllib.parse import quote_plus

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

# Type mapping from MySQL to PostgreSQL
MYSQL_TO_PG_TYPE_MAP = {
    'TINYINT': 'SMALLINT',
    'MEDIUMINT': 'INTEGER',
    'INT': 'INTEGER',
    'BIGINT': 'BIGINT',
    'FLOAT': 'REAL',
    'DOUBLE': 'DOUBLE PRECISION',
    'DECIMAL': 'DECIMAL',
    'VARCHAR': 'VARCHAR',
    'CHAR': 'CHAR',
    'TEXT': 'TEXT',
    'TINYTEXT': 'TEXT',
    'MEDIUMTEXT': 'TEXT',
    'LONGTEXT': 'TEXT',
    'BLOB': 'BYTEA',
    'TINYBLOB': 'BYTEA',
    'MEDIUMBLOB': 'BYTEA',
    'LONGBLOB': 'BYTEA',
    'DATE': 'DATE',
    'DATETIME': 'TIMESTAMP',
    'TIMESTAMP': 'TIMESTAMP',
    'TIME': 'TIME',
    'YEAR': 'SMALLINT',
    'ENUM': 'VARCHAR',
    'SET': 'TEXT',
}


class SchemaCreator:
    """Create PostgreSQL schema from MySQL."""

    def __init__(self):
        """Initialize with both database connections."""
        # MySQL connection
        mysql_host = os.getenv("MYSQL_HOST", "localhost")
        mysql_port = os.getenv("MYSQL_PORT", "3306")
        mysql_user = os.getenv("MYSQL_USER")
        mysql_password = os.getenv("MYSQL_PASSWORD")
        mysql_database = os.getenv("MYSQL_NAME")

        if not all([mysql_user, mysql_password, mysql_database]):
            raise ValueError(
                "Missing MySQL environment variables: "
                "MYSQL_HOST, MYSQL_PORT, MYSQL_USER, MYSQL_PASSWORD, MYSQL_NAME"
            )

        mysql_url = (
            f"mysql+pymysql://{quote_plus(mysql_user)}:{quote_plus(mysql_password)}"
            f"@{mysql_host}:{mysql_port}/{mysql_database}"
        )
        self.mysql_engine = create_engine(mysql_url)

        # PostgreSQL connection
        pg_host = os.getenv("DB_HOST", "localhost")
        pg_port = os.getenv("DB_PORT", "5432")
        pg_user = os.getenv("DB_USER")
        pg_password = os.getenv("DB_PASSWORD")
        pg_database = os.getenv("DB_NAME")

        if not all([pg_user, pg_password, pg_database]):
            raise ValueError(
                "Missing PostgreSQL environment variables: "
                "DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_NAME"
            )

        pg_url = (
            f"postgresql+psycopg2://{quote_plus(pg_user)}:{quote_plus(pg_password)}"
            f"@{pg_host}:{pg_port}/{pg_database}"
        )
        self.pg_engine = create_engine(pg_url)
        self.PgSession = sessionmaker(bind=self.pg_engine)

        print(f"Connected to MySQL: {mysql_host}/{mysql_database}")
        print(f"Connected to PostgreSQL: {pg_host}/{pg_database}")

    def convert_column_type(self, column) -> str:
        """Convert MySQL column type to PostgreSQL type."""
        mysql_type = str(column['type']).upper()
        
        # Handle NULL type (unknown column type)
        if mysql_type in ('NULL', 'NULLTYPE'):
            # Default to TEXT for unknown types
            return 'TEXT'
        
        # Extract base type (e.g., VARCHAR(255) -> VARCHAR)
        base_type = mysql_type.split('(')[0]
        
        # Get PostgreSQL equivalent
        pg_type = MYSQL_TO_PG_TYPE_MAP.get(base_type, mysql_type)
        
        # Handle types with length/precision
        if '(' in mysql_type:
            # Keep the length/precision
            suffix = mysql_type[mysql_type.index('('):]
            pg_type = pg_type + suffix
        
        return pg_type

    def sanitize_default_value(self, default_val, col_type: str) -> str:
        """Convert MySQL default values to PostgreSQL format."""
        if default_val is None:
            return ""
        
        # Handle MySQL-specific timestamp defaults
        if isinstance(default_val, str):
            upper_default = default_val.upper()
            
            # MySQL's CURRENT_TIMESTAMP with ON UPDATE - PostgreSQL doesn't support ON UPDATE
            if 'CURRENT_TIMESTAMP' in upper_default:
                if 'ON UPDATE' in upper_default:
                    # Just use CURRENT_TIMESTAMP, ON UPDATE will need triggers
                    return " DEFAULT CURRENT_TIMESTAMP"
                return " DEFAULT CURRENT_TIMESTAMP"
            
            # MySQL returns defaults WITH quotes already (e.g. "'0'" not "0")
            # Strip outer quotes first
            clean_val = default_val.strip()
            if clean_val.startswith("'") and clean_val.endswith("'"):
                clean_val = clean_val[1:-1]
            
            # Invalid date/time defaults (check AFTER stripping quotes)
            if clean_val in ('0000-00-00', '0000-00-00 00:00:00', '00:00:00'):
                # PostgreSQL doesn't allow zero dates - use NULL or omit default
                return ""
            
            # Now determine if we need to quote it for PostgreSQL
            # Check if it's a numeric type
            col_type_upper = col_type.upper()
            is_numeric = any(t in col_type_upper for t in [
                'INT', 'DECIMAL', 'NUMERIC', 'REAL', 'DOUBLE', 'FLOAT', 'SERIAL'
            ])
            
            if is_numeric:
                # For numeric columns, don't quote the default
                try:
                    # Try to parse as a number to validate
                    float(clean_val)
                    return f" DEFAULT {clean_val}"
                except ValueError:
                    # If it's not a valid number, skip the default
                    return ""
            else:
                # For string/char types, quote the default
                return f" DEFAULT '{clean_val}'"
        
        # Numeric defaults (when MySQL returns as number not string)
        return f" DEFAULT {default_val}"

    def has_null_values(self, table_name: str, column_name: str) -> bool:
        """Check if a column has any NULL values in the actual data."""
        try:
            with self.mysql_engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT COUNT(*) FROM {table_name} WHERE `{column_name}` IS NULL")
                )
                count = result.scalar()
                return count > 0
        except Exception:
            # If query fails, assume no NULLs
            return False

    def create_table_sql(self, table_name: str) -> str:
        """Generate CREATE TABLE SQL for PostgreSQL from MySQL table."""
        inspector = inspect(self.mysql_engine)
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        indexes = inspector.get_indexes(table_name)

        # Get the EXACT column names from MySQL (SQLAlchemy may lowercase them)
        with self.mysql_engine.connect() as conn:
            result = conn.execute(text(
                f"SELECT COLUMN_NAME FROM INFORMATION_SCHEMA.COLUMNS "
                f"WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = '{table_name}' "
                f"ORDER BY ORDINAL_POSITION"
            ))
            exact_column_names = [row[0] for row in result]
        
        # Map inspector column names (potentially lowercased) to exact names
        col_name_map = {}
        for exact_name in exact_column_names:
            for col in columns:
                if col['name'].lower() == exact_name.lower():
                    col_name_map[col['name']] = exact_name
                    break

        # PostgreSQL reserved words that need quoting
        pg_reserved = {'user', 'order', 'group', 'table', 'index', 'type', 'order'}
        
        # Quote table name if it's a reserved word or has spaces
        quoted_table_name = f'"{table_name}"' if table_name.lower() in pg_reserved or ' ' in table_name else table_name

        # Build column definitions
        col_defs = []
        for col in columns:
            col_name = col_name_map.get(col['name'], col['name'])  # Use exact name from MySQL
            
            # ALWAYS quote column names to preserve exact case from MySQL
            quoted_col_name = f'"{col_name}"'
            
            col_type = self.convert_column_type(col)
            
            # Strip collation from type (PostgreSQL uses different collations)
            if ' COLLATE ' in col_type:
                col_type = col_type.split(' COLLATE ')[0]
            
            # Handle default values first (needed for nullable check)
            default = ""
            if col['default'] is not None:
                default = self.sanitize_default_value(col['default'], col_type)
            
            # Handle nullable
            # PostgreSQL is stricter than MySQL about NOT NULL constraints
            # MySQL is very lenient and allows NULLs in many NOT NULL columns
            # For compatibility, we'll make most columns nullable unless they're obviously required
            if col['nullable']:
                nullable = ""
            elif not col['nullable']:
                # Always enforce NOT NULL for auto-increment (primary keys)
                if col.get('autoincrement'):
                    nullable = " NOT NULL"
                else:
                    # Make everything else nullable for MySQL compatibility
                    # This avoids countless issues with MySQL's lenient NULL handling
                    nullable = ""
            else:
                nullable = ""
            
            # Handle auto_increment -> SERIAL/BIGSERIAL
            if col.get('autoincrement'):
                if 'INT' in col_type.upper():
                    if 'BIGINT' in col_type.upper():
                        col_type = 'BIGSERIAL'
                    else:
                        col_type = 'SERIAL'
                    default = ""  # SERIAL handles its own default
            
            col_def = f"  {quoted_col_name} {col_type}{nullable}{default}"
            col_defs.append(col_def)

        # Add PostGIS location column for spatial tables
        spatial_tables = ['trig', 'place', 'town', 'postcode6']
        if table_name in spatial_tables:
            col_defs.append("  location GEOGRAPHY(POINT, 4326)")

        # Add primary key constraint
        if pk_constraint and pk_constraint['constrained_columns']:
            # Map PK column names to exact names
            exact_pk_cols = []
            for col in pk_constraint['constrained_columns']:
                exact_col = col_name_map.get(col, col)
                exact_pk_cols.append(exact_col)
            
            # Always quote to preserve case
            pk_cols = ', '.join(f'"{col}"' for col in exact_pk_cols)
            col_defs.append(f"  PRIMARY KEY ({pk_cols})")

        # Create table SQL
        drop_sql = f"DROP TABLE IF EXISTS {quoted_table_name} CASCADE;"
        create_sql = f"CREATE TABLE {quoted_table_name} (\n"
        create_sql += ',\n'.join(col_defs)
        create_sql += "\n);"

        # Create indexes (excluding primary key index)
        index_sqls = []
        for idx in indexes:
            if not idx['unique']:  # Skip unique indexes for now
                idx_name = idx['name']
                # Map index column names to exact names
                exact_idx_cols = []
                for col in idx['column_names']:
                    exact_col = col_name_map.get(col, col)
                    exact_idx_cols.append(exact_col)
                
                # Always quote to preserve case
                idx_cols = ', '.join(f'"{col}"' for col in exact_idx_cols)
                index_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {quoted_table_name} ({idx_cols});"
                index_sqls.append(index_sql)

        return drop_sql, create_sql, index_sqls

    def create_all_tables(self):
        """Create all tables in PostgreSQL."""
        inspector = inspect(self.mysql_engine)
        tables = inspector.get_table_names()

        # Order tables by dependency (put reference tables first)
        priority_tables = ['status', 'county', 'town', 'server']
        ordered_tables = [t for t in priority_tables if t in tables]
        ordered_tables += [t for t in tables if t not in priority_tables]

        print(f"\nCreating {len(ordered_tables)} tables in PostgreSQL...")
        print("=" * 60)

        created = 0
        failed = []

        for table_name in ordered_tables:
            # Use a new session for each table to avoid transaction issues
            with self.PgSession() as session:
                try:
                    print(f"\nCreating table: {table_name}")
                    
                    # Get CREATE TABLE SQL (includes DROP)
                    drop_sql, create_sql, index_sqls = self.create_table_sql(table_name)
                    
                    # Execute DROP TABLE
                    session.execute(text(drop_sql))
                    session.commit()
                    
                    # Execute CREATE TABLE
                    session.execute(text(create_sql))
                    session.commit()
                    print(f"  ✓ Table created")
                    
                    # Create indexes
                    for idx_sql in index_sqls:
                        try:
                            session.execute(text(idx_sql))
                            session.commit()
                        except Exception as e:
                            print(f"  ⚠ Index creation warning: {e}")
                            session.rollback()
                    
                    created += 1
                    
                except Exception as e:
                    session.rollback()
                    print(f"  ✗ Error: {e}")
                    failed.append((table_name, str(e)))

        # Fix nullable constraints for tables with composite PRIMARY KEY that includes nullable fields
        # PostgreSQL forces PRIMARY KEY columns to be NOT NULL, but MySQL allows NULLs despite the constraint
        print("\nFixing nullable constraints for MySQL compatibility...")
        with self.pg_engine.connect() as conn:
            try:
                # The 'place' table has a composite PK with address fields that can be NULL in MySQL
                conn.execute(text("""
                    ALTER TABLE place 
                        ALTER COLUMN addr1 DROP NOT NULL,
                        ALTER COLUMN addr2 DROP NOT NULL,
                        ALTER COLUMN addr3 DROP NOT NULL,
                        ALTER COLUMN addr4 DROP NOT NULL,
                        ALTER COLUMN addr5 DROP NOT NULL,
                        ALTER COLUMN addr6 DROP NOT NULL,
                        ALTER COLUMN postcode8 DROP NOT NULL
                """))
                conn.commit()
                print("  ✓ Fixed place table nullable constraints")
            except Exception as e:
                print(f"  ⚠️  Could not fix place nullable constraints: {e}")
                conn.rollback()

        print("\n" + "=" * 60)
        print(f"✅ Created {created}/{len(ordered_tables)} tables")
        
        if failed:
            print(f"\n⚠️  Failed to create {len(failed)} tables:")
            for table_name, error in failed:
                print(f"  - {table_name}: {error}")
        
        return created, failed


def main():
    """Main entry point."""
    print("\n" + "=" * 60)
    print("PostgreSQL Schema Creation from MySQL")
    print("=" * 60)

    try:
        creator = SchemaCreator()
        created, failed = creator.create_all_tables()
        
        if failed:
            print("\n⚠️  Some tables failed to create. You may need to:")
            print("  1. Review the errors above")
            print("  2. Manually create problematic tables")
            print("  3. Re-run this script")
            sys.exit(1)
        else:
            print("\n✅ All tables created successfully!")
            print("\nYou can now run the import script to load data.")
            sys.exit(0)
            
    except Exception as e:
        print(f"\n✗ Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

