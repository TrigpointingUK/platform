-- Bring tuk_staging's triggers, keys, constraints and indexes back in line with
-- tuk_production.
--
-- Staging was rebuilt from a production dump around 2026-01-10, after migration
-- f3e16ee9c5f1 (upd_timestamp triggers) had run. The rebuild left out the
-- triggers and a few other objects, and because it also copied production's
-- alembic_version, `make migrate-staging` will never recreate them.
--
-- Differences this fixes (production is correct in every case):
--   * 9 set_upd_timestamp_utc triggers missing (from migration f3e16ee9c5f1)
--   * area_type_code_key UNIQUE (code) missing
--   * 4 user_activity_summary indexes missing (api/db/user_activity_summary_view.py);
--     without the unique one, REFRESH MATERIALIZED VIEW CONCURRENTLY fails
--   * trig / user primary keys named pk_trig / pk_user instead of the
--     Postgres defaults trig_pkey / user_pkey
--
-- Deliberately left alone: scratch tables that exist in only one database
-- (production: area_staging_ctryie, _trig_county_backup; staging: tmp_gbpn and
-- the visits view).
--
-- Usage (with `make postgres-tunnel` running):
--   source scripts/set-db-env-staging.sh
--   PGPASSWORD="$DB_PASSWORD" psql -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" \
--     -d "$DB_NAME" -v ON_ERROR_STOP=1 -f scripts/fix_staging_schema_drift.sql
--
-- Runs in one transaction and is safe to re-run: each step checks first.

\set ON_ERROR_STOP on
BEGIN;

DO $$
BEGIN
    IF current_database() <> 'tuk_staging' THEN
        RAISE EXCEPTION 'This script only fixes tuk_staging (connected to %)', current_database();
    END IF;
END
$$;

-- 1. upd_timestamp triggers: the same loop as migration f3e16ee9c5f1, which
--    drops and recreates each trigger, so it is idempotent
DO $$
DECLARE
    r RECORD;
    created integer := 0;
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
            r.table_schema, r.table_name
        );
        EXECUTE format(
            'DROP TRIGGER IF EXISTS set_upd_timestamp_utc ON %I.%I',
            r.table_schema, r.table_name
        );
        EXECUTE format(
            'CREATE TRIGGER set_upd_timestamp_utc '
            'BEFORE INSERT OR UPDATE ON %I.%I '
            'FOR EACH ROW EXECUTE FUNCTION public.set_upd_timestamp_utc()',
            r.table_schema, r.table_name
        );
        created := created + 1;
        RAISE NOTICE 'set_upd_timestamp_utc trigger on %', r.table_name;
    END LOOP;
    RAISE NOTICE 'upd_timestamp triggers in place: %', created;
END
$$;

-- 2. area_type.code unique constraint. Staging kept the unique index
--    area_type_code_key but not the constraint built on it, so promote the
--    index rather than creating a second one.
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conrelid = 'public.area_type'::regclass AND conname = 'area_type_code_key'
    ) THEN
        RAISE NOTICE 'area_type_code_key constraint already present';
    ELSIF EXISTS (
        SELECT 1 FROM pg_indexes
        WHERE schemaname = 'public' AND indexname = 'area_type_code_key'
    ) THEN
        ALTER TABLE public.area_type
            ADD CONSTRAINT area_type_code_key UNIQUE USING INDEX area_type_code_key;
        RAISE NOTICE 'Promoted index area_type_code_key to a UNIQUE constraint';
    ELSE
        ALTER TABLE public.area_type ADD CONSTRAINT area_type_code_key UNIQUE (code);
        RAISE NOTICE 'Added area_type_code_key';
    END IF;
END
$$;

-- 3. user_activity_summary indexes (definitions from api/db/user_activity_summary_view.py)
CREATE UNIQUE INDEX IF NOT EXISTS idx_user_activity_summary_user_id
    ON user_activity_summary (user_id);
CREATE INDEX IF NOT EXISTS idx_user_activity_summary_trigs_desc
    ON user_activity_summary (total_trigs_logged DESC, user_id DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_summary_photos_desc
    ON user_activity_summary (total_photos DESC, user_id DESC);
CREATE INDEX IF NOT EXISTS idx_user_activity_summary_member_since_desc
    ON user_activity_summary (member_since DESC, user_id DESC);

-- 4. Primary key names (renaming the constraint renames its index too;
--    foreign keys reference it by OID, so they are unaffected)
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'public.trig'::regclass AND conname = 'pk_trig') THEN
        ALTER TABLE public.trig RENAME CONSTRAINT pk_trig TO trig_pkey;
        RAISE NOTICE 'Renamed pk_trig -> trig_pkey';
    END IF;
    IF EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'public."user"'::regclass AND conname = 'pk_user') THEN
        ALTER TABLE public."user" RENAME CONSTRAINT pk_user TO user_pkey;
        RAISE NOTICE 'Renamed pk_user -> user_pkey';
    END IF;
END
$$;

COMMIT;
