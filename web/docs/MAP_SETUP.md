# Interactive Map Setup Guide

This document explains how to configure and use the interactive trigpoint mapping features.

## Overview

The web application includes two interactive map views:

1. **Detail Map** (`/trig/:trigId`) - Shows a single trigpoint location
2. **Exploration Map** (`/map`) - Full interactive map with filtering and thousands of markers

## Features

- **Multiple Tile Layers**: Switch between OS Landranger, Mapnik, OS Digital, ESRI Satellite, and OpenTopoMap
- **Custom Trigpoint Icons**: Icons vary by physical type (Pillar, FBM, Passive Station, Intersection)
- **Color Modes**: 
  - Condition mode: Green (good), Yellow (damaged), Red (missing), Grey (unknown)
  - User Log mode: Green (found), Red (not found), Grey (not logged)
- **Filtering**: Filter by physical type, exclude already-found trigpoints
- **Smart Rendering**: Auto-switches between individual markers and heatmap based on trigpoint count
- **Location Services**: Center map on your current location
- **Responsive Design**: Works on desktop, tablet, and mobile

## Configuration

### Environment Variables

Create a `.env.local` file in the `web/` directory with the following variables:

```bash
# Required
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id
VITE_AUTH0_AUDIENCE=https://api.trigpointing.uk
VITE_API_BASE=http://localhost:8000

# Optional - Map Tile Servers
VITE_TILE_OS_LANDRANGER=https://tiles.example.com/os-landranger/{z}/{x}/{y}.png
VITE_TILE_OS_DIGITAL=https://tiles.example.com/os-digital/{z}/{x}/{y}.png
VITE_TILE_ESRI_SATELLITE=https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}
```

### OS Landranger Tiles

OS Landranger tiles require licensing from Ordnance Survey. Options:

1. **Self-hosted tile server**: Use tools like TileServer GL or MapProxy
2. **Commercial tile service**: Subscribe to a mapping provider
3. **Fallback**: Use OpenStreetMap (default, no configuration needed)

The application will gracefully fall back to OpenStreetMap if OS tiles are not configured.

### Icon Files

Trigpoint icons are located in `web/public/icons/` and follow the naming convention:

```
mapicon_{type}_{color}.png
mapicon_{type}_{color}_h.png  (highlighted version)
```

Types: `pillar`, `fbm`, `passive`, `intersected`
Colors: `green`, `yellow`, `red`, `grey`

## Map Components

### BaseMap

Reusable Leaflet map wrapper with configurable tile layers.

```tsx
import BaseMap from '../components/map/BaseMap';

<BaseMap
  center={[54.5, -2.0]}
  zoom={10}
  height={400}
  tileLayerId="osm"
>
  {/* Map content */}
</BaseMap>
```

### TrigMarker

Individual trigpoint marker with custom icon and popup.

```tsx
import TrigMarker from '../components/map/TrigMarker';

<TrigMarker
  trig={trigData}
  colorMode="condition"
  highlighted={false}
/>
```

### TilesetSelector

Dropdown to switch between available tile layers.

```tsx
import TilesetSelector from '../components/map/TilesetSelector';

<TilesetSelector
  value={tileLayerId}
  onChange={setTileLayerId}
/>
```

### IconColorModeSelector

Toggle between condition and user log color modes.

```tsx
import IconColorModeSelector from '../components/map/IconColorModeSelector';

<IconColorModeSelector
  value={iconColorMode}
  onChange={setIconColorMode}
  showLegend={true}
/>
```

### LocationButton

Button to center the map on user's current location.

```tsx
import LocationButton from '../components/map/LocationButton';

<LocationButton
  onLocationFound={(lat, lon) => {
    map.setView([lat, lon], 13);
  }}
/>
```

### HeatmapLayer

Density heatmap for large numbers of trigpoints.

```tsx
import HeatmapLayer from '../components/map/HeatmapLayer';

<HeatmapLayer trigpoints={trigpoints} />
```

## Usage

### Detail Map

The detail map is automatically rendered on trigpoint pages at `/trig/:trigId`. It shows:

- Single trigpoint marker
- Tileset selector
- Fixed zoom level (14)
- Condition-based icon colors

### Exploration Map

Access the exploration map at `/map`. Features include:

- **Sidebar Filters**:
  - Physical type checkboxes
  - Exclude found trigpoints (authenticated users)
  - Icon color mode selector
  - Tileset selector
  - Render mode (Auto/Markers/Heatmap)

- **Map Controls**:
  - Location center button
  - Zoom controls
  - Pan/drag navigation

- **Rendering Modes**:
  - **Auto**: Switches between markers and heatmap at 500 trigpoint threshold
  - **Markers**: Always show individual markers
  - **Heatmap**: Always show density heatmap

### URL Parameters

The map route supports URL parameters:

- `lat` - Latitude to center map
- `lon` - Longitude to center map
- `trig` - Trigpoint ID to highlight
- `types` - Comma-separated physical types to filter
- `excludeFound` - Set to "true" to exclude found trigpoints

Example:
```
/map?lat=54.5&lon=-2.0&types=Pillar,FBM&excludeFound=true
```

## Performance

### Tile Caching

Tiles are cached by the browser with `crossOrigin="anonymous"` to enable offline use.

### Marker Threshold

The map automatically switches to heatmap mode when displaying more than 500 trigpoints. This threshold can be adjusted in `web/src/lib/mapConfig.ts`:

```ts
export const MAP_CONFIG = {
  markerThreshold: 500, // Adjust this value
  // ...
};
```

### Viewport Loading

The map only loads trigpoints within the current viewport bounds, improving performance for large datasets.

## Troubleshooting

### Icons Not Displaying

1. Verify icons are copied to `web/public/icons/`
2. Check browser console for 404 errors
3. Ensure icon filenames match the expected format

### Tiles Not Loading

1. Check `.env.local` tile server URLs
2. Verify CORS headers on tile server
3. Check browser console for network errors
4. Fall back to OpenStreetMap tiles

### Map Performance

1. Reduce marker threshold if map is slow
2. Use heatmap mode for large datasets
3. Clear browser cache if tiles are stale
4. Limit physical type filters to reduce trigpoint count

## Future Enhancements

Potential improvements for future development:

- Service worker for offline tile access
- Clustering markers instead of heatmap
- User log status integration for color modes
- Batch log status endpoint for efficient checking
- Route planning between trigpoints
- Custom marker highlighting
- Printable map views

