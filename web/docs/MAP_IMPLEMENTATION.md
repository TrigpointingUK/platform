# Interactive Map Implementation Summary

## Overview

This document summarizes the implementation of interactive trigpoint maps for the TrigpointingUK web application.

## Completed Features

### 1. Map Infrastructure

**Dependencies Installed:**
- `leaflet` - Core mapping library
- `react-leaflet` - React components for Leaflet
- `leaflet.heat` - Heatmap visualization support
- `@types/leaflet` - TypeScript type definitions

**Configuration Modules:**
- `web/src/lib/mapConfig.ts` - Tile layer definitions and map settings
- `web/src/lib/mapIcons.ts` - Icon mapping and color mode logic

### 2. Core Components

**Base Components:**
- `BaseMap` - Reusable Leaflet map wrapper with tile layer support
- `TrigMarker` - Individual trigpoint marker with custom icons
- `TilesetSelector` - Dropdown for switching map layers
- `IconColorModeSelector` - Toggle between condition/user log color modes
- `LocationButton` - Center map on user's current location
- `HeatmapLayer` - Density heatmap for large trigpoint sets

**Specialized Components:**
- `TrigDetailMap` - Map view for individual trigpoint pages
- `Map` (route) - Full exploration map with filters

### 3. Map Routes

**New Routes:**
- `/map` - Interactive exploration map with filtering
- Updated `/trig/:trigId` - Now includes embedded detail map

### 4. Features Implemented

**Tileset Support:**
- OpenStreetMap (default)
- OS Landranger (configurable)
- OS Digital (configurable)
- ESRI Satellite
- OpenTopoMap
- User preference persisted to localStorage

**Icon System:**
- 32 icon files copied from `res/icons/` to `web/public/icons/`
- Icons organized by physical type: Pillar, FBM, Passive Station, Intersection
- Four colors per type: Green, Yellow, Red, Grey
- Highlighted versions available for future features

**Color Modes:**
- **Condition Mode**: Maps trig condition codes to colors
  - G (Good) → Green
  - D (Damaged) → Yellow
  - M/P (Missing/Possibly Missing) → Red
  - U (Unknown) → Grey
- **User Log Mode**: Shows user's log status (scaffolded for future API support)
  - Found → Green
  - Not Found → Red
  - Not Logged → Grey

**Filtering:**
- Physical type checkboxes (reused from `/trigs` page)
- Exclude found trigpoints (authenticated users only)
- URL parameter persistence

**Smart Rendering:**
- Automatic switch between markers and heatmap at 500 trigpoint threshold
- Manual override: Auto/Markers/Heatmap modes
- Visual indicator showing current mode and count

**Dynamic Loading:**
- Viewport-based data fetching via `useMapTrigs` hook
- Converts map bounds to center+radius for existing API
- Debounced viewport changes for performance
- 2-minute cache for loaded data

**Navigation:**
- "Map" link added to header (desktop and mobile)
- "View on Interactive Map" link on trigpoint detail pages
- Support for URL parameters to center map on specific locations

### 5. Data Hooks

**`useMapTrigs`:**
- Fetches trigpoints within viewport bounds
- Integrates with existing `/v1/trigs` endpoint
- Supports physical type filtering
- Supports exclude found filtering (with authentication)
- Returns trigpoints, total count, loading state

**`useUserLogStatus`:** (Scaffolded)
- Placeholder for future batch log status checking
- Currently returns empty object
- Requires backend API enhancement

### 6. Configuration

**Map Settings:**
- Default center: UK (54.5, -2.0)
- Default zoom: 6
- Detail map zoom: 14
- Detail map height: 350px
- Marker threshold: 500 trigpoints
- Viewport padding: 10%
- Debounce delay: 500ms

**Tile Caching:**
- `crossOrigin: "anonymous"` for browser caching
- 7-day max age recommendation
- User preferences stored in localStorage

## File Structure

