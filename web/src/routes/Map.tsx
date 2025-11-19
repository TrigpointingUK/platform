import { useState, useEffect, useCallback, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useMap } from "react-leaflet";
import { useAuth0 } from "@auth0/auth0-react";
import type { Map as LeafletMap } from "leaflet";
import BaseMap from "../components/map/BaseMap";
import TrigMarker from "../components/map/TrigMarker";
import HeatmapLayer from "../components/map/HeatmapLayer";
import TilesetSelector from "../components/map/TilesetSelector";
import IconColorModeSelector from "../components/map/IconColorModeSelector";
import LocationButton from "../components/map/LocationButton";
import { StatusFilter } from "../components/trigs/StatusFilter";
import { ColorFilter } from "../components/trigs/ColorFilter";
import Layout from "../components/layout/Layout";
import Spinner from "../components/ui/Spinner";
import { useMapTrigsWithProgress, type MapBounds } from "../hooks/useMapTrigsWithProgress";
import { useMapTrigsGeoJSON, type GeoJSONTrig } from "../hooks/useMapTrigsGeoJSON";
import { useUserProfile } from "../hooks/useUserProfile";
import { useUserLoggedTrigs } from "../hooks/useUserLoggedTrigs";
import type { UserLogStatus } from "../lib/mapIcons";
import {
  getPreferredTileLayer,
  MAP_CONFIG,
  DEFAULT_TILE_LAYER,
} from "../lib/mapConfig";
import {
  getPreferredIconColorMode,
  type IconColorMode,
  getUserLogColor,
  getConditionColor,
  type IconColor
} from "../lib/mapIcons";
import { Menu, X } from "lucide-react";

// All status levels (IDs)
const ALL_STATUSES = [10, 20, 30, 40, 50, 60];

// Status ID to name mapping (for API keys)
const STATUS_NAMES: Record<number, string> = {
  10: "pillar",
  20: "major_mark",
  30: "minor_mark",
  40: "intersected",
  50: "user_added",
  60: "controversial",
};

// Status ID to display name mapping
const STATUS_DISPLAY_NAMES: Record<number, string> = {
  10: "Pillar",
  20: "Major mark",
  30: "Minor mark",
  40: "Intersected",
  50: "User Added",
  60: "Controversial",
};

const ALL_ICON_COLORS: IconColor[] = ["green", "yellow", "red", "grey"];
const USER_LOG_ICON_COLORS: IconColor[] = ["green", "yellow", "red"];

/**
 * Component to track map viewport changes
 */
