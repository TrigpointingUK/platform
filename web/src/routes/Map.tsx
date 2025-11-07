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
import { PhysicalTypeFilter } from "../components/trigs/PhysicalTypeFilter";
import Layout from "../components/layout/Layout";
import Spinner from "../components/ui/Spinner";
import { useMapTrigsWithProgress, type MapBounds } from "../hooks/useMapTrigsWithProgress";
import {
  getPreferredTileLayer,
  MAP_CONFIG,
} from "../lib/mapConfig";
import { getPreferredIconColorMode, type IconColorMode } from "../lib/mapIcons";
import { Menu, X } from "lucide-react";

// All physical types
const ALL_PHYSICAL_TYPES = [
  "Pillar",
  "Bolt",
  "FBM",
  "Passive Station",
  "Active Station",
  "Intersection",
  "Other",
];

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

export default function Map() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth0();
  
  // State
  const [tileLayerId, setTileLayerId] = useState(getPreferredTileLayer());
  const [iconColorMode, setIconColorMode] = useState<IconColorMode>(getPreferredIconColorMode());
  const [selectedPhysicalTypes, setSelectedPhysicalTypes] = useState<string[]>(() => {
    const types = searchParams.get("types");
    return types ? types.split(",") : ALL_PHYSICAL_TYPES;
  });
  const [excludeFound, setExcludeFound] = useState<boolean>(
    () => searchParams.get("excludeFound") === "true"
  );
  const [mapBounds, setMapBounds] = useState<MapBounds | undefined>(undefined);
  const [mapInstance, setMapInstance] = useState<LeafletMap | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [renderMode, setRenderMode] = useState<'auto' | 'markers' | 'heatmap'>('auto');
  const [currentZoom, setCurrentZoom] = useState<number>(MAP_CONFIG.defaultZoom);
  
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
    isLoading,
    loadingProgress,
    error,
  } = useMapTrigsWithProgress({
    bounds: mapBounds,
    excludeFound,
    enabled: !!mapBounds,
    zoom: currentZoom,
  });
  
  // Client-side filtering by physical type
  const trigpoints = useMemo(() => {
    // If all types selected, no need to filter
    if (selectedPhysicalTypes.length === ALL_PHYSICAL_TYPES.length) {
      return allTrigsData;
    }
    
    // Filter by selected physical types
    return allTrigsData.filter(trig => 
      selectedPhysicalTypes.includes(trig.physical_type)
    );
  }, [allTrigsData, selectedPhysicalTypes]);
  
  // Determine whether to show markers or heatmap based on zoom level
  const shouldShowHeatmap = useMemo(() => {
    if (renderMode === 'markers') return false;
    if (renderMode === 'heatmap') return true;
    // Auto mode: use heatmap when zoomed out (zoom < 10) OR too many trigpoints
    const isZoomedOut = currentZoom < 10;
    const tooManyMarkers = trigpoints.length > MAP_CONFIG.markerThreshold;
    return isZoomedOut || tooManyMarkers;
  }, [renderMode, trigpoints.length, currentZoom]);
  
  // Update URL params when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    
    if (selectedPhysicalTypes.length !== ALL_PHYSICAL_TYPES.length) {
      params.set("types", selectedPhysicalTypes.join(","));
    }
    
    if (excludeFound) {
      params.set("excludeFound", "true");
    }
    
    setSearchParams(params, { replace: true });
  }, [selectedPhysicalTypes, excludeFound, setSearchParams]);
  
  // Handle bounds change with debouncing
  const handleBoundsChange = useCallback((bounds: MapBounds) => {
    setMapBounds(bounds);
  }, []);
  
  const handleTogglePhysicalType = useCallback((type: string) => {
    setSelectedPhysicalTypes((prev) => {
      if (prev.includes(type)) {
        return prev.filter((t) => t !== type);
      } else {
        return [...prev, type];
      }
    });
  }, []);
  
  const handleClearFilters = useCallback(() => {
    setSelectedPhysicalTypes(ALL_PHYSICAL_TYPES);
    setExcludeFound(false);
  }, []);
  
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
            
            {/* Physical type filter */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Physical Types
              </label>
              <PhysicalTypeFilter
                selectedTypes={selectedPhysicalTypes}
                onToggleType={handleTogglePhysicalType}
              />
            </div>
            
            {/* Exclude found checkbox */}
            {isAuthenticated && (
              <div className="mb-4">
                <label className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={excludeFound}
                    onChange={(e) => setExcludeFound(e.target.checked)}
                    className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                  />
                  <span>Exclude trigpoints I've found</span>
                </label>
              </div>
            )}
            
            {/* Icon color mode selector */}
            <div className="mb-4">
              <IconColorModeSelector
                value={iconColorMode}
                onChange={setIconColorMode}
                showLegend={true}
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
              <label className="block text-sm font-medium text-gray-700 mb-2">
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
                  title="Always show individual markers"
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
                      Showing heatmap (zoom: {currentZoom.toFixed(1)}, {trigpoints.length} trigpoints)
                    </span>
                  ) : (
                    <span className="text-trig-green-600">
                      Showing markers (zoom: {currentZoom.toFixed(1)}, {trigpoints.length} trigpoints)
                    </span>
                  )}
                </div>
              )}
            </div>
            
            {/* Clear filters button */}
            <button
              type="button"
              onClick={handleClearFilters}
              className="w-full text-sm text-blue-600 hover:text-blue-800 font-medium py-2 border border-blue-600 rounded hover:bg-blue-50 transition-colors"
            >
              Clear filters
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
                  <div className="font-semibold">Showing {trigpoints.length} trigpoints</div>
                  <div className="text-xs text-gray-500 mt-1">
                    {allTrigsData.length} loaded, {totalCount} in database
                  </div>
                  {selectedPhysicalTypes.length < ALL_PHYSICAL_TYPES.length && (
                    <div className="text-xs text-blue-600 mt-1">
                      Filtered by type (client-side)
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
            
            {/* Render trigpoint markers or heatmap */}
            {shouldShowHeatmap ? (
              <HeatmapLayer trigpoints={trigpoints} />
            ) : (
              <>
                {trigpoints.map((trig) => (
                  <TrigMarker
                    key={trig.id}
                    trig={trig}
                    colorMode={iconColorMode}
                    logStatus={null} // TODO: Implement user log status
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
              className="absolute top-4 left-4 z-[1000] bg-white hover:bg-gray-50 p-3 rounded-lg shadow-md"
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

