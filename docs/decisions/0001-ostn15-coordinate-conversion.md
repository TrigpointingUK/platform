# ADR 0001: OSTN15/OSGM15 Coordinate Conversion

## Status

Accepted

## Date

2026-01-11

## Context

The TrigpointingUK admin interface allows administrators to edit trigpoint coordinates in both WGS84 (GPS) and OSGB36 (British National Grid) coordinate systems. When editing coordinates in one system, the values need to be automatically converted to the other system.

### Current Implementation

The current implementation uses a **7-parameter Helmert transformation** implemented in:
- Backend: `api/utils/geodesy.py` 
- Frontend: `web/src/lib/coordinates.ts`

This transformation uses fixed rotation and translation parameters to convert between datums.

### Problems with Helmert Transformation

1. **Accuracy**: The Helmert transformation is only accurate to approximately **5-10 metres** across Great Britain. This is insufficient for trigpoint data where positions are known to centimetre accuracy.

2. **Inconsistent Results**: A trigpoint recorded at SD 65113 72134 was showing as 5.7km away from the correct location due to coordinate conversion errors.

3. **No Height Conversion**: The database stores two different height values:
   - `wgs_height`: Ellipsoidal height (above WGS84 ellipsoid)
   - `osgb_height`: Orthometric height (above Ordnance Datum Newlyn / sea level)
   
   The difference between these (the geoid-ellipsoid separation) varies from ~45m in SE England to ~57m in NW Scotland. The current system does not convert heights, leading to potential data inconsistencies.

### OSTN15 and OSGM15

Ordnance Survey provides two definitive transformation models for Great Britain:

- **OSTN15** (Ordnance Survey National Transformation 2015): A "rubber-sheet" transformation that provides sub-centimetre horizontal accuracy by interpolating corrections from a dense grid of control points.

- **OSGM15** (Ordnance Survey Geoid Model 2015): A geoid model that provides the separation between the WGS84 ellipsoid and Ordnance Datum Newlyn, enabling accurate height conversions.

## Decision

We will replace the Helmert transformation with **pyproj** using OSTN15 and OSGM15 grid files for coordinate conversion.

### Implementation Approach

1. **Use pyproj** (already in `requirements.txt` at v3.7.2) which interfaces with the PROJ library
2. **Download grid files at Docker build time** (~5.5MB total):
   - `uk_os_OSTN15_NTv2_OSGBtoETRS.tif` (~4MB) - horizontal transformation
   - `uk_os_OSGM15_GB.tif` (~1.5MB) - geoid model for height
3. **Disable runtime network access** (`PROJ_NETWORK=OFF`) to ensure no external dependencies
4. **Add startup verification** that confirms OSTN15 is loaded and working
5. **Create new API endpoint** for coordinate conversion, moving the computation to the backend
6. **Update frontend** to call the API instead of performing client-side conversion

### Why pyproj over convertbng?

| Criteria | pyproj | convertbng |
|----------|--------|------------|
| Horizontal (OSTN15) | ✅ | ✅ |
| Vertical (OSGM15) | ✅ | ❌ |
| Already installed | ✅ | ❌ |
| Industry standard | ✅ | Limited |

Since we need **both** horizontal and vertical transformations, and pyproj is already a dependency, it is the clear choice.

## Consequences

### Positive

1. **Sub-centimetre horizontal accuracy** instead of 5-10m errors
2. **Accurate height conversion** between ellipsoidal and orthometric heights
3. **Single source of truth** for coordinate conversion (backend API)
4. **No client-side computation** - simpler frontend, consistent results
5. **Offline operation** - no runtime dependency on external URLs

### Negative

1. **Docker image size increase** of ~5.5MB for grid files
2. **API latency** - coordinate conversion now requires network round-trip
3. **Backend dependency** - frontend cannot convert coordinates if API is unavailable

### Mitigations

- Grid files are downloaded at build time, not runtime
- 500ms debounce on frontend prevents excessive API calls
- Startup check fails fast if OSTN15 is not properly loaded

## EPSG Codes Used

| Description | EPSG Code |
|-------------|-----------|
| WGS84 (2D) | EPSG:4326 |
| WGS84 + ellipsoidal height (3D) | EPSG:4979 |
| British National Grid (2D) | EPSG:27700 |
| British National Grid + ODN height (3D) | EPSG:7405 |

## References

- [OS OSTN15 Technical Information](https://www.ordnancesurvey.co.uk/documents/resources/guide-coordinate-systems-great-britain.pdf)
- [PROJ Grid Files CDN](https://cdn.proj.org/)
- [pyproj Documentation](https://pyproj4.github.io/pyproj/)

