import { useState, useCallback, useEffect, useRef } from "react";
import { useSearchParams } from "react-router-dom";
import { useInfiniteTrigs } from "../hooks/useInfiniteTrigs";
import { useUserLoggedTrigs } from "../hooks/useUserLoggedTrigs";
import { LocationSearch } from "../components/trigs/LocationSearch";
import { StatusFilter } from "../components/trigs/StatusFilter";
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

export default function FindTrigs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth0();
  
  // Fetch user profile to get status_max preference
  const { data: userProfile } = useUserProfile("me");
  
  // Fetch user's logged trigpoints for badge indicator
  const { data: loggedTrigsMap } = useUserLoggedTrigs();

  // Track if we've attempted to get user location
  const [locationAttempted, setLocationAttempted] = useState<boolean>(false);

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
  
  const [selectedStatuses, setSelectedStatuses] = useState<number[]>(
    () => {
      const statuses = searchParams.get("statuses");
      if (statuses) return statuses.split(",").map(Number);
      
      // Default based on user preference or fallback to 30 (Minor mark)
      const userStatusMax = userProfile?.prefs?.status_max || 30;
      
      // Select all statuses up to and including user's max
      return ALL_STATUSES.filter(s => s <= userStatusMax);
    }
  );
  
  const [excludeFound, setExcludeFound] = useState<boolean>(
    () => searchParams.get("excludeFound") === "true"
  );

  // Attempt to get user's current location on mount
  useEffect(() => {
    // Only attempt if no location is set from URL params
    if (centerLat !== null || locationAttempted) {
      return;
    }

    setLocationAttempted(true);

    if (!navigator.geolocation) {
      // Geolocation not supported, fall back to default
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
  }, [centerLat, locationAttempted]);

  // Initialize selected statuses from user preference when profile loads
  useEffect(() => {
    // Only apply user preference if no URL params are set
    if (!searchParams.get("statuses") && userProfile?.prefs?.status_max) {
      const userStatusMax = userProfile.prefs.status_max;
      const defaultStatuses = ALL_STATUSES.filter(s => s <= userStatusMax);
      setSelectedStatuses(defaultStatuses);
    }
  }, [userProfile, searchParams]);

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
    
    if (excludeFound) {
      params.set("excludeFound", "true");
    }
    
    setSearchParams(params, { replace: true });
  }, [centerLat, centerLon, locationName, selectedStatuses, excludeFound, setSearchParams]);

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
    excludeFound,
  });

  const handleSelectLocation = useCallback(
    (lat: number, lon: number, name: string) => {
      setCenterLat(lat);
      setCenterLon(lon);
      setLocationName(name);
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
    setExcludeFound(false);
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
          <div className="space-y-4">
          <div>
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

            {/* Status filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Status Levels
              </label>
              <StatusFilter
                selectedStatuses={selectedStatuses}
                onToggleStatus={handleToggleStatus}
              />
            </div>

            {/* Additional filters */}
            <div className="flex items-center justify-between flex-wrap gap-4">
              <div className="flex items-center gap-4">
                {isAuthenticated && (
                  <label className="flex items-center gap-2 text-sm">
                    <input
                      type="checkbox"
                      checked={excludeFound}
                      onChange={(e) => setExcludeFound(e.target.checked)}
                      className="rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                    />
                    <span>Exclude trigpoints I've found</span>
                  </label>
                )}
              </div>
              
              <button
                type="button"
                onClick={handleClearFilters}
                className="text-sm text-blue-600 hover:text-blue-800 font-medium"
              >
                Clear filters
              </button>
            </div>

            {/* Results count */}
            <div className="text-sm text-gray-600">
              {isLoading || centerLat === null || centerLon === null ? (
                <span>Loading...</span>
              ) : (
                <span>
                  Showing {allTrigs.length} of {totalCount} trigpoints
                  {centerLat && centerLon && locationName && ` near ${locationName}`}
                </span>
              )}
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
            {/* First trigpoint map preview */}
            <div className="mx-4 mt-4 mb-2 flex justify-center">
              <img
                src={`${import.meta.env.VITE_API_BASE}/v1/trigs/${allTrigs[0].id}/map`}
                alt={`Map for ${allTrigs[0].name}`}
                title="The dot represents the first trigpoint in the list, not the searched location"
                className="w-[110px] h-[110px] rounded border-2 border-gray-300 shadow-md cursor-help"
              />
            </div>
            
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

