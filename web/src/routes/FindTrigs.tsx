import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useInfiniteTrigs } from "../hooks/useInfiniteTrigs";
import { useUserLoggedTrigs } from "../hooks/useUserLoggedTrigs";
import { useAreasContaining } from "../hooks/useAreasContaining";
import { LocationSearch } from "../components/trigs/LocationSearch";
import { StatusFilter } from "../components/trigs/StatusFilter";
import { LoggedConditionFilter } from "../components/trigs/LoggedConditionFilter";
import { AreaFilter } from "../components/trigs/AreaFilter";
import { DistanceFilter } from "../components/trigs/DistanceFilter";
import { DownloadButton } from "../components/trigs/DownloadButton";
import { TrigCard } from "../components/trigs/TrigCard";
import { useAuth0 } from "@auth0/auth0-react";
import { useUserProfile } from "../hooks/useUserProfile";
import type { UserLogStatus } from "../lib/mapIcons";
import Layout from "../components/layout/Layout";

// Default location: Buxton
const DEFAULT_LAT = 53.2585;
const DEFAULT_LON = -1.9106;
const DEFAULT_LOCATION_NAME = "Buxton";

// All status levels (default: all enabled)
const ALL_STATUSES = [10, 20, 30, 40, 50, 60];

// Reverse mapping: group code to status ID
const GROUP_CODE_TO_STATUS_ID: Record<string, number> = {
  PILLAR: 10,
  FBM: 20,
  SURVEY_MARK: 30,
  INTERSECTED: 40,
  ACTIVE: 50,
  OTHER: 60,
};

