"""add upd_timestamp utc triggers

Revision ID: f3e16ee9c5f1
Revises: a1b2c3d4e5f6
Create Date: 2026-01-08 21:14:58.651934

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "f3e16ee9c5f1"
down_revision: Union[str, Sequence[str], None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Store UTC consistently. Many tables use `timestamp` (no time zone), so we store a
    # naive UTC timestamp via `timezone('utc', clock_timestamp())`.
    #
    # Behaviour:
    # - INSERT: set upd_timestamp only if not explicitly provided
    # - UPDATE: set upd_timestamp unless the update explicitly changes it
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.set_upd_timestamp_utc()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
            IF TG_OP = 'INSERT' THEN
                IF NEW.upd_timestamp IS NULL THEN
                    NEW.upd_timestamp := timezone('utc', clock_timestamp());
                END IF;
                RETURN NEW;
            END IF;

            -- TG_OP = 'UPDATE'
            IF NEW.upd_timestamp IS DISTINCT FROM OLD.upd_timestamp THEN
                -- Respect explicit upd_timestamp changes (e.g. data backfills).
                RETURN NEW;
            END IF;

            NEW.upd_timestamp := timezone('utc', clock_timestamp());
            RETURN NEW;
        END;
        $$;
        """
    )

    # Attach triggers (and a UTC default for inserts) to every base table in the public
    # schema that contains an `upd_timestamp` column.
    op.execute(
        """
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN
                SELECT c.table_schema, c.table_name
                FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON t.table_schema = c.table_schema
                 AND t.table_name = c.table_name
                WHERE c.column_name = 'upd_timestamp'
                  AND c.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
            LOOP
                EXECUTE format(
                    'ALTER TABLE %I.%I ALTER COLUMN upd_timestamp SET DEFAULT (timezone(''utc'', clock_timestamp()))',
                    r.table_schema,
                    r.table_name
                );

                EXECUTE format(
                    'DROP TRIGGER IF EXISTS set_upd_timestamp_utc ON %I.%I',
                    r.table_schema,
                    r.table_name
                );

                EXECUTE format(
                    'CREATE TRIGGER set_upd_timestamp_utc '
                    'BEFORE INSERT OR UPDATE ON %I.%I '
                    'FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc()',
                    r.table_schema,
                    r.table_name
                );
            END LOOP;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Downgrade schema."""
    # Remove triggers/defaults from all tables that have an upd_timestamp column.
    op.execute(
        """
        DO $$
        DECLARE
            r RECORD;
        BEGIN
            FOR r IN
                SELECT c.table_schema, c.table_name
                FROM information_schema.columns c
                JOIN information_schema.tables t
                  ON t.table_schema = c.table_schema
                 AND t.table_name = c.table_name
                WHERE c.column_name = 'upd_timestamp'
                  AND c.table_schema = 'public'
                  AND t.table_type = 'BASE TABLE'
            LOOP
                EXECUTE format(
                    'DROP TRIGGER IF EXISTS set_upd_timestamp_utc ON %I.%I',
                    r.table_schema,
                    r.table_name
                );

                EXECUTE format(
                    'ALTER TABLE %I.%I ALTER COLUMN upd_timestamp DROP DEFAULT',
                    r.table_schema,
                    r.table_name
                );
            END LOOP;
        END
        $$;
        """
    )

    op.execute("DROP FUNCTION IF EXISTS public.set_upd_timestamp_utc();")
