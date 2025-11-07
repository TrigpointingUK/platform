# Interactive Map Testing Guide

This document provides testing procedures for the interactive trigpoint map features.

## Development Server Testing

### Prerequisites

1. Start the development server:
```bash
cd web
npm run dev
```

2. Ensure the backend API is running (if testing with real data)

3. Have Auth0 credentials configured in `.env.local`

## Test Cases

### 1. Detail Map (`/trig/:trigId`)

**Test Steps:**
1. Navigate to any trigpoint detail page (e.g., `/trig/1`)
2. Verify the map displays in the card below the trigpoint info
3. Check that the trigpoint marker is centered on the map
4. Verify the marker icon matches the physical type and condition
5. Click the marker to see popup with trigpoint info
6. Use tileset selector to switch map layers
7. Verify map renders correctly at detail zoom level (14)

**Expected Results:**
- Map loads without errors
- Marker is properly centered
- Icon color reflects condition (green/yellow/red/grey)
- Popup shows correct trigpoint information
- Tileset switching works smoothly
- Map is responsive (resizes with window)

### 2. Exploration Map (`/map`)

**Test Steps:**
1. Navigate to `/map` route
2. Verify full-screen map loads
3. Check that sidebar is visible with filters
4. Verify trigpoints load within viewport

**Expected Results:**
- Map fills the available height (minus header)
- Sidebar is visible on desktop, collapsible on mobile
- Trigpoints appear as markers or heatmap
- No console errors

### 3. Filtering

**Physical Type Filtering:**
1. On `/map`, uncheck all physical types except "Pillar"
2. Verify only pillar markers display
3. Re-check other types and verify they appear
4. Clear filters and verify all types show

**Exclude Found Filtering:**
1. Ensure you're logged in
2. Check "Exclude trigpoints I've found"
3. Verify the checkbox appears only when authenticated
4. Note: Full functionality requires backend API support

**URL Persistence:**
1. Select filters on `/map`
2. Copy the URL
3. Paste URL in new tab
4. Verify filters are preserved

### 4. Tileset Switching

**Test All Tilesets:**
1. On `/map`, open tileset selector
2. Switch to each available tileset:
   - OpenStreetMap (default)
   - OS Landranger (if configured)
   - OS Digital (if configured)
   - ESRI Satellite
   - OpenTopoMap
3. Verify tiles load correctly for each
4. Check for any tile loading errors in console

**Preference Persistence:**
1. Select a non-default tileset
2. Reload the page
3. Verify the selected tileset is still active

### 5. Icon Color Modes

**Condition Mode:**
1. Select "Condition" mode
2. Verify icon colors match:
   - Green = Good condition
   - Yellow = Damaged
   - Red = Missing/Possibly Missing
   - Grey = Unknown
3. Expand legend and verify it matches

**User Log Mode:**
1. Select "My Logs" mode
2. Verify mode switches (currently shows grey for all)
3. Note: Full functionality requires backend API support

### 6. Rendering Modes

**Auto Mode:**
1. Start with all physical types selected
2. Verify marker rendering shows count: "Showing markers (N ≤ 500)"
3. Zoom out to include more trigpoints
4. When count exceeds 500, verify switch to heatmap: "Showing heatmap (N > 500)"

**Manual Modes:**
1. Select "Markers" mode
2. Verify individual markers always display (may be slow with many points)
3. Select "Heatmap" mode
4. Verify heatmap always displays
5. Return to "Auto" mode

### 7. Location Services

**Grant Permission:**
1. Click location button
2. Grant location permission when prompted
3. Verify map centers on your location
4. Verify zoom level increases

**Deny Permission:**
1. Clear location permission
2. Click location button
3. Deny permission
4. Verify error message displays
5. Verify message disappears after 3 seconds

**No Geolocation Support:**
1. Test in browser with geolocation disabled
2. Verify appropriate error message

### 8. Map Interactions

**Panning:**
1. Click and drag the map
2. Verify smooth panning
3. Verify trigpoints update after pan (with debounce)

**Zooming:**
1. Use zoom controls (+/-)
2. Use mouse wheel (desktop)
3. Use pinch gesture (mobile)
4. Verify trigpoints update after zoom

**Marker Clicks:**
1. In marker mode, click individual markers
2. Verify popup appears
3. Click "View Details" link
4. Verify navigation to trigpoint detail page