function MapViewportTracker({ 
  onBoundsChange,
  onZoomChange 
}: { 
  onBoundsChange: (bounds: MapBounds) => void;
  onZoomChange: (zoom: number) => void;
}) {
  const map = useMap();
  
  useEffect(() => {
    const updateBounds = () => {
      const bounds = map.getBounds();
      onBoundsChange({
        north: bounds.getNorth(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        west: bounds.getWest(),
      });
      onZoomChange(map.getZoom());
    };
    
    // Initial bounds
    updateBounds();
    
    // Listen to map movements
    map.on('moveend', updateBounds);
    map.on('zoomend', updateBounds);
    
    return () => {
      map.off('moveend', updateBounds);
      map.off('zoomend', updateBounds);
    };
  }, [map, onBoundsChange, onZoomChange]);
  
  return null;
}

/**
 * Component to invalidate map size when sidebar opens/closes
 */
function MapSizeInvalidator({ sidebarOpen }: { sidebarOpen: boolean }) {
  const map = useMap();
  
  useEffect(() => {
    // Wait for CSS transition to complete, then invalidate map size
    const timer = setTimeout(() => {
      map.invalidateSize();
    }, 300); // Match the transition-all duration-300 from sidebar
    
    return () => clearTimeout(timer);
  }, [sidebarOpen, map]);
  
  return null;
}

export default function Map() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth0();
  
  // Fetch user profile to get status_max preference
  const { data: userProfile } = useUserProfile("me");
  
  // Fetch user's logged trigpoints for icon coloring
  const { data: loggedTrigsMap } = useUserLoggedTrigs();

  // Derive preferred statuses from user preferences (defaults to Minor mark max)
  const preferredStatuses = useMemo(() => {
    const userStatusMax = userProfile?.prefs?.status_max ?? 30;
    return ALL_STATUSES.filter((status) => status <= userStatusMax);
  }, [userProfile]);
  
  // Data source mode: always use geojson (now includes all status levels)
  const [dataSource] = useState<'geojson' | 'paginated'>('geojson');
  
  // State
  const [tileLayerId, setTileLayerId] = useState(getPreferredTileLayer());
  const [iconColorMode, setIconColorMode] = useState<IconColorMode>(getPreferredIconColorMode());
  const [selectedStatuses, setSelectedStatuses] = useState<number[]>(() => {
    const statuses = searchParams.get("statuses");
    if (statuses) return statuses.split(",").map(Number);
    
    return preferredStatuses;
  });
  const [selectedColors, setSelectedColors] = useState<IconColor[]>(() => [...ALL_ICON_COLORS]);
  const [excludeFound, setExcludeFound] = useState<boolean>(
    () => searchParams.get("excludeFound") === "true"
  );
  const [mapBounds, setMapBounds] = useState<MapBounds | undefined>(undefined);
  const [mapInstance, setMapInstance] = useState<LeafletMap | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [renderMode, setRenderMode] = useState<'auto' | 'markers' | 'heatmap'>('auto');
  const [currentZoom, setCurrentZoom] = useState<number>(MAP_CONFIG.defaultZoom);
  const maxTrigpoints = 50000; // Always load all trigpoints
  
  // Track if we've initialized statuses from user preferences
  const [statusesInitialized, setStatusesInitialized] = useState(false);
  
  // Get center from URL params or use default
  const initialCenter: [number, number] = useMemo(() => {
    const lat = parseFloat(searchParams.get("lat") || "");
    const lon = parseFloat(searchParams.get("lon") || "");
    
    if (lat && lon) {
      return [lat, lon];
    }
    
    return [MAP_CONFIG.defaultCenter.lat, MAP_CONFIG.defaultCenter.lng];
  }, [searchParams]);
  
  const initialZoom = useMemo(() => {
    return searchParams.get("trig") ? 14 : MAP_CONFIG.defaultZoom;
  }, [searchParams]);
  
  // Fetch trigpoints for current viewport
  // Note: physical_types filter NOT applied in API - we filter client-side
  const {
    data: allTrigsData,
    totalCount,
    isLoading: isPaginatedLoading,
    loadingProgress,
    error: paginatedError,
  } = useMapTrigsWithProgress({
    bounds: mapBounds,
    excludeFound,
    enabled: dataSource === 'paginated' && !!mapBounds,
    zoom: currentZoom,
    maxTrigpoints,
  });
  
  // Fetch GeoJSON data (Pillar + FBM only)
  const {
    data: geojsonData,
    isLoading: isGeoJSONLoading,
    error: geoJsonError,
  } = useMapTrigsGeoJSON({
    enabled: dataSource === 'geojson',
    limit: maxTrigpoints === 50000 ? null : maxTrigpoints, // null = no limit
  });
  
  // Convert GeoJSON features to Trig format for rendering
  const geojsonTrigs = useMemo(() => {
    if (!geojsonData) return [];
    
    // Debug: log the structure we received
    console.log('GeoJSON data keys:', Object.keys(geojsonData));
    
    const trigs: typeof allTrigsData = [];
    
    // Iterate through all selected statuses
    for (const statusId of selectedStatuses) {
      const statusKey = STATUS_NAMES[statusId];
      if (!statusKey) continue;
      
      // Safely access the collection
      const collection = geojsonData[statusKey as keyof typeof geojsonData];
      
      // Check if collection exists and has features array
      if (!collection || typeof collection === 'string') {
        console.log(`Skipping ${statusKey} - not a collection:`, typeof collection);
        continue;
      }
      if (!collection.features || !Array.isArray(collection.features)) {
        console.warn(`No features array for status ${statusKey}:`, collection);
        continue;
      }
      
      console.log(`Processing ${statusKey}: ${collection.features.length} features`);
      
      collection.features.forEach((feature: GeoJSONTrig) => {
        // Skip features with missing critical data
        if (!feature.properties?.id || !feature.geometry?.coordinates?.[0] || !feature.geometry?.coordinates?.[1]) {
          console.warn('Skipping feature with missing data:', feature);
          return;
        }
        
        trigs.push({
          id: feature.properties.id,
          waypoint: `TP${feature.properties.id.toString().padStart(4, '0')}`,
          name: feature.properties.name || "",
          physical_type: feature.properties.physical_type || "Unknown",
          condition: feature.properties.condition || "U",
          wgs_lat: feature.geometry.coordinates[1].toString(),
          wgs_long: feature.geometry.coordinates[0].toString(),
          osgb_gridref: feature.properties.osgb_gridref || "",
          status_name: STATUS_DISPLAY_NAMES[statusId] || "",
        });
      });
    }
    
    return trigs;
  }, [geojsonData, selectedStatuses]);
  
  // Client-side filtering by status (for paginated mode - not currently used)
  const paginatedTrigs = useMemo(() => {
    // If all statuses selected, no need to filter
    if (selectedStatuses.length === ALL_STATUSES.length) {
      return allTrigsData;
    }
    
    // Filter by selected statuses (would need status_id in data)
    return allTrigsData;
  }, [allTrigsData, selectedStatuses]);
  
  // Determine which data to use based on mode
  const trigpoints = dataSource === 'geojson' ? geojsonTrigs : paginatedTrigs;
  const isLoading = dataSource === 'geojson' ? isGeoJSONLoading : isPaginatedLoading;
  const error = dataSource === 'geojson' ? geoJsonError : paginatedError;
  
  // Helper function to get log status for a trigpoint
  const getLogStatus = useCallback((trigId: number): UserLogStatus | null => {
    // Only return log status if using userLog color mode
    if (iconColorMode !== 'userLog' || !loggedTrigsMap) {
      return null;
    }
    
    const condition = loggedTrigsMap.get(trigId);
    return condition 
      ? { hasLogged: true, condition }
      : { hasLogged: false };
  }, [iconColorMode, loggedTrigsMap]);
  
  // Helper function to get the color for a trigpoint based on current mode
  const getTrigColor = useCallback((trig: typeof trigpoints[0]): IconColor => {
    if (iconColorMode === 'condition') {
      return getConditionColor(trig.condition);
    } else {
      // userLog mode
      const logStatus = getLogStatus(trig.id);
      if (!logStatus) return 'grey';
      return getUserLogColor(logStatus);
    }
  }, [iconColorMode, getLogStatus]);

  const colorFilteredTrigpoints = useMemo(() => {
    if (selectedColors.length === 0) {
      return [];
    }

    const allColorsSelected =
      selectedColors.length === ALL_ICON_COLORS.length &&
      ALL_ICON_COLORS.every((color) => selectedColors.includes(color));

    if (allColorsSelected) {
      return trigpoints;
    }

    return trigpoints.filter((trig) => selectedColors.includes(getTrigColor(trig)));
  }, [trigpoints, selectedColors, getTrigColor]);
  
  // Calculate physical type counts from filtered trigpoints
  const physicalTypeCounts = useMemo(() => {
    const counts: Record<string, number> = {};

    for (const trig of colorFilteredTrigpoints) {
      const type = trig.physical_type || "Unknown";
      counts[type] = (counts[type] || 0) + 1;
    }

    return counts;
  }, [colorFilteredTrigpoints]);
  
  // Filter trigpoints by viewport bounds for performance
  const visibleTrigpoints = useMemo(() => {
    if (!mapBounds) return colorFilteredTrigpoints;
    
    return colorFilteredTrigpoints.filter((trig) => {
      const lat = parseFloat(trig.wgs_lat);
      const lon = parseFloat(trig.wgs_long);
      
      return (
        lat >= mapBounds.south &&
        lat <= mapBounds.north &&
        lon >= mapBounds.west &&
        lon <= mapBounds.east
      );
    });
  }, [colorFilteredTrigpoints, mapBounds]);
  
  // Determine whether to show markers or heatmap based on visible trigpoint count
  const shouldShowHeatmap = useMemo(() => {
    if (renderMode === 'markers') return false;
    if (renderMode === 'heatmap') return true;
    // Auto mode: use heatmap when more than 1000 markers would be visible in viewport
    const tooManyVisibleMarkers = visibleTrigpoints.length > 1000;
    return tooManyVisibleMarkers;
  }, [renderMode, visibleTrigpoints.length]);
  
  // Initialize selected statuses from user preference when profile loads
  useEffect(() => {
    // Only apply user preference if:
    // 1. No URL params are set
    // 2. We haven't already initialized from preferences
    // 3. We have a preferred status list computed
    if (!searchParams.get("statuses") && !statusesInitialized && preferredStatuses.length > 0) {
      setSelectedStatuses([...preferredStatuses]);
      setStatusesInitialized(true);
    }
  }, [preferredStatuses, searchParams, statusesInitialized]);
  
  // Handle color selection when switching between Condition and My Logs modes
  useEffect(() => {
    if (iconColorMode === 'condition') {
      setSelectedColors(() => [...ALL_ICON_COLORS]);
    } else {
      setSelectedColors(() => [...USER_LOG_ICON_COLORS]);
    }
  }, [iconColorMode]);
  
  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    
    if (selectedStatuses.length !== ALL_STATUSES.length) {
      params.set("statuses", selectedStatuses.join(","));
    }
    
    if (excludeFound) {
      params.set("excludeFound", "true");
    }
    
    setSearchParams(params, { replace: true });
  }, [selectedStatuses, excludeFound, setSearchParams]);
  
  // Handle bounds change with debouncing
  const handleBoundsChange = useCallback((bounds: MapBounds) => {
    setMapBounds(bounds);
  }, []);
  
  const handleToggleStatus = useCallback((statusId: number) => {
    setSelectedStatuses((prev) => {
      if (prev.includes(statusId)) {
        return prev.filter((s) => s !== statusId);
      } else {
        return [...prev, statusId];
      }
    });
  }, []);
  
  const handleToggleColor = useCallback((color: IconColor) => {
    setSelectedColors((prev) => {
      if (prev.includes(color)) {
        return prev.filter((c) => c !== color);
      } else {
        return [...prev, color];
      }
    });
  }, []);
  
  const handleClearFilters = useCallback(() => {
    setSelectedStatuses([...preferredStatuses]);
    setSelectedColors(() => [...ALL_ICON_COLORS]);
    setExcludeFound(false);
    setRenderMode('auto');
    setTileLayerId(DEFAULT_TILE_LAYER);
    
    // Reset map to show whole UK
    if (mapInstance) {
      mapInstance.setView(
        [MAP_CONFIG.defaultCenter.lat, MAP_CONFIG.defaultCenter.lng],
        MAP_CONFIG.defaultZoom
      );
    }
  }, [mapInstance, preferredStatuses]);
  
  return (
    <Layout>
      <div className="flex h-[calc(100vh-4rem-7rem)] relative -mx-4 -mb-6">
        {/* Sidebar */}
        <div
          className={`${
            isSidebarOpen ? 'w-80' : 'w-0'
          } transition-all duration-300 bg-white border-r border-gray-200 overflow-hidden flex-shrink-0`}
        >
          <div className="p-4 h-full overflow-y-auto">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900">Map Filters</h2>
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="lg:hidden p-1 hover:bg-gray-100 rounded"
              >
                <X size={20} />
              </button>
            </div>
            
            {/* Status filter */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status Levels
              </label>
              <StatusFilter
                selectedStatuses={selectedStatuses}
                onToggleStatus={handleToggleStatus}
              />
            </div>
            
            {/* Color filter */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Marker Colors
              </label>
              <ColorFilter
                selectedColors={selectedColors}
                onToggleColor={handleToggleColor}
              />
            </div>
            
            {/* Icon color mode selector */}
            <div className="mb-4">
              <IconColorModeSelector
                value={iconColorMode}
                onChange={setIconColorMode}
                showLegend={true}
                isAuthenticated={isAuthenticated}
              />
            </div>
            
            {/* Tileset selector */}
            <div className="mb-4">
              <TilesetSelector
                value={tileLayerId}
                onChange={setTileLayerId}
              />
            </div>
            
            {/* Render mode selector */}
            <div className="mb-4">
              <div className="bg-white rounded-lg shadow-md p-3">
                <label className="block text-xs font-medium text-gray-700 mb-2">
                  Display Mode
                </label>
                <div className="flex gap-1">
                  <button
                    onClick={() => setRenderMode('auto')}
                    className={`flex-1 px-2 py-1.5 text-xs rounded transition-colors ${
                      renderMode === 'auto'
                        ? 'bg-trig-green-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    title="Auto-switch between markers and heatmap based on count"
                  >
                    Auto
                  </button>
                  <button
                    onClick={() => setRenderMode('markers')}
                    className={`flex-1 px-2 py-1.5 text-xs rounded transition-colors ${
                      renderMode === 'markers'
                        ? 'bg-trig-green-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    title="Always show individual markers (may be slow for large datasets)"
                  >
                    Markers
                  </button>
                  <button
                    onClick={() => setRenderMode('heatmap')}
                    className={`flex-1 px-2 py-1.5 text-xs rounded transition-colors ${
                      renderMode === 'heatmap'
                        ? 'bg-trig-green-600 text-white'
                        : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
                    }`}
                    title="Always show density heatmap"
                  >
                    Heatmap
                  </button>
                </div>
                {renderMode === 'auto' && (
                  <div className="mt-2 text-xs text-gray-600">
                    {shouldShowHeatmap ? (
                      <span className="text-amber-600">
                        Showing heatmap ({visibleTrigpoints.length} visible, {colorFilteredTrigpoints.length} total)
                      </span>
                    ) : (
                      <span className="text-trig-green-600">
                        Showing {visibleTrigpoints.length} markers ({colorFilteredTrigpoints.length} total)
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>
            
            {/* Reset map button */}
            <button
              type="button"
              onClick={handleClearFilters}
              className="w-full text-sm text-trig-green-700 hover:text-trig-green-900 font-medium py-2 border border-trig-green-700 rounded hover:bg-trig-green-50 transition-colors"
            >
              Reset map
            </button>
            
            {/* Results count */}
            <div className="mt-4 text-sm text-gray-600 p-3 bg-gray-50 rounded">
              {isLoading ? (
                <div>
                  <div className="text-sm font-semibold mb-2">Loading trigpoints...</div>
                  <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                    <div
                      className="bg-trig-green-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${loadingProgress}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500">{loadingProgress.toFixed(0)}%</div>
                </div>
              ) : (
                <div>
                  <div className="font-semibold">Showing {colorFilteredTrigpoints.length} trigpoints</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {dataSource === 'geojson' ? (
                      <>
                        Comprising: {geojsonData ? (
                          <>
                            {Object.entries(physicalTypeCounts)
                              .sort(([, countA], [, countB]) => countB - countA)
                              .map(([type, count], index, arr) => (
                                <span key={type}>
                                  {count} {type}{count !== 1 ? 's' : ''}
                                  {index < arr.length - 1 ? ', ' : ''}
                                </span>
                              ))
                            }
                          </>
                        ) : 'Loading...'}
                      </>
                    ) : (
                      <>
                        {allTrigsData.length} loaded, {totalCount} in database (zoom: {currentZoom.toFixed(1)})
                      </>
                    )}
                  </div>
                  {selectedStatuses.length < ALL_STATUSES.length && (
                    <div className="text-xs text-blue-600 mt-1">
                      Filtered by status (client-side)
                    </div>
                  )}
                  {iconColorMode === 'condition' && selectedColors.length !== ALL_ICON_COLORS.length && (
                    <div className="text-xs text-blue-600 mt-1">
                      Filtered by marker colours
                    </div>
                  )}
                </div>
              )}
            </div>
          </div>
        </div>
        
        {/* Map */}
        <div className="flex-1 relative">
          <BaseMap
            center={initialCenter}
            zoom={initialZoom}
            height="100%"
            tileLayerId={tileLayerId}
            onMapReady={setMapInstance}
          >
            <MapViewportTracker 
              onBoundsChange={handleBoundsChange}
              onZoomChange={setCurrentZoom}
            />
            <MapSizeInvalidator sidebarOpen={isSidebarOpen} />
            
            {/* Render trigpoint markers or heatmap */}
            {shouldShowHeatmap ? (
              <HeatmapLayer trigpoints={colorFilteredTrigpoints} />
            ) : (
              <>
                {visibleTrigpoints.map((trig) => (
                  <TrigMarker
                    key={trig.id}
                    trig={trig}
                    colorMode={iconColorMode}
                    logStatus={getLogStatus(trig.id)}
                  />
                ))}
              </>
            )}
          </BaseMap>
          
          {/* Map controls overlay */}
          <div className="absolute top-4 right-4 z-[1000] flex flex-col gap-2">
            {mapInstance && (
              <LocationButton
                map={mapInstance}
                onLocationFound={(lat, lon) => {
                  mapInstance.setView([lat, lon], 13);
                }}
              />
            )}
          </div>
          
          {/* Toggle sidebar button (mobile) */}
          {!isSidebarOpen && (
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="absolute top-4 left-20 z-[1000] bg-white hover:bg-gray-50 p-3 rounded-lg shadow-md"
            >
              <Menu size={24} className="text-gray-700" />
            </button>
          )}
          
          {/* Loading overlay */}
          {isLoading && (
            <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-[1000] bg-white px-6 py-4 rounded-lg shadow-lg min-w-[300px]">
              <div className="flex items-center gap-2 mb-3">
                <Spinner size="sm" />
                <span className="text-sm text-gray-700 font-semibold">Loading trigpoints...</span>
              </div>
              <div className="w-full bg-gray-200 rounded-full h-2 mb-1">
                <div
                  className="bg-trig-green-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${loadingProgress}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 text-center">{loadingProgress.toFixed(0)}%</div>
            </div>
          )}
          
          {/* Error message */}
          {error && (
            <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-[1000] bg-red-50 border border-red-200 text-red-700 px-4 py-2 rounded-lg shadow-md max-w-md">
              <p className="text-sm">Failed to load trigpoints: {error.message}</p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}

