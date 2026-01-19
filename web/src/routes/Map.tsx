import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useMap } from "react-leaflet";
import { useAuth0 } from "@auth0/auth0-react";
import type { Map as LeafletMap } from "leaflet";
import BaseMap from "../components/map/BaseMap";
import TrigMarker from "../components/map/TrigMarker";
import HeatmapLayer from "../components/map/HeatmapLayer";
import AreaBoundaryLayer from "../components/map/AreaBoundaryLayer";
import TilesetSelector from "../components/map/TilesetSelector";
import IconColorModeSelector from "../components/map/IconColorModeSelector";
import LocationButton from "../components/map/LocationButton";
import { useAreaBoundary } from "../hooks/useAreaBoundary";
import { StatusFilter } from "../components/trigs/StatusFilter";
import { ColorFilter } from "../components/trigs/ColorFilter";
import Layout from "../components/layout/Layout";
import Spinner from "../components/ui/Spinner";
import {
  useMapTrigsWithProgress,
  type MapBounds,
} from "../hooks/useMapTrigsWithProgress";
import {
  useMapTrigsGeoJSON,
  type GeoJSONTrig,
} from "../hooks/useMapTrigsGeoJSON";
import { useUserProfile } from "../hooks/useUserProfile";
import { useUserLoggedTrigs } from "../hooks/useUserLoggedTrigs";
import type { UserLogStatus } from "../lib/mapIcons";
import {
  getPreferredTileLayer,
  MAP_CONFIG,
  DEFAULT_TILE_LAYER,
  getTileLayer,
  calculateProjectionZoom,
} from "../lib/mapConfig";
import {
  getPreferredIconColorMode,
  type IconColorMode,
  getUserLogColor,
  getConditionColor,
  type IconColor,
} from "../lib/mapIcons";
import { Menu, X, List } from "lucide-react";

// All status levels (IDs) - maps to trig_category.sort_order
const ALL_STATUSES = [10, 20, 30, 40, 50, 60];

// Status ID to API key mapping (for GeoJSON collections)
// These map to trig_category.code as returned by the API
const STATUS_NAMES: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "SURVEY_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

// Reverse mapping: category code to status ID
const CATEGORY_CODE_TO_STATUS_ID: Record<string, number> = {
  PILLAR: 10,
  FBM: 20,
  SURVEY_MARK: 30,
  INTERSECTED: 40,
  ACTIVE: 50,
  OTHER: 60,
};

// Status ID to display name mapping (from trig_category.name)
const STATUS_DISPLAY_NAMES: Record<number, string> = {
  10: "Pillar",
  20: "FBM",
  30: "Survey mark",
  40: "Intersected",
  50: "Active station",
  60: "Other",
};

const ALL_ICON_COLORS: IconColor[] = ["green", "yellow", "red", "grey"];
const USER_LOG_ICON_COLORS: IconColor[] = ["green", "yellow", "red"];

/**
 * Component to track map viewport changes
 */