### 9. Responsive Design

**Desktop (>1024px):**
1. Verify sidebar is visible
2. Verify sidebar is fixed width (320px)
3. Verify map fills remaining space

**Tablet (768px - 1024px):**
1. Verify sidebar is still visible
2. Verify map is responsive
3. Test sidebar toggle (mobile menu button)

**Mobile (<768px):**
1. Verify sidebar is hidden by default
2. Click menu button to show sidebar
3. Verify sidebar overlays map
4. Click X to close sidebar
5. Verify filters work on mobile

### 10. Navigation Links

**Header Link:**
1. Click "Map" in header (desktop)
2. Verify navigation to `/map`
3. Test mobile menu "Map" link

**Trigpoint Detail Links:**
1. From any trigpoint page, click "View on Interactive Map"
2. Verify navigation to `/map` with lat/lon/trig parameters
3. Verify map centers on trigpoint
4. Click "View Nearby Trigpoints"
5. Verify navigation to `/trigs` with filters

### 11. URL Parameters

**Test Parameter Handling:**
1. Visit `/map?lat=54.5&lon=-2.0`
2. Verify map centers on specified location
3. Visit `/map?types=Pillar,FBM`
4. Verify only Pillar and FBM types are selected
5. Visit `/map?excludeFound=true`
6. Verify exclude found checkbox is checked (if authenticated)

### 12. Performance

**Marker Rendering:**
1. Zoom to area with many trigpoints
2. Monitor performance in browser dev tools
3. Verify no significant lag or frame drops
4. Check for memory leaks during extended use

**Tile Loading:**
1. Pan rapidly across map
2. Verify tiles load quickly
3. Check for any tile loading failures
4. Verify browser caches tiles (check Network tab)

**Data Fetching:**
1. Monitor Network tab during map use
2. Verify debounced requests (not too frequent)
3. Check request payload sizes
4. Verify response caching (2-minute stale time)

### 13. Error Handling

**Network Errors:**
1. Disable network in dev tools
2. Verify appropriate error message
3. Re-enable network
4. Verify map recovers

**Tile Loading Errors:**
1. Use invalid tile server URL
2. Verify fallback behavior or error message
3. Restore valid tile server URL

**API Errors:**
1. Stop backend API server
2. Verify error message displays
3. Restart API server
4. Verify map recovers

## Browser Compatibility

Test on the following browsers:

- [ ] Chrome (latest)
- [ ] Firefox (latest)
- [ ] Safari (latest)
- [ ] Edge (latest)
- [ ] Mobile Safari (iOS)
- [ ] Chrome Mobile (Android)

## Accessibility

- [ ] Tab navigation works through map controls
- [ ] Keyboard shortcuts work (if implemented)
- [ ] Screen reader announces map changes
- [ ] High contrast mode displays correctly
- [ ] Focus indicators are visible

## Known Issues

Document any issues found during testing here:

1. User Log color mode shows all grey (awaiting backend API)
2. OS Landranger/OS Digital require configuration
3. Heatmap doesn't support individual trigpoint clicks
4. Large marker counts (>1000) may cause performance issues

## Performance Benchmarks

Record performance metrics:

| Test Case | Trigpoints | Render Time | Memory Usage |
|-----------|-----------|-------------|--------------|
| Small area | <100 | ___ ms | ___ MB |
| Medium area | 100-500 | ___ ms | ___ MB |
| Large area (markers) | 500-1000 | ___ ms | ___ MB |
| Large area (heatmap) | >1000 | ___ ms | ___ MB |

## Manual Testing Checklist

- [ ] All test cases above completed
- [ ] No console errors during normal use
- [ ] No network errors (except when testing error handling)
- [ ] Maps display correctly on all tested browsers
- [ ] Mobile experience is smooth and usable
- [ ] Filters persist correctly
- [ ] Navigation links work as expected
- [ ] Performance is acceptable for typical use cases

## Automated Testing

For future implementation:

- Unit tests for icon mapping utilities
- Unit tests for config modules
- Integration tests for map components
- E2E tests for critical user flows
- Performance regression tests

## Sign-off

- [ ] Developer testing complete
- [ ] QA testing complete
- [ ] User acceptance testing complete
- [ ] Performance testing complete
- [ ] Accessibility testing complete
- [ ] Ready for deployment

