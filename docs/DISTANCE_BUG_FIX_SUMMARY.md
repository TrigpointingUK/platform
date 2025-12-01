# Distance Calculation Bug Fix - Summary

## Problem

When searching for trigpoints by grid reference (e.g., "SD 65113 72134"), the distance calculations were off by **~5.7 kilometers**. The user reported that a trigpoint at virtually the same location (SD 65114 72131, just 3 metres away) was shown as 5.7km away.

## Root Cause

The issue was **NOT** with the distance calculation algorithm (haversine formula is fine). The problem was with coordinate conversion from OSGB36 grid references to WGS84 lat/lon.

In `api/crud/locations.py`, the `osgb_to_wgs84()` function used a crude linear approximation:

```python
# OLD (broken) code:
def osgb_to_wgs84(eastings: int, northings: int) -> Tuple[float, float]:
    # Simplified conversion - this is an approximation
    lat0 = 49.0
    lon0 = -2.0
    lat_per_m = 1.0 / 111320.0  # meters per degree latitude
    lon_per_m = 1.0 / (111320.0 * 0.7)  # adjusted for UK latitude
    
    e = eastings - 400000
    n = northings - -100000
    lat = lat0 + n * lat_per_m
    lon = lon0 + e * lon_per_m
    return lat, lon
```

This gave coordinates that were **5.74km off** from the true location.

## The Fix

Replaced the crude approximation with a proper Helmert transformation that was already implemented in `api/utils/geodesy.py`:

```python
# NEW (correct) code:
from api.utils.geodesy import osgb_to_wgs84 as geodesy_osgb_to_wgs84

def osgb_to_wgs84(eastings: int, northings: int) -> Tuple[float, float]:
    """
    Convert OSGB36 eastings/northings to WGS84 lat/lon using Helmert transformation.
    
    Uses the proper implementation from api.utils.geodesy which includes:
    - Inverse Transverse Mercator projection (OSGB36 grid → OSGB36 lat/lon)
    - Full 7-parameter Helmert transformation (OSGB36 → WGS84)
    - Accuracy within metres across all of GB
    """
    return geodesy_osgb_to_wgs84(eastings, northings)
```

## Results

### Before Fix
- Search: SD 65113 72134
- Converted to (WRONG): 54.139544, -2.447705
- Burton-in-Lonsdale at: 54.143817, -2.535533 (correct)
- **Calculated distance: 5.74km ❌**

### After Fix
- Search: SD 65113 72134
- Converted to (CORRECT): 54.143844, -2.535549
- Burton-in-Lonsdale at: 54.143817, -2.535533 (correct)
- **Calculated distance: 3.2m ✓**

## Impact

This fix affects:
1. **Grid reference searches** - Users searching by grid ref (e.g., "SD 65113 72134") now get accurate results
2. **Postcode lookups** - Postcodes using OSGB coordinates now convert correctly
3. **Distance-based filtering** - All distance calculations from grid references now accurate

## Files Changed

- `api/crud/locations.py` - Replaced `osgb_to_wgs84()` implementation

## Testing

✓ All existing geodesy tests pass (6/6)
✓ Grid reference parsing verified with test case from bug report
✓ Complete flow tested: input → conversion → distance calculation
✓ Coordinate conversion error reduced from 5.74km to < 5m

## Date

2025-12-01
