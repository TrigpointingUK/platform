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

    def create_table_sql(self, table_name: str) -> str:
        """Generate CREATE TABLE SQL for PostgreSQL from MySQL table."""
        inspector = inspect(self.mysql_engine)
        columns = inspector.get_columns(table_name)
        pk_constraint = inspector.get_pk_constraint(table_name)
        indexes = inspector.get_indexes(table_name)

        # Build column definitions
        col_defs = []
        for col in columns:
            col_name = col['name']
            col_type = self.convert_column_type(col)
            
            # Handle nullable
            nullable = "" if col['nullable'] else " NOT NULL"
            
            # Handle default values
            default = ""
            if col['default'] is not None:
                default_val = col['default']
                if isinstance(default_val, str):
                    default = f" DEFAULT '{default_val}'"
                else:
                    default = f" DEFAULT {default_val}"
            
            # Handle auto_increment
            autoincrement = ""
            if col.get('autoincrement'):
                if 'INT' in col_type.upper():
                    col_type = 'SERIAL' if 'INT' in col_type else 'BIGSERIAL'
                    default = ""  # SERIAL handles its own default
            
            col_def = f"  {col_name} {col_type}{autoincrement}{nullable}{default}"
            col_defs.append(col_def)

        # Add primary key constraint
        if pk_constraint and pk_constraint['constrained_columns']:
            pk_cols = ', '.join(pk_constraint['constrained_columns'])
            col_defs.append(f"  PRIMARY KEY ({pk_cols})")

        # Create table SQL
        create_sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
        create_sql += ',\n'.join(col_defs)
        create_sql += "\n);"

        # Create indexes (excluding primary key index)
        index_sqls = []
        for idx in indexes:
            if not idx['unique']:  # Skip unique indexes for now
                idx_name = idx['name']
                idx_cols = ', '.join(idx['column_names'])
                index_sql = f"CREATE INDEX IF NOT EXISTS {idx_name} ON {table_name} ({idx_cols});"
                index_sqls.append(index_sql)

        return create_sql, index_sqls

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

        with self.PgSession() as session:
            for table_name in ordered_tables:
                try:
                    print(f"\nCreating table: {table_name}")
                    
                    # Get CREATE TABLE SQL
                    create_sql, index_sqls = self.create_table_sql(table_name)
                    
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
                    
                    created += 1
                    
                except Exception as e:
                    session.rollback()
                    print(f"  ✗ Error: {e}")
                    failed.append((table_name, str(e)))

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