export default function FindTrigs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth0();
  const [isFilterCollapsed, setIsFilterCollapsed] = useState(false);
  
  // Fetch user profile to get default_groups preference
  const { data: userProfile } = useUserProfile("me");
  
  // Fetch user's logged trigpoints for badge indicator
  const { data: loggedTrigsMap } = useUserLoggedTrigs();

  // Track if we've attempted to get user location (use ref to avoid triggering re-renders)
  const locationAttemptedRef = useRef(false);
  
  // Track if statuses have been initialized from user profile
  const statusesInitializedRef = useRef(false);

  // Parse URL params or use null initially (will attempt geolocation)
  const [centerLat, setCenterLat] = useState<number | null>(() => {
    const lat = parseFloat(searchParams.get("lat") || "");
    return lat || null;
  });
  const [centerLon, setCenterLon] = useState<number | null>(() => {
    const lon = parseFloat(searchParams.get("lon") || "");
    return lon || null;
  });
  const [locationName, setLocationName] = useState<string>(
    () => searchParams.get("location") || ""
  );
  
  // Compute preferred statuses from user profile
  // Uses default_groups (list of group codes) from ui_prefs
  const preferredStatuses = useMemo(() => {
    const defaultGroups = userProfile?.prefs?.ui_prefs?.default_groups;
    if (defaultGroups && defaultGroups.length > 0) {
      return defaultGroups
        .map((code: string) => GROUP_CODE_TO_STATUS_ID[code])
        .filter((id: number | undefined): id is number => id !== undefined);
    }
    
    // Default is PILLAR + FBM only for guests and users without preferences
    return [10, 20]; // PILLAR, FBM
  }, [userProfile?.prefs?.ui_prefs?.default_groups]);
  
  const [selectedStatuses, setSelectedStatuses] = useState<number[]>(
    () => {
      const statuses = searchParams.get("statuses");
      if (statuses) return statuses.split(",").map(Number);
      
      // Default to PILLAR + FBM only (user profile may not be loaded yet)
      return ALL_STATUSES.filter(s => s <= 20);
    }
  );
  
  // Log filter state: show logged and not-logged trigpoints (both default to true)
  const [showLogged, setShowLogged] = useState<boolean>(
    () => searchParams.get("showLogged") !== "false"
  );
  const [showNotLogged, setShowNotLogged] = useState<boolean>(
    () => searchParams.get("showNotLogged") !== "false"
  );
  
  // Area filter state
  const [selectedAreaId, setSelectedAreaId] = useState<number | null>(() => {
    const areaId = searchParams.get("areaId");
    return areaId ? parseInt(areaId, 10) : null;
  });
  const [selectedAreaName, setSelectedAreaName] = useState<string | null>(
    () => searchParams.get("areaName") || null
  );
  
  // Distance filter state (null means no limit)
  // Default to 200km for performance - prevents slow full-table scans
  const DEFAULT_MAX_KM = 200;
  const [maxKm, setMaxKm] = useState<number | null>(() => {
    const km = searchParams.get("maxKm");
    return km ? parseInt(km, 10) : DEFAULT_MAX_KM;
  });
  
  // Fetch areas containing the current location
  const { data: areasData, isLoading: isLoadingAreas } = useAreasContaining(
    centerLat ?? undefined,
    centerLon ?? undefined
  );

  // Attempt to get user's current location on mount
  useEffect(() => {
    // Only attempt if no location is set from URL params and not already attempted
    if (centerLat !== null || locationAttemptedRef.current) {
      return;
    }

    locationAttemptedRef.current = true;

    if (!navigator.geolocation) {
      // Geolocation not supported, fall back to default
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Responding to external geolocation API check
      setCenterLat(DEFAULT_LAT);
      setCenterLon(DEFAULT_LON);
      setLocationName(DEFAULT_LOCATION_NAME);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        // Success: use user's location
        setCenterLat(position.coords.latitude);
        setCenterLon(position.coords.longitude);
        setLocationName("Current Location");
      },
      (error) => {
        // Permission denied or error: fall back to default
        console.log("Geolocation error:", error.message);
        setCenterLat(DEFAULT_LAT);
        setCenterLon(DEFAULT_LON);
        setLocationName(DEFAULT_LOCATION_NAME);
      }
    );
  }, [centerLat]);

  // Initialize selected statuses from user preference when profile loads (once)
  // This is responding to async user profile data, not derived state
  useEffect(() => {
    // Only apply user preference if no URL params are set and not already initialized
    if (!searchParams.get("statuses") && preferredStatuses.length > 0 && !statusesInitializedRef.current) {
      statusesInitializedRef.current = true;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time initialization from async user profile
      setSelectedStatuses(preferredStatuses);
    }
  }, [preferredStatuses, searchParams]);

  // Update URL when filters change (only if location is set)
  useEffect(() => {
    if (centerLat === null || centerLon === null) {
      return;
    }

    const params = new URLSearchParams();
    params.set("lat", centerLat.toString());
    params.set("lon", centerLon.toString());
    params.set("location", locationName);
    
    if (selectedStatuses.length !== ALL_STATUSES.length) {
      params.set("statuses", selectedStatuses.join(","));
    }
    
    // Only add to URL if not showing (default is to show both)
    if (!showLogged) {
      params.set("showLogged", "false");
    }
    if (!showNotLogged) {
      params.set("showNotLogged", "false");
    }
    
    // Add area filter to URL if selected
    if (selectedAreaId !== null) {
      params.set("areaId", selectedAreaId.toString());
      if (selectedAreaName) {
        params.set("areaName", selectedAreaName);
      }
    }
    
    // Add distance filter to URL if set
    if (maxKm !== null) {
      params.set("maxKm", maxKm.toString());
    }
    
    setSearchParams(params, { replace: true });
  }, [centerLat, centerLon, locationName, selectedStatuses, showLogged, showNotLogged, selectedAreaId, selectedAreaName, maxKm, setSearchParams]);

  // Fetch trigpoints with current filters (only if location is set)
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteTrigs({
    lat: centerLat ?? undefined,
    lon: centerLon ?? undefined,
    statusIds: selectedStatuses.length > 0 ? selectedStatuses : undefined,
    showLogged,
    showNotLogged,
    areaId: selectedAreaId ?? undefined,
    maxKm: maxKm ?? undefined,
  });

  const handleSelectLocation = useCallback(
    (lat: number, lon: number, name: string) => {
      setCenterLat(lat);
      setCenterLon(lon);
      setLocationName(name);
      // Clear area filter when location changes (areas are location-specific)
      setSelectedAreaId(null);
      setSelectedAreaName(null);
    },
    []
  );
  
  const handleSelectArea = useCallback(
    (areaId: number | null, areaName: string | null) => {
      setSelectedAreaId(areaId);
      setSelectedAreaName(areaName);
    },
    []
  );

  const handleToggleStatus = useCallback((statusId: number) => {
    setSelectedStatuses((prev) => {
      if (prev.includes(statusId)) {
        return prev.filter((s) => s !== statusId);
      } else {
        return [...prev, statusId];
      }
    });
  }, []);

  const handleClearFilters = useCallback(() => {
    setSelectedStatuses(ALL_STATUSES);
    setShowLogged(true);
    setShowNotLogged(true);
    setSelectedAreaId(null);
    setSelectedAreaName(null);
    setMaxKm(null);
    setCenterLat(DEFAULT_LAT);
    setCenterLon(DEFAULT_LON);
    setLocationName(DEFAULT_LOCATION_NAME);
  }, []);

  const allTrigs = data?.pages.flatMap((page) => page.items) || [];
  const totalCount = data?.pages[0]?.pagination.total || 0;

  // Infinite scroll: observe the sentinel element
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        // If the sentinel is visible and we have more pages, fetch next page
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      {
        rootMargin: "400px", // Start loading 200px before reaching the sentinel
      }
    );

    observer.observe(sentinel);

    return () => {
      observer.disconnect();
    };
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);
  
  // Helper function to get log status for a trigpoint
  const getLogStatus = (trigId: number): UserLogStatus | null => {
    if (!loggedTrigsMap) return null;
    const condition = loggedTrigsMap.get(trigId);
    return condition 
      ? { hasLogged: true, condition }
      : { hasLogged: false };
  };

  return (
    <Layout>
      <title>Find Trigpoints | TrigpointingUK</title>
      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">
            Browse Trig Points
          </h1>
          <p className="text-gray-600">
            Search and filter UK triangulation pillars and survey markers
          </p>
        </div>

        {/* Fixed filter header */}
        <div className="bg-white border-b border-gray-200 shadow-md rounded-lg p-4 mb-6 sticky top-16 z-40">
          {/* Toggle button and results summary when collapsed */}
          <div className={`flex items-center gap-3 ${isFilterCollapsed ? "" : "mb-2"}`}>
            <button
              type="button"
              onClick={() => setIsFilterCollapsed(!isFilterCollapsed)}
              className="p-1.5 rounded-md hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700"
              aria-label={isFilterCollapsed ? "Expand filters" : "Collapse filters"}
              title={isFilterCollapsed ? "Expand filters" : "Collapse filters"}
            >
              <svg
                className={`w-5 h-5 transition-transform ${isFilterCollapsed ? "" : "rotate-90"}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
              </svg>
            </button>
            {isFilterCollapsed ? (
              <span className="text-sm text-gray-600">
                {centerLat && centerLon && locationName && `Near ${locationName}`}
                {selectedAreaName && ` in ${selectedAreaName}`}
                {!locationName && !selectedAreaName && "Expand to search"}
              </span>
            ) : (
              <span className="text-sm font-medium text-gray-700">
                Search & Filter
              </span>
            )}
          </div>

          {/* Collapsible filter content */}
          <div className={`space-y-4 ${isFilterCollapsed ? "hidden" : ""}`}>
            {/* Location and map preview row */}
            <div className="flex items-end gap-4">
              <div className="flex-1">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Location
                </label>
                <LocationSearch
                  onSelectLocation={handleSelectLocation}
                  defaultLocation={
                    centerLat !== null && centerLon !== null
                      ? {
                          lat: centerLat,
                          lon: centerLon,
                          name: locationName,
                        }
                      : undefined
                  }
                />
              </div>
              {/* First trigpoint map preview */}
              {allTrigs.length > 0 && (
                <img
                  src={`${import.meta.env.VITE_API_BASE}/v1/trigs/${allTrigs[0].id}/map`}
                  alt={`Map for ${allTrigs[0].name}`}
                  title="The dot represents the first trigpoint in the list, not the searched location"
                  className="w-[80px] h-[80px] rounded border-2 border-gray-300 shadow-sm cursor-help flex-shrink-0"
                />
              )}
            </div>

            {/* Status filter and distance filter */}
            <div className="flex flex-wrap items-end gap-4">
              <div className="flex-shrink-0">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Trigpoint types
                </label>
                <StatusFilter
                  selectedStatuses={selectedStatuses}
                  onToggleStatus={handleToggleStatus}
                />
              </div>
              
              {/* Distance filter - grows to fill remaining space, wraps to new row on small screens */}
              <div className="flex-1 min-w-[300px] max-w-[500px] ml-auto">
                <DistanceFilter
                  value={maxKm}
                  onChange={setMaxKm}
                  disabled={centerLat === null || centerLon === null}
                />
              </div>
            </div>

            {/* Log filter, Area filter, and download button */}
            <div className="flex items-center justify-between flex-wrap gap-4">
              {isAuthenticated && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    My logged condition
                  </label>
                  <LoggedConditionFilter
                    showLogged={showLogged}
                    showNotLogged={showNotLogged}
                    onToggleLogged={() => setShowLogged((prev) => !prev)}
                    onToggleNotLogged={() => setShowNotLogged((prev) => !prev)}
                  />
                </div>
              )}
              
              {/* Area filter - shows available areas for the selected location */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Filter by area
                </label>
                <div className="flex items-center gap-2">
                  <AreaFilter
                    areaGroups={areasData?.groups || []}
                    selectedAreaId={selectedAreaId}
                    onSelectArea={handleSelectArea}
                    isLoading={isLoadingAreas}
                    disabled={centerLat === null || centerLon === null}
                  />
                  {selectedAreaId && (
                    <Link
                      to={`/map?area_id=${selectedAreaId}`}
                      className="inline-flex items-center gap-1 px-3 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors"
                      title="View area boundary on map"
                    >
                      <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                      </svg>
                      Map
                    </Link>
                  )}
                </div>
              </div>
              
              {isAuthenticated && (
                <div className="self-end">
                  <DownloadButton
                    statusIds={selectedStatuses}
                    areaId={selectedAreaId}
                    lat={centerLat}
                    lon={centerLon}
                    maxKm={maxKm ?? undefined}
                    onlyFound={!showNotLogged && showLogged}
                    excludeFound={showNotLogged && !showLogged}
                  />
                </div>
              )}
            </div>
            
            {/* Results count and clear filters */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {isLoading || centerLat === null || centerLon === null ? (
                  <span>Loading...</span>
                ) : (
                  <span>
                    Showing {allTrigs.length} of {totalCount} trigpoints
                    {centerLat && centerLon && locationName && ` near ${locationName}`}
                    {selectedAreaName && ` in ${selectedAreaName}`}
                  </span>
                )}
              </div>
              <button
                type="button"
                onClick={handleClearFilters}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors"
              >
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
                Clear filters
              </button>
            </div>
          </div>
        </div>

        {/* Trigpoint list */}
        <div>
        {error && (
          <div className="mx-4 mt-4 p-4 bg-red-50 border border-red-200 rounded-lg text-red-700">
            Error loading trigpoints: {error.message}
          </div>
        )}

        {!isLoading && allTrigs.length === 0 && (
          <div className="mx-4 mt-8 text-center py-12">
            <div className="text-gray-400 text-5xl mb-4">📍</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No trigpoints found
            </h3>
            <p className="text-gray-500">
              Try adjusting your filters or selecting a different location.
            </p>
          </div>
        )}

        {allTrigs.length > 0 && (
          <>
            {/* Trigpoint cards */}
            <div className="bg-white mx-4 mt-4 rounded-lg shadow overflow-hidden">
              {allTrigs.map((trig) => (
                <TrigCard
                  key={trig.id}
                  trig={trig}
                  showDistance={centerLat !== null && centerLon !== null}
                  centerLat={centerLat ?? 0}
                  centerLon={centerLon ?? 0}
                  distanceUnit={(userProfile?.prefs?.distance_ind as 'K' | 'M') || 'K'}
                  logStatus={getLogStatus(trig.id)}
                />
              ))}
            </div>

            {/* Infinite scroll sentinel - invisible element to trigger loading */}
            {hasNextPage && <div ref={sentinelRef} className="h-px" />}

            {/* Loading indicator for infinite scroll */}
            {isFetchingNextPage && (
              <div className="mx-4 my-6 text-center">
                <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"></div>
                <p className="mt-2 text-sm text-gray-500">Loading more...</p>
              </div>
            )}
          </>
        )}

        {/* Initial loading indicator */}
        {isLoading && (
          <div className="mx-4 my-12 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-500">Loading trigpoints...</p>
          </div>
        )}
        </div>
      </div>
    </Layout>
  );
}

