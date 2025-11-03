# Global Search Implementation Summary

## Overview

Implemented a smart global search box in the page header that searches across trigpoints, locations (postcodes, towns, grid references, coordinates), and users, with intelligent routing based on the result type.

## Changes Made

### 1. API Updates

#### Schema (`api/schemas/locations.py`)
- Added `id` field (optional) to `LocationSearchResult` for routing to specific resources
- Updated type description to include `user`

#### Endpoint (`api/api/v1/endpoints/locations.py`)
- Added import for `user_crud` module
- Updated `/v1/locations/search` endpoint to search for users by name
- Added `id` field to trigpoint results (trig ID for routing)
- Added `id` field to user results (user ID for routing)
- User results use a default UK center point (54.0, -2.0) since users don't have specific locations
- Updated docstring to mention user search capability

### 2. Frontend Components

#### New Component: GlobalSearch (`web/src/components/layout/GlobalSearch.tsx`)
Created a new search component with the following features:

**UX Features:**
- Dropdown appears when user types 2+ characters
- Debounced search (300ms delay)
- Click outside to close
- Form submission on Enter key
- Loading states
- Empty state messaging
- Icons for each result type (📍🏘️📮🗺️🌐👤)

**Routing Logic:**
1. **Trigpoint results** → Navigate to `/trig/:trigid`
2. **User results** → Navigate to `/profile/:userid`
3. **Location results** (postcode, town, gridref, latlon) → Navigate to `/trigs` with location parameters
4. **Enter without selection** → Navigate to `/trigs` with query as location name

**Props:**
- `className`: Optional styling classes
- `placeholder`: Custom placeholder text
- `onSearch`: Callback when search completes (for closing mobile menu)

#### Updated Component: Header (`web/src/components/layout/Header.tsx`)
- Imported `GlobalSearch` component
- Replaced desktop search input with `<GlobalSearch />`
- Replaced mobile search input with `<GlobalSearch />`
- Added `handleSearchComplete` callback to close mobile menu on search
- Consistent placeholder text: "Search trigs, places, users..."

### 3. API Behavior

The `/v1/locations/search?q=<query>` endpoint now returns up to 10 results (configurable) from:

1. **Lat/Lon coordinates** - if query matches coordinate format
2. **OSGB grid references** - if query matches grid ref format
3. **Trigpoints** - by name or waypoint (limit 5)
4. **Towns** - by name (limit 5)
5. **Postcodes** - from both postcode6 and postcodes tables (limit 5 each)
6. **Users** - by username (limit 5)

All results include:
- `type`: Result category
- `name`: Display name
- `lat`, `lon`: Coordinates (or default for users)
- `description`: Additional info
- `id`: Resource ID (for trigpoints and users)

## User Experience Flow

### Desktop Usage
1. User types in search box in header
2. Dropdown appears below with matching results
3. Results show icon, name, description, and coordinates
4. User can:
   - Click a result → Routes appropriately
   - Press Enter → Goes to /trigs page with query

### Mobile Usage
1. User opens mobile menu
2. Search box appears at top
3. Same dropdown behavior as desktop
4. After selecting result or pressing Enter, mobile menu closes

## Example Searches

### Trigpoint Search
**Query:** `Kinder`
**Results:** Trigpoints with "Kinder" in name/waypoint
**Action:** Click → Navigate to `/trig/12345`

### Location Search
**Query:** `PE27 4`
**Results:** Postcodes starting with "PE27 4"
**Action:** Click → Navigate to `/trigs?lat=52.329&lon=-0.057&location=PE27+4AA`

### User Search
**Query:** `john`
**Results:** Users with "john" in username
**Action:** Click → Navigate to `/profile/auth0|123456`

### Grid Reference
**Query:** `SK 123 456`
**Results:** Parsed grid reference
**Action:** Click → Navigate to `/trigs` with calculated coordinates

### Enter Without Selection
**Query:** `Manchester`
**Action:** Press Enter → Navigate to `/trigs?lat=54.0&lon=-2.0&location=Manchester`

## Technical Details

### Debouncing
- 300ms delay before API call (implemented in `useLocationSearch` hook)
- Prevents excessive API calls while typing

### Caching
- Location search results cached for 1 hour
- Reduces server load for common searches

### Accessibility
- `aria-label`, `aria-autocomplete`, `aria-controls`, `aria-expanded` attributes
- Semantic HTML with proper form elements
- Keyboard navigation support (Enter to submit)

### Mobile Optimization
- Search dropdown has `z-50` to appear above other content
- Mobile menu closes automatically after search
- Touch-friendly button sizes

## Files Modified

1. `api/schemas/locations.py` - Added `id` field to schema
2. `api/api/v1/endpoints/locations.py` - Added user search, IDs
3. `web/src/components/layout/GlobalSearch.tsx` - **NEW** component
4. `web/src/components/layout/Header.tsx` - Integrated GlobalSearch

## Testing Checklist

- [x] Search for trigpoints by name
- [x] Search for trigpoints by waypoint
- [x] Search for postcodes (with and without space)
- [x] Search for towns
- [x] Search for users by username
- [x] Enter coordinates (lat/lon format)
- [x] Enter OSGB grid references
- [x] Press Enter without selecting (default to /trigs)
- [x] Click outside to close dropdown
- [x] Mobile menu closes after search
- [x] Desktop and mobile layouts work correctly
- [x] Loading states display properly
- [x] No results message shows when appropriate

## Future Enhancements

Potential improvements:
1. Keyboard navigation (arrow keys to select results)
2. Recent searches memory
3. Search history
4. Fuzzy matching for typos
5. Search result ranking/relevance scoring
6. Highlighting matched text in results
7. Category filtering (search only trigs, only users, etc.)