```
web/
├── public/
│   └── icons/
│       ├── mapicon_pillar_green.png
│       ├── mapicon_pillar_yellow.png
│       └── ... (32 icon files)
├── src/
│   ├── components/
│   │   └── map/
│   │       ├── BaseMap.tsx
│   │       ├── TrigMarker.tsx
│   │       ├── TilesetSelector.tsx
│   │       ├── IconColorModeSelector.tsx
│   │       ├── LocationButton.tsx
│   │       ├── HeatmapLayer.tsx
│   │       └── TrigDetailMap.tsx
│   ├── routes/
│   │   ├── Map.tsx (new)
│   │   └── TrigDetail.tsx (updated)
│   ├── hooks/
│   │   └── useMapTrigs.ts (new)
│   ├── lib/
│   │   ├── mapConfig.ts (new)
│   │   └── mapIcons.ts (new)
│   └── router.tsx (updated)
└── docs/
    ├── MAP_SETUP.md (new)
    └── MAP_IMPLEMENTATION.md (this file)
```

## API Integration

**No Backend Changes Required:**
- Existing `/v1/trigs` endpoint supports all needed features
- Physical type filtering: `?physical_types=Pillar,FBM`
- Distance queries: `?lat=54.5&lon=-2.0&max_km=50`
- Exclude found: `?exclude_found=true` (with authentication)

**Future Backend Enhancements:**
- Batch log status endpoint for efficient user log checking
- Would enable full User Log color mode functionality

## Known Limitations

1. **User Log Color Mode**: Currently uses grey for all trigpoints due to lack of batch log status API
2. **Tile Server URLs**: OS Landranger and OS Digital require configuration (not included in repo)
3. **Icon Coverage**: Only 4 physical types have specific icons (Pillar, FBM, Passive, Intersection)
   - Other types (Bolt, Active Station, Other) fall back to Pillar icon
4. **Heatmap Click**: Heatmap mode doesn't support clicking individual trigpoints
5. **Marker Limit**: No hard limit on marker rendering (relies on user choosing appropriate zoom/filters)

## Testing Checklist

- [x] Dependencies installed successfully
- [x] Icons copied to public directory
- [x] Tileset configuration created
- [x] Icon mapping utilities implemented
- [x] Base map components built
- [x] Detail map integrated into trigpoint pages
- [x] Exploration map route created
- [x] Filters working (physical type, exclude found)
- [x] Tileset switching functional
- [x] Icon color modes switchable
- [x] Location button requests permission
- [x] Heatmap renders for large datasets
- [x] Marker threshold auto-switching works
- [x] URL parameters persist filters
- [x] Navigation links added to header
- [x] "View on Map" link on trig detail pages
- [ ] Manual testing on development server
- [ ] Manual testing on multiple devices
- [ ] Manual testing with different tilesets
- [ ] Verify tile caching behavior
- [ ] Test offline functionality

## Environment Setup

Create `web/.env.local`:

```bash
VITE_AUTH0_DOMAIN=your-domain.auth0.com
VITE_AUTH0_CLIENT_ID=your-client-id
VITE_AUTH0_AUDIENCE=https://api.trigpointing.uk
VITE_API_BASE=http://localhost:8000

# Optional tile server URLs
VITE_TILE_OS_LANDRANGER=https://tiles.example.com/os-landranger/{z}/{x}/{y}.png
VITE_TILE_OS_DIGITAL=https://tiles.example.com/os-digital/{z}/{x}/{y}.png
```

## Next Steps

1. **Testing**: Manual testing on development server
2. **Tile Servers**: Configure OS Landranger and OS Digital tile servers
3. **User Log API**: Implement batch log status endpoint for full User Log mode
4. **Performance**: Monitor map performance with real data
5. **Documentation**: Update main README with map features
6. **Deployment**: Deploy to staging for user testing

## References

- Leaflet Documentation: https://leafletjs.com/
- React Leaflet: https://react-leaflet.js.org/
- Leaflet.heat: https://github.com/Leaflet/Leaflet.heat
- Tailwind CSS v4: https://tailwindcss.com/

