# Postcode API Migration Summary

## Overview

The Find Trigs API has been updated to use the new `postcodes` table from the NSPL (National Statistics Postcode Lookup) dataset instead of the legacy `postcode8` table.

## Changes Made

### 1. New Database Table

A new `postcodes` table has been created with the following structure:

```sql
CREATE TABLE postcodes (
    code VARCHAR(10) NOT NULL,
    lat DECIMAL(10, 7) NOT NULL,
    `long` DECIMAL(11, 7) NOT NULL,
    PRIMARY KEY (code),
    INDEX idx_code_prefix (code(4))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**Key Features:**
- Contains 2,717,743 UK postcodes from the official NSPL dataset
- Higher precision coordinates (10,7 for lat, 11,7 for lon vs 6,5 in old tables)
- Prefix index on first 4 characters for efficient prefix searching
- WGS84 coordinates stored directly (no conversion needed)

### 2. API Model Changes

**New Model Added:** `api/models/location.py`
```python
class Postcode(Base):
    """Postcode model for all UK postcodes from NSPL dataset."""
    
    __tablename__ = "postcodes"
    
    code = Column(String(10), primary_key=True, nullable=False)
    lat: Any = Column(DECIMAL(10, 7), nullable=False)
    long: Any = Column(DECIMAL(11, 7), nullable=False)
```

The legacy `Postcode8` model is retained for backward compatibility but marked as legacy.

### 3. CRUD Function Updates

**File:** `api/crud/locations.py`

**Function:** `search_postcodes()`
- **Before:** Returned `Tuple[List[Postcode6], List[Postcode8]]`
- **After:** Returns `Tuple[List[Postcode6], List[Postcode]]`
- Now queries the new `postcodes` table instead of `postcode8`

### 4. Endpoint Updates

**File:** `api/api/v1/endpoints/locations.py`

**Endpoint:** `GET /api/v1/locations/search`

**Changes:**
1. **Postcode6 Fix**: Now uses OSGB eastings/northings for coordinate conversion
   - Previous code used `pc.wgs_lat` and `pc.wgs_long` which were corrupted
   - Now uses `osgb_to_wgs84(pc.osgb_eastings, pc.osgb_northings)`

2. **Postcodes Table**: Uses the new `postcodes` table for full postcode lookups
   - Directly uses `pc.lat` and `pc.long` from the NSPL data
   - No conversion needed (already in WGS84)

## Benefits

### Data Quality
- Official NSPL dataset with verified coordinates
- Higher precision (7 decimal places vs 5)
- No dependency on external APIs
- Regular updates available from ONS

### Performance
- Prefix index optimized for postcode searches
- 2.7M postcodes available locally
- Faster queries (no external API calls)

### Maintenance
- Single source of truth for postcode data
- Easy to update with new NSPL releases
- Script-based import process (reproducible)

## Migration Path

### For Development/Testing

1. **Generate SQL file:**
   ```bash
   python scripts/convert_postcodes_to_sql.py
   ```

2. **Import into database:**
   ```bash
   mysql -u username -p database_name < init-db/postcodes.sql
   ```

### For Production

The SQL file can be imported as part of the deployment process:
- The script drops the `postcodes` table if it exists
- Creates the new table with proper schema
- Inserts all 2.7M postcode records

**Note:** The legacy `postcode6` and `postcode8` tables are retained for backward compatibility but are no longer used by the API.

## Testing

After migration, test the `/api/v1/locations/search` endpoint with:

1. **Full postcode searches:**
   - `AB1 0AA` - Should return exact match from `postcodes` table
   - `SW1A 1AA` - London postcode

2. **Prefix searches:**
   - `AB1` - Should return multiple matches
   - `SW1` - London area

3. **6-character postcodes:**
   - `AB10AA` (no space) - Should match from both `postcode6` and `postcodes`

4. **Verify coordinates:**
   - Check that returned lat/lon values are reasonable for UK (49-61°N, 8-2°W)
   - Postcode6 results should now use converted OSGB coordinates

## Rollback

If issues arise, the API can be quickly rolled back:

1. Revert changes to `api/api/v1/endpoints/locations.py`
2. Revert changes to `api/crud/locations.py`
3. Keep the new `Postcode` model (harmless if unused)

The `postcode8` table is not dropped, so legacy functionality remains available.

## Future Improvements

1. **Remove Legacy Tables**: Once confidence is established, remove `postcode8` table
2. **Update postcode6**: Consider migrating `postcode6` to use NSPL data as well
3. **Regular Updates**: Set up process for importing new NSPL releases (quarterly)
4. **Spatial Indexing**: Consider adding spatial indexes for distance queries

## Related Files

- `scripts/convert_postcodes_to_sql.py` - Conversion script
- `init-db/postcodes.sql` - Generated SQL file (94 MB)
- `docs/database/POSTCODES_CONVERSION.md` - Detailed conversion documentation
- `res/NSPL_Online_latest_Centroids_.csv` - Source CSV file (200+ MB)

