# Postcode Database Conversion Script

This script converts the NSPL (National Statistics Postcode Lookup) CSV file into SQL statements for importing UK postcode data into the database.

## Generated Table Structure

The script creates a `postcodes` table with the following structure:

```sql
CREATE TABLE postcodes (
    code VARCHAR(10) NOT NULL,
    lat DECIMAL(10, 7) NOT NULL,
    `long` DECIMAL(11, 7) NOT NULL,
    PRIMARY KEY (code),
    INDEX idx_code_prefix (code(4))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

### Indexes

- **PRIMARY KEY on `code`**: Ensures unique postcodes and provides fast exact lookups
- **PREFIX INDEX on `code(4)`**: Optimizes prefix searches (e.g., `WHERE code LIKE 'AB1%'`) by indexing the first 4 characters

This index structure is ideal for:
- Exact postcode lookups: `WHERE code = 'AB1 0AA'`
- Postcode prefix searches: `WHERE code LIKE 'AB1%'`
- Area/district searches: `WHERE code LIKE 'AB%'`

## Usage

### Basic Usage

```bash
# Activate virtual environment
source venv/bin/activate

# Run with default paths
python scripts/convert_postcodes_to_sql.py

# Or specify custom input/output paths
python scripts/convert_postcodes_to_sql.py <input_csv> <output_sql>
```

### Default Paths

- **Input**: `res/NSPL_Online_latest_Centroids_.csv`
- **Output**: `init-db/postcodes.sql`

### Example

```bash
# Convert using default paths
python scripts/convert_postcodes_to_sql.py

# Custom paths
python scripts/convert_postcodes_to_sql.py data/postcodes.csv output/postcodes.sql
```

## CSV Format

The script expects a CSV file with the following columns:
- `PCDS`: Postcode (e.g., "AB1 0AA")
- `LAT`: Latitude (decimal degrees)
- `LONG`: Longitude (decimal degrees)

## Output

The script generates:
1. SQL to drop the legacy `postcode8` table
2. SQL to create the new `postcodes` table with indexes
3. Batched INSERT statements (1,000 rows per statement) for all postcodes

### Statistics

For the current NSPL dataset:
- **Rows processed**: 2,717,743 postcodes
- **Output file size**: ~94 MB
- **INSERT statements**: 2,718 batches

## Migration from postcode8

This table replaces the legacy `postcode8` table which was a cache of an external API. The new `postcodes` table:
- Contains all UK postcodes from the NSPL dataset
- Has proper indexes for efficient querying
- Stores WGS84 coordinates directly without external API dependency
- Provides higher precision coordinates (DECIMAL(10,7) for lat, DECIMAL(11,7) for lon)

### API Changes

The Find Trigs API (`/api/v1/locations/search`) has been updated to:
- Use the new `postcodes` table instead of `postcode8`
- Continue supporting legacy `postcode6` table for backward compatibility
- Use OSGB eastings/northings for `postcode6` conversions (as wgs_lat column is corrupted)

## Database Import

To import the generated SQL file into your database:

```bash
# Using mysql command line
mysql -u username -p database_name < init-db/postcodes.sql

# Or using Docker Compose
docker compose exec -T db mysql -u root -p database_name < init-db/postcodes.sql
```

## Performance Notes

- The script processes ~2.7M rows in approximately 30-60 seconds
- Batched INSERTs (1,000 rows each) optimize database import performance
- The prefix index on `code(4)` provides efficient prefix matching without indexing the full string length
- Using InnoDB engine provides ACID compliance and row-level locking

## Data Source

The NSPL (National Statistics Postcode Lookup) dataset is provided by the Office for National Statistics (ONS) and contains comprehensive UK postcode information including geographic coordinates.