function MapViewportTracker({
  onBoundsChange,
  onZoomChange,
  onCenterChange,
}: {
  onBoundsChange: (bounds: MapBounds) => void;
  onZoomChange: (zoom: number) => void;
  onCenterChange: (lat: number, lon: number) => void;
}) {
  const map = useMap();

  useEffect(() => {
    const updateViewport = () => {
      const bounds = map.getBounds();
      onBoundsChange({
        north: bounds.getNorth(),
        south: bounds.getSouth(),
        east: bounds.getEast(),
        west: bounds.getWest(),
      });
      onZoomChange(map.getZoom());
      const center = map.getCenter();
      onCenterChange(center.lat, center.lng);
    };

    // Initial viewport
    updateViewport();

    // Listen to map movements
    map.on("moveend", updateViewport);
    map.on("zoomend", updateViewport);

    return () => {
      map.off("moveend", updateViewport);
      map.off("zoomend", updateViewport);
    };
  }, [map, onBoundsChange, onZoomChange, onCenterChange]);

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

  // Fetch user profile to get default_groups preference
  const { data: userProfile } = useUserProfile("me");

  // Fetch user's logged trigpoints for icon coloring
  const { data: loggedTrigsMap } = useUserLoggedTrigs();

  // Derive preferred statuses from user preferences
  // Uses default_categories (list of category codes) from ui_prefs
  const preferredStatuses = useMemo(() => {
    const defaultCategories = userProfile?.prefs?.ui_prefs?.default_categories;
    if (defaultCategories && defaultCategories.length > 0) {
      return defaultCategories
        .map((code: string) => CATEGORY_CODE_TO_STATUS_ID[code])
        .filter((id: number | undefined): id is number => id !== undefined);
    }
    
    // Default is PILLAR + FBM only for guests and users without preferences
    return [10, 20]; // PILLAR, FBM
  }, [userProfile]);

  // Data source mode: always use geojson (now includes all status levels)
  const [dataSource] = useState<"geojson" | "paginated">("geojson");

  // State
  const [tileLayerId, setTileLayerId] = useState(getPreferredTileLayer());
  const [iconColorMode, setIconColorMode] = useState<IconColorMode>(
    getPreferredIconColorMode(),
  );
  const [selectedStatuses, setSelectedStatuses] = useState<number[]>(() => {
    const statuses = searchParams.get("statuses");
    if (statuses) return statuses.split(",").map(Number);

    return preferredStatuses;
  });
  // Derive initial color selection based on icon mode
  const [selectedColors, setSelectedColors] = useState<IconColor[]>(() => [
    ...ALL_ICON_COLORS,
  ]);
  const [excludeFound, setExcludeFound] = useState<boolean>(
    () => searchParams.get("excludeFound") === "true",
  );
  const [mapBounds, setMapBounds] = useState<MapBounds | undefined>(undefined);
  const [mapInstance, setMapInstance] = useState<LeafletMap | null>(null);
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const [renderMode, setRenderMode] = useState<"auto" | "markers" | "heatmap">(
    "auto",
  );
  const [currentZoom, setCurrentZoom] = useState<number>(
    MAP_CONFIG.defaultZoom,
  );
  // Track current center for URL persistence
  const [currentCenter, setCurrentCenter] = useState<{
    lat: number;
    lon: number;
  } | null>(null);
  const maxTrigpoints = 50000; // Always load all trigpoints

  // Track if we've initialized statuses from user preferences (use ref to avoid triggering re-renders)
  const statusesInitializedRef = useRef(false);

  // Parse area_id from URL params for boundary display
  const areaId = useMemo(() => {
    const areaIdParam = searchParams.get("area_id");
    return areaIdParam ? parseInt(areaIdParam, 10) : undefined;
  }, [searchParams]);

  // Fetch area boundary when area_id is provided
  const { data: areaBoundary, isLoading: isLoadingBoundary } =
    useAreaBoundary(areaId);

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
    // Check for zoom in URL params first
    const zoomParam = parseFloat(searchParams.get("zoom") || "");
    if (!isNaN(zoomParam) && zoomParam > 0) {
      return zoomParam;
    }
    // Fall back to trig-specific zoom or default
    return searchParams.get("trig") ? 14 : MAP_CONFIG.defaultZoom;
  }, [searchParams]);

  // Active zoom for BaseMap - starts with initial zoom, updated when projection changes
  const [activeZoom, setActiveZoom] = useState<number>(initialZoom);

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
    enabled: dataSource === "paginated" && !!mapBounds,
    zoom: currentZoom,
    maxTrigpoints,
  });

  // Fetch GeoJSON data (Pillar + FBM only)
  const {
    data: geojsonData,
    isLoading: isGeoJSONLoading,
    error: geoJsonError,
  } = useMapTrigsGeoJSON({
    enabled: dataSource === "geojson",
    limit: maxTrigpoints === 50000 ? null : maxTrigpoints, // null = no limit
  });

  // Convert GeoJSON features to Trig format for rendering
  const geojsonTrigs = useMemo(() => {
    if (!geojsonData) return [];

    // Debug: log the structure we received
    console.log("GeoJSON data keys:", Object.keys(geojsonData));

    const trigs: typeof allTrigsData = [];

    // Iterate through all selected statuses
    for (const statusId of selectedStatuses) {
      const statusKey = STATUS_NAMES[statusId];
      if (!statusKey) continue;

      // Safely access the collection
      const collection = geojsonData[statusKey as keyof typeof geojsonData];

      // Check if collection exists and is a FeatureCollection (not a string or warning)
      if (!collection || typeof collection === "string") {
        console.log(
          `Skipping ${statusKey} - not a collection:`,
          typeof collection,
        );
        continue;
      }

      // Type guard: check it's a FeatureCollection with features array
      if (
        !("type" in collection) ||
        collection.type !== "FeatureCollection" ||
        !("features" in collection) ||
        !Array.isArray(collection.features)
      ) {
        console.warn(`No features array for status ${statusKey}:`, collection);
        continue;
      }

      console.log(
        `Processing ${statusKey}: ${collection.features.length} features`,
      );

      (collection.features as GeoJSONTrig[]).forEach((feature: GeoJSONTrig) => {
        // Skip features with missing critical data
        if (
          !feature.properties?.id ||
          !feature.geometry?.coordinates?.[0] ||
          !feature.geometry?.coordinates?.[1]
        ) {
          console.warn("Skipping feature with missing data:", feature);
          return;
        }

        trigs.push({
          id: feature.properties.id,
          waypoint: `TP${feature.properties.id.toString().padStart(4, "0")}`,
          name: feature.properties.name || "",
          physical_type: feature.properties.physical_type || "Unknown",
          condition: feature.properties.condition || "U",
          wgs_lat: feature.geometry.coordinates[1].toString(),
          wgs_long: feature.geometry.coordinates[0].toString(),
          osgb_gridref: feature.properties.osgb_gridref || "",
          status_name: STATUS_DISPLAY_NAMES[statusId] || "",
          type_name: feature.properties.type_name,
          category_code: feature.properties.category_code,
          category_name: feature.properties.category_name,
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
  const trigpoints = dataSource === "geojson" ? geojsonTrigs : paginatedTrigs;
  const isLoading =
    dataSource === "geojson" ? isGeoJSONLoading : isPaginatedLoading;
  const error = dataSource === "geojson" ? geoJsonError : paginatedError;

  // Helper function to get log status for a trigpoint
  const getLogStatus = useCallback(
    (trigId: number): UserLogStatus | null => {
      // Only return log status if using userLog color mode
      if (iconColorMode !== "userLog" || !loggedTrigsMap) {
        return null;
      }

      const condition = loggedTrigsMap.get(trigId);
      return condition ? { hasLogged: true, condition } : { hasLogged: false };
    },
    [iconColorMode, loggedTrigsMap],
  );

  // Helper function to get the color for a trigpoint based on current mode
  const getTrigColor = useCallback(
    (trig: (typeof trigpoints)[0]): IconColor => {
      if (iconColorMode === "condition") {
        return getConditionColor(trig.condition);
      } else {
        // userLog mode
        const logStatus = getLogStatus(trig.id);
        if (!logStatus) return "grey";
        return getUserLogColor(logStatus);
      }
    },
    [iconColorMode, getLogStatus],
  );

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

    return trigpoints.filter((trig) =>
      selectedColors.includes(getTrigColor(trig)),
    );
  }, [trigpoints, selectedColors, getTrigColor]);

  // Calculate type counts from filtered trigpoints
  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {};

    for (const trig of colorFilteredTrigpoints) {
      // Prefer type_name, fall back to physical_type
      const type = trig.type_name || trig.physical_type || "Unknown";
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
    if (renderMode === "markers") return false;
    if (renderMode === "heatmap") return true;
    // Auto mode: use heatmap when more than 1000 markers would be visible in viewport
    const tooManyVisibleMarkers = visibleTrigpoints.length > 1000;
    return tooManyVisibleMarkers;
  }, [renderMode, visibleTrigpoints.length]);

  // Initialize selected statuses from user preference when profile loads (once)
  // This is responding to async user profile data, not derived state
  useEffect(() => {
    // Only apply user preference if:
    // 1. No URL params are set
    // 2. We haven't already initialized from preferences
    // 3. We have a preferred status list computed
    if (
      !searchParams.get("statuses") &&
      !statusesInitializedRef.current &&
      preferredStatuses.length > 0
    ) {
      statusesInitializedRef.current = true;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time initialization from async user profile
      setSelectedStatuses([...preferredStatuses]);
    }
  }, [preferredStatuses, searchParams]);

  // Track previous icon color mode to detect changes and avoid cascading renders
  const prevIconColorModeRef = useRef(iconColorMode);

  // Handle color selection when switching between Condition and My Logs modes
  // This responds to user interaction (mode toggle), not derived state
  useEffect(() => {
    // Only update if mode actually changed (prevents initial render trigger)
    if (prevIconColorModeRef.current === iconColorMode) {
      return;
    }
    prevIconColorModeRef.current = iconColorMode;

    const newColors =
      iconColorMode === "condition"
        ? [...ALL_ICON_COLORS]
        : [...USER_LOG_ICON_COLORS];
    // eslint-disable-next-line react-hooks/set-state-in-effect -- Responding to user mode toggle
    setSelectedColors(newColors);
  }, [iconColorMode]);

  // Update URL params when filters or viewport change (preserve area_id if present)
  // Using replace: true to avoid polluting browser history with every pan/zoom
  useEffect(() => {
    const params = new URLSearchParams();

    // Preserve area_id if it was passed in
    if (areaId !== undefined) {
      params.set("area_id", areaId.toString());
    }

    if (selectedStatuses.length !== ALL_STATUSES.length) {
      params.set("statuses", selectedStatuses.join(","));
    }

    if (excludeFound) {
      params.set("excludeFound", "true");
    }

    // Persist viewport state (lat, lon, zoom) for back navigation
    // Only update if we have actual viewport data (not initial render)
    if (currentCenter && currentZoom) {
      params.set("lat", currentCenter.lat.toFixed(5));
      params.set("lon", currentCenter.lon.toFixed(5));
      params.set("zoom", currentZoom.toFixed(1));
    }

    setSearchParams(params, { replace: true });
  }, [
    selectedStatuses,
    excludeFound,
    areaId,
    currentCenter,
    currentZoom,
    setSearchParams,
  ]);

  // Handle bounds change with debouncing
  const handleBoundsChange = useCallback((bounds: MapBounds) => {
    setMapBounds(bounds);
  }, []);

  // Handle center change for URL persistence
  const handleCenterChange = useCallback((lat: number, lon: number) => {
    setCurrentCenter({ lat, lon });
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

  // Handle tileset changes with zoom adjustment for projection switches
  const handleTilesetChange = useCallback(
    (newTileLayerId: string) => {
      const currentLayer = getTileLayer(tileLayerId);
      const newLayer = getTileLayer(newTileLayerId);

      const currentCrs = currentLayer.crs || "EPSG:3857";
      const newCrs = newLayer.crs || "EPSG:3857";

      // Calculate adjusted zoom if projection is changing
      if (currentCrs !== newCrs) {
        const adjustedZoom = calculateProjectionZoom(
          currentZoom,
          currentCrs,
          newCrs,
          newLayer,
        );
        setActiveZoom(adjustedZoom);
      }

      setTileLayerId(newTileLayerId);
    },
    [tileLayerId, currentZoom],
  );

  const handleClearFilters = useCallback(() => {
    setSelectedStatuses([...preferredStatuses]);
    setSelectedColors(() => [...ALL_ICON_COLORS]);
    setExcludeFound(false);
    setRenderMode("auto");
    setTileLayerId(DEFAULT_TILE_LAYER);
    setActiveZoom(MAP_CONFIG.defaultZoom);

    // Clear area_id from URL if present
    if (searchParams.has("area_id")) {
      const newParams = new URLSearchParams(searchParams);
      newParams.delete("area_id");
      setSearchParams(newParams, { replace: true });
    }

    // Reset map to show whole UK
    if (mapInstance) {
      mapInstance.setView(
        [MAP_CONFIG.defaultCenter.lat, MAP_CONFIG.defaultCenter.lng],
        MAP_CONFIG.defaultZoom,
      );
    }
  }, [mapInstance, preferredStatuses, searchParams, setSearchParams]);

  return (
    <Layout>
      <title>Map | TrigpointingUK</title>
      <div className="flex h-[calc(100vh-4rem-7rem)] relative -mx-4 -mb-6">
        {/* Sidebar */}
        <div
          className={`${
            isSidebarOpen ? "w-80" : "w-0"
          } transition-all duration-300 bg-white dark:bg-gray-800 border-r border-gray-200 dark:border-gray-700 overflow-hidden flex-shrink-0`}
        >
          <div className="p-4 h-full overflow-y-auto scrollbar-hide">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-900 dark:text-gray-100">Map Filters</h2>
              <button
                onClick={() => setIsSidebarOpen(false)}
                className="lg:hidden p-1 hover:bg-gray-100 dark:hover:bg-gray-700 rounded"
              >
                <X size={20} className="text-gray-700 dark:text-gray-300" />
              </button>
            </div>

            {/* Status filter */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Trigpoint types
              </label>
              <StatusFilter
                selectedStatuses={selectedStatuses}
                onToggleStatus={handleToggleStatus}
              />
            </div>

            {/* Color filter */}
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
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
                onChange={handleTilesetChange}
              />
            </div>

            {/* Render mode selector */}
            <div className="mb-4">
              <div className="bg-white dark:bg-gray-700 rounded-lg shadow-md dark:shadow-gray-900/50 p-3">
                <label className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Display Mode
                </label>
                <div className="flex gap-1">
                  <button
                    onClick={() => setRenderMode("auto")}
                    className={`flex-1 px-2 py-1.5 text-xs rounded transition-colors ${
                      renderMode === "auto"
                        ? "bg-trig-green-600 text-white"
                        : "bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-500"
                    }`}
                    title="Auto-switch between markers and heatmap based on count"
                  >
                    Auto
                  </button>
                  <button
                    onClick={() => setRenderMode("markers")}
                    className={`flex-1 px-2 py-1.5 text-xs rounded transition-colors ${
                      renderMode === "markers"
                        ? "bg-trig-green-600 text-white"
                        : "bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-500"
                    }`}
                    title="Always show individual markers (may be slow for large datasets)"
                  >
                    Markers
                  </button>
                  <button
                    onClick={() => setRenderMode("heatmap")}
                    className={`flex-1 px-2 py-1.5 text-xs rounded transition-colors ${
                      renderMode === "heatmap"
                        ? "bg-trig-green-600 text-white"
                        : "bg-gray-100 dark:bg-gray-600 text-gray-700 dark:text-gray-200 hover:bg-gray-200 dark:hover:bg-gray-500"
                    }`}
                    title="Always show density heatmap"
                  >
                    Heatmap
                  </button>
                </div>
                {renderMode === "auto" && (
                  <div className="mt-2 text-xs text-gray-600 dark:text-gray-400">
                    {shouldShowHeatmap ? (
                      <span className="text-amber-600 dark:text-amber-400">
                        Showing heatmap ({visibleTrigpoints.length} visible,{" "}
                        {colorFilteredTrigpoints.length} total)
                      </span>
                    ) : (
                      <span className="text-trig-green-600 dark:text-trig-green-400">
                        Showing {visibleTrigpoints.length} markers (
                        {colorFilteredTrigpoints.length} total)
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            {/* Area boundary info (when viewing an area from /trigs) */}
            {areaBoundary && (
              <div className="mb-4 p-3 bg-blue-50 dark:bg-blue-900/30 border border-blue-200 dark:border-blue-800 rounded-lg">
                <div className="text-xs font-medium text-blue-600 dark:text-blue-400 mb-1">
                  Viewing Area Boundary
                </div>
                <div className="text-sm font-semibold text-blue-900 dark:text-blue-200">
                  {areaBoundary.area_type.name}: {areaBoundary.name}
                </div>
              </div>
            )}
            {isLoadingBoundary && (
              <div className="mb-4 p-3 bg-gray-50 dark:bg-gray-700 border border-gray-200 dark:border-gray-600 rounded-lg">
                <div className="text-sm text-gray-600 dark:text-gray-400">
                  Loading area boundary...
                </div>
              </div>
            )}

            {/* Reset map button */}
            <button
              type="button"
              onClick={handleClearFilters}
              className="w-full text-sm text-trig-green-700 dark:text-trig-green-400 hover:text-trig-green-900 dark:hover:text-trig-green-300 font-medium py-2 border border-trig-green-700 dark:border-trig-green-600 rounded hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30 transition-colors"
            >
              Reset map
            </button>

            {/* Results count */}
            <div className="mt-4 text-sm text-gray-600 dark:text-gray-400 p-3 bg-gray-50 dark:bg-gray-700 rounded">
              {isLoading ? (
                <div>
                  <div className="text-sm font-semibold mb-2 text-gray-700 dark:text-gray-300">
                    Loading trigpoints...
                  </div>
                  <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 mb-1">
                    <div
                      className="bg-trig-green-600 h-2 rounded-full transition-all duration-300"
                      style={{ width: `${loadingProgress}%` }}
                    />
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">
                    {loadingProgress.toFixed(0)}%
                  </div>
                </div>
              ) : (
                <div>
                  <div className="font-semibold text-gray-700 dark:text-gray-200">
                    Showing {colorFilteredTrigpoints.length} trigpoints
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    {dataSource === "geojson" ? (
                      <>
                        Comprising:{" "}
                        {geojsonData ? (
                          <>
                            {Object.entries(typeCounts)
                              .sort(([, countA], [, countB]) => countB - countA)
                              .map(([type, count], index, arr) => (
                                <span key={type}>
                                  {count} {type}
                                  {count !== 1 ? "s" : ""}
                                  {index < arr.length - 1 ? ", " : ""}
                                </span>
                              ))}
                          </>
                        ) : (
                          "Loading..."
                        )}
                      </>
                    ) : (
                      <>
                        {allTrigsData.length} loaded, {totalCount} in database
                        (zoom: {currentZoom.toFixed(1)})
                      </>
                    )}
                  </div>
                  {iconColorMode === "condition" &&
                    selectedColors.length !== ALL_ICON_COLORS.length && (
                      <div className="text-xs text-blue-600 dark:text-blue-400 mt-1">
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
            zoom={activeZoom}
            height="100%"
            tileLayerId={tileLayerId}
            onMapReady={setMapInstance}
          >
            <MapViewportTracker
              onBoundsChange={handleBoundsChange}
              onZoomChange={setCurrentZoom}
              onCenterChange={handleCenterChange}
            />
            <MapSizeInvalidator sidebarOpen={isSidebarOpen} />

            {/* Render area boundary if area_id is provided */}
            {areaBoundary && (
              <AreaBoundaryLayer
                boundary={areaBoundary.boundary}
                name={areaBoundary.name}
                areaTypeName={areaBoundary.area_type.name}
                fitBounds={true}
              />
            )}

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
              <>
                <LocationButton
                  map={mapInstance}
                  onLocationFound={(lat, lon) => {
                    mapInstance.setView([lat, lon], 13);
                  }}
                />
                <Link
                  to={`/trigs?lat=${mapInstance.getCenter().lat.toFixed(5)}&lon=${mapInstance.getCenter().lng.toFixed(5)}&location=Map%20centre`}
                  className="bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 p-3 rounded-lg shadow-md dark:shadow-gray-900/50 flex items-center justify-center"
                  title="List nearest trigpoints"
                >
                  <List size={24} className="text-gray-700 dark:text-gray-300" />
                </Link>
              </>
            )}
          </div>

          {/* Toggle sidebar button (mobile) */}
          {!isSidebarOpen && (
            <button
              onClick={() => setIsSidebarOpen(true)}
              className="absolute top-4 left-20 z-[1000] bg-white dark:bg-gray-800 hover:bg-gray-50 dark:hover:bg-gray-700 p-3 rounded-lg shadow-md dark:shadow-gray-900/50"
            >
              <Menu size={24} className="text-gray-700 dark:text-gray-300" />
            </button>
          )}

          {/* Loading overlay */}
          {isLoading && (
            <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-[1000] bg-white dark:bg-gray-800 px-6 py-4 rounded-lg shadow-lg dark:shadow-gray-900/50 min-w-[300px]">
              <div className="flex items-center gap-2 mb-3">
                <Spinner size="sm" />
                <span className="text-sm text-gray-700 dark:text-gray-200 font-semibold">
                  Loading trigpoints...
                </span>
              </div>
              <div className="w-full bg-gray-200 dark:bg-gray-600 rounded-full h-2 mb-1">
                <div
                  className="bg-trig-green-600 h-2 rounded-full transition-all duration-300"
                  style={{ width: `${loadingProgress}%` }}
                />
              </div>
              <div className="text-xs text-gray-500 dark:text-gray-400 text-center">
                {loadingProgress.toFixed(0)}%
              </div>
            </div>
          )}

          {/* Error message */}
          {error && (
            <div className="absolute top-20 left-1/2 transform -translate-x-1/2 z-[1000] bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 text-red-700 dark:text-red-300 px-4 py-2 rounded-lg shadow-md dark:shadow-gray-900/50 max-w-md">
              <p className="text-sm">
                Failed to load trigpoints: {error.message}
              </p>
            </div>
          )}
        </div>
      </div>
    </Layout>
  );
}
