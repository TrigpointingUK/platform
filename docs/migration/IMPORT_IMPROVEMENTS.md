# Import Script Improvements - November 2025

## Changes Made to `scripts/import_postgres.py`

### 1. PostgreSQL COPY Command Implementation (10x-50x Faster)

Added new method `import_csv_with_copy()` that uses PostgreSQL's native COPY command for bulk imports:

- **Speed improvement**: 10x-50x faster than INSERT statements for large tables
- **Automatic fallback**: Falls back to INSERT for tables with PostGIS location columns
- **Error handling**: If COPY fails, automatically retries with INSERT method

**How it works**:
- Uses raw psycopg2 connection and `cursor.copy_expert()`
- Directly streams CSV file to PostgreSQL
- Bypasses SQLAlchemy overhead for maximum performance
- Still uses INSERT with `ST_GeogFromText()` for spatial tables (trig, place, town, postcode6)

### 2. Improved Progress Reporting

**Row-based AND time-based progress**:
- Progress updates every N rows (depending on table size)
- **NEW**: Also reports progress every 30 seconds (even if row threshold not reached)
- Shows rows/second rate
- Shows estimated time to completion (ETA)

**Progress intervals adjusted**:
- Tables < 10k rows: Every 2,500 rows (was 5,000)
- Tables 10k-100k: Every 10,000 rows (was 25,000)
- Tables 100k-1M: Every 25,000 rows (was 50,000)  
- Tables 1M+: Every 50,000 rows (was 100,000)

**Example output**:
```
Progress: 250,000/2,750,000 (9.1%) [8,547 rows/s, ETA: 0:04:52]
```

### 3. Increased Batch Size

- **Old**: 5,000 rows per batch
- **New**: 10,000 rows per batch
- Reduces number of commits, improving performance

### 4. Per-Table Timing

Each table now reports:
- Time taken to import
- Rows per second rate
- Overall elapsed time

**Example**:
```
✓ Imported 2,750,000 rows in 0:05:21 (8,547 rows/s)
⏱️  Table completed in 0:05:21
```

### 5. Import Order Preview

Before starting, the script now shows:
- All tables to be imported
- Row count for each table
- Import order (respects dependencies)

This helps you estimate total time and see what's coming.

## Performance Improvements

### Expected Speed Gains

| Table Size | Old Method | New Method (COPY) | Speedup |
|------------|-----------|-------------------|---------|
| 10k rows   | ~10s      | ~1s               | 10x     |
| 100k rows  | ~2 min    | ~5s               | 24x     |
| 1M rows    | ~20 min   | ~30s              | 40x     |
| 2.7M rows  | ~1 hour   | ~2 min            | 30x     |

### Tables Using COPY (Fast Path)

Most tables will use the fast COPY command:
- status, county, server, user
- tlog, tphoto
- postcodes, postcode8 (2.7M+ rows!)
- All other non-spatial tables

### Tables Using INSERT (Spatial Path)

These tables need special handling for PostGIS and use INSERT:
- trig (with location column)
- place (with location column)
- town (with location column)
- postcode6 (with location column)

These will still benefit from larger batch size (10k) and better progress reporting.

## Migration Script Already Updated

The `run_migration_on_bastion.sh` script already correctly uses:
- **Source**: `fastapi-legacy-credentials` (legacy production MySQL)
- **Target**: `fastapi-staging-postgres-credentials` (staging PostgreSQL)

## Estimated Total Migration Time

Based on typical database sizes:

**Before improvements**: 2-4 hours
**After improvements**: 15-30 minutes

Breakdown (estimated):
- Export from MySQL: ~5 minutes
- Transform coordinates: ~2 minutes  
- Create schema: ~1 minute
- **Import to PostgreSQL: ~5-10 minutes** (was 1-2 hours)
- Create spatial indexes: ~2 minutes
- Validation: ~5 minutes

**Total: ~20-25 minutes** (was 2-4 hours)

## Running the Improved Migration

Simply run the same command as before:

```bash
./scripts/run_migration_on_bastion.sh
```

The script will automatically use the improved import with:
- COPY command for maximum speed
- Real-time progress with ETA
- Per-table timing information

## Monitoring Progress

You'll now see output like:

```
Found 38 CSV files to import

Import order:
  1. status (5 rows)
  2. county (47 rows)
  3. town (2,847 rows)
  ...
  37. postcodes (2,750,000 rows)
  38. postcode8 (1,800,000 rows)

Importing status (5 rows)...
  ✓ Imported 5 rows in 0:00:00 (500 rows/s)
  ⏱️  Table completed in 0:00:00

Importing postcodes (2,750,000 rows)...
  Progress: 50,000/2,750,000 (1.8%) [12,500 rows/s, ETA: 0:03:36]
  Progress: 100,000/2,750,000 (3.6%) [13,200 rows/s, ETA: 0:03:20]
  ...
  ✓ Imported 2,750,000 rows in 0:03:27 (13,250 rows/s)
  ⏱️  Table completed in 0:03:27

✅ Successfully imported 38/38 tables
Total elapsed time: 0:18:43
```

## Troubleshooting

### If Import Hangs

Check progress with:
```sql
-- In PostgreSQL
SELECT count(*) FROM pg_stat_activity WHERE state = 'active' AND query ILIKE '%COPY%';
```

### If COPY Fails

The script automatically falls back to INSERT method. Check the output for:
```
✗ COPY failed: <error message>
🔄 Falling back to INSERT method...
```

### Check Table Counts

After migration:
```sql
SELECT schemaname, tablename, n_live_tup 
FROM pg_stat_user_tables 
ORDER BY n_live_tup DESC;
```

## Next Steps

1. Run the migration: `./scripts/run_migration_on_bastion.sh`
2. Monitor progress (much better visibility now!)
3. Validate results (row counts, spatial data)
4. Test application against staging PostgreSQL
5. Repeat migration practice runs as needed

---

**Last Updated**: 2025-11-24
**Status**: Ready for testing

