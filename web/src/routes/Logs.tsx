import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import Layout from "../components/layout/Layout";
import LogCard from "../components/logs/LogCard";
import MiniTrigMap from "../components/map/MiniTrigMap";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import { useInfiniteLogs } from "../hooks/useInfiniteLogs";
import { useAreasContaining } from "../hooks/useAreasContaining";
import { LocationSearch } from "../components/trigs/LocationSearch";
import { DistanceFilter } from "../components/trigs/DistanceFilter";
import { StatusFilter } from "../components/trigs/StatusFilter";
import { AreaFilter } from "../components/trigs/AreaFilter";
import type { Log } from "../hooks/useInfiniteLogs";

// All status levels (default: all enabled)
const ALL_STATUSES = [10, 20, 30, 40, 50, 60];

export default function Logs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [isFilterCollapsed, setIsFilterCollapsed] = useState(false);

  // Filter state - parse from URL or use defaults
  const [centerLat, setCenterLat] = useState<number | null>(() => {
    const lat = parseFloat(searchParams.get("lat") || "");
    return isNaN(lat) ? null : lat;
  });
  const [centerLon, setCenterLon] = useState<number | null>(() => {
    const lon = parseFloat(searchParams.get("lon") || "");
    return isNaN(lon) ? null : lon;
  });
  const [locationName, setLocationName] = useState<string>(
    () => searchParams.get("location") || ""
  );
  const [selectedStatuses, setSelectedStatuses] = useState<number[]>(() => {
    const statuses = searchParams.get("statuses");
    if (statuses) return statuses.split(",").map(Number);
    return ALL_STATUSES; // Default: all statuses
  });
  const [selectedAreaId, setSelectedAreaId] = useState<number | null>(() => {
    const areaId = searchParams.get("areaId");
    return areaId ? parseInt(areaId, 10) : null;
  });
  const [selectedAreaName, setSelectedAreaName] = useState<string | null>(
    () => searchParams.get("areaName") || null
  );
  const [maxKm, setMaxKm] = useState<number | null>(() => {
    const km = searchParams.get("maxKm");
    return km ? parseInt(km, 10) : null;
  });

  // Fetch areas containing the current location
  const { data: areasData, isLoading: isLoadingAreas } = useAreasContaining(
    centerLat ?? undefined,
    centerLon ?? undefined
  );

  // Check if any filters are active
  const hasActiveFilters =
    centerLat !== null ||
    centerLon !== null ||
    maxKm !== null ||
    selectedStatuses.length !== ALL_STATUSES.length ||
    selectedAreaId !== null;

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();

    if (centerLat !== null && centerLon !== null) {
      params.set("lat", centerLat.toString());
      params.set("lon", centerLon.toString());
      if (locationName) {
        params.set("location", locationName);
      }
    }

    if (selectedStatuses.length !== ALL_STATUSES.length) {
      params.set("statuses", selectedStatuses.join(","));
    }

    if (selectedAreaId !== null) {
      params.set("areaId", selectedAreaId.toString());
      if (selectedAreaName) {
        params.set("areaName", selectedAreaName);
      }
    }

    if (maxKm !== null) {
      params.set("maxKm", maxKm.toString());
    }

    setSearchParams(params, { replace: true });
  }, [
    centerLat,
    centerLon,
    locationName,
    selectedStatuses,
    selectedAreaId,
    selectedAreaName,
    maxKm,
    setSearchParams,
  ]);

  // Fetch logs with filters
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteLogs({
    lat: centerLat ?? undefined,
    lon: centerLon ?? undefined,
    maxKm: maxKm ?? undefined,
    statusIds: selectedStatuses.length !== ALL_STATUSES.length ? selectedStatuses : undefined,
    areaId: selectedAreaId ?? undefined,
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
    setCenterLat(null);
    setCenterLon(null);
    setLocationName("");
    setSelectedStatuses(ALL_STATUSES);
    setSelectedAreaId(null);
    setSelectedAreaName(null);
    setMaxKm(null);
  }, []);

  // Map positioning logic
  const MAP_SPACING = 24;
  const MAP_FALLBACK_WIDTH = 200;
  const [centerLogIndex, setCenterLogIndex] = useState<number | null>(null);
  const [selectedFeaturedLog, setSelectedFeaturedLog] = useState<Log | null>(
    null
  );
  const logRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const mapOverlayRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [mapRightOffset, setMapRightOffset] = useState<number>(8);
  const [mapLeftOffset, setMapLeftOffset] = useState<number | null>(null);

  const updateMapOffset = useCallback(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const rect = container.getBoundingClientRect();
    const mapWidth = mapOverlayRef.current?.offsetWidth ?? MAP_FALLBACK_WIDTH;
    const candidateLeft = rect.right + MAP_SPACING;
    const fitsLeft =
      candidateLeft + mapWidth + MAP_SPACING <= window.innerWidth;

    if (fitsLeft) {
      setMapLeftOffset(candidateLeft);
    } else {
      const rightOffset = Math.max(MAP_SPACING, window.innerWidth - rect.right);
      setMapLeftOffset(null);
      setMapRightOffset(rightOffset);
    }
  }, [MAP_SPACING]);

  useEffect(() => {
    updateMapOffset();
    window.addEventListener("resize", updateMapOffset);

    return () => {
      window.removeEventListener("resize", updateMapOffset);
    };
  }, [updateMapOffset]);

  // Intersection observer to trigger loading more logs
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
    rootMargin: "600px", // Start loading 600px before reaching the trigger
  });

  // Flatten all pages into a single array (memoized to prevent re-creation on every render)
  const allLogs = useMemo<Log[]>(
    () => data?.pages.flatMap((page) => page.items) || [],
    [data?.pages]
  );

  const totalCount = data?.pages[0]?.pagination.total || 0;

  useEffect(() => {
    updateMapOffset();
  }, [isLoading, allLogs.length, updateMapOffset]);

  // Auto-fetch when scrolling into view
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Track which log is the first fully visible in viewport
  useEffect(() => {
    const handleScroll = () => {
      if (allLogs.length === 0) return;

      const mapBottom =
        mapOverlayRef.current?.getBoundingClientRect().bottom ?? 0;

      let firstBelowIndex: number | null = null;
      for (let i = 0; i < allLogs.length; i += 1) {
        const element = logRefs.current.get(i);
        if (!element) {
          continue;
        }
        const rect = element.getBoundingClientRect();
        if (rect.top >= mapBottom) {
          firstBelowIndex = i;
          break;
        }
      }

      const targetIndex =
        firstBelowIndex !== null
          ? Math.max(0, firstBelowIndex - 1)
          : allLogs.length > 0
            ? allLogs.length - 1
            : null;

      if (targetIndex !== null) {
        if (targetIndex !== centerLogIndex) {
          setCenterLogIndex(targetIndex);
        }
        const candidate = allLogs[targetIndex];
        if (candidate && candidate.id !== selectedFeaturedLog?.id) {
          setSelectedFeaturedLog(candidate);
        }
      }
    };

    // Initial check
    handleScroll();

    // Listen for scroll events with throttling
    let timeoutId: number;
    const throttledScroll = () => {
      if (timeoutId) {
        window.cancelAnimationFrame(timeoutId);
      }
      timeoutId = window.requestAnimationFrame(handleScroll);
    };

    window.addEventListener("scroll", throttledScroll, { passive: true });
    window.addEventListener("resize", throttledScroll);

    return () => {
      window.removeEventListener("scroll", throttledScroll);
      window.removeEventListener("resize", throttledScroll);
      if (timeoutId) {
        window.cancelAnimationFrame(timeoutId);
      }
    };
  }, [allLogs.length, allLogs, centerLogIndex, selectedFeaturedLog]);

  // Derive effective featured log: user selection or default to first log
  const featuredLog =
    selectedFeaturedLog ?? (allLogs.length > 0 ? allLogs[0] : null);

  if (error) {
    return (
      <Layout>
        <title>Recent Logs | TrigpointingUK</title>
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Visit Logs</h1>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-600 mb-4">
              Failed to load logs. Please try again later.
            </p>
            <Button onClick={() => window.location.reload()}>Reload Page</Button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <title>Recent Logs | TrigpointingUK</title>
      <div className="max-w-4xl mx-auto relative" ref={containerRef}>
        {/* Page Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-900 mb-2">Visit Logs</h1>
          <p className="text-gray-600">
            Browse recent visit logs from trigpointers across the UK
          </p>
        </div>

        {/* Filter Panel */}
        <div className="bg-white border-b border-gray-200 shadow-md rounded-lg p-4 mb-6 sticky top-16 z-40">
          {/* Toggle button and results summary when collapsed */}
          <div
            className={`flex items-center gap-3 ${isFilterCollapsed ? "" : "mb-2"}`}
          >
            <button
              type="button"
              onClick={() => setIsFilterCollapsed(!isFilterCollapsed)}
              className="p-1.5 rounded-md hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700"
              aria-label={
                isFilterCollapsed ? "Expand filters" : "Collapse filters"
              }
              title={isFilterCollapsed ? "Expand filters" : "Collapse filters"}
            >
              <svg
                className={`w-5 h-5 transition-transform ${isFilterCollapsed ? "" : "rotate-90"}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
            {isFilterCollapsed ? (
              <span className="text-sm text-gray-600">
                {hasActiveFilters
                  ? `Filtered${locationName ? ` near ${locationName}` : ""}${selectedAreaName ? ` in ${selectedAreaName}` : ""}`
                  : "Expand to filter"}
              </span>
            ) : (
              <span className="text-sm font-medium text-gray-700">
                Filter Logs
              </span>
            )}
          </div>

          {/* Collapsible filter content */}
          <div className={`space-y-4 ${isFilterCollapsed ? "hidden" : ""}`}>
            {/* Location search */}
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

              {/* Distance filter - grows to fill remaining space */}
              <div className="flex-1 min-w-[300px] max-w-[500px] ml-auto">
                <DistanceFilter
                  value={maxKm}
                  onChange={setMaxKm}
                  disabled={centerLat === null || centerLon === null}
                />
              </div>
            </div>

            {/* Area filter */}
            <div>
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by area
              </label>
              <AreaFilter
                areaGroups={areasData?.groups || []}
                selectedAreaId={selectedAreaId}
                onSelectArea={handleSelectArea}
                isLoading={isLoadingAreas}
                disabled={centerLat === null || centerLon === null}
              />
            </div>

            {/* Results count and clear filters */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {isLoading ? (
                  <span>Loading...</span>
                ) : (
                  <span>
                    Showing {allLogs.length} of {totalCount.toLocaleString()}{" "}
                    log
                    {totalCount !== 1 ? "s" : ""}
                    {locationName && ` near ${locationName}`}
                    {selectedAreaName && ` in ${selectedAreaName}`}
                  </span>
                )}
              </div>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={handleClearFilters}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                  Clear filters
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="py-12">
            <Spinner size="lg" />
            <p className="text-center text-gray-600 mt-4">Loading logs...</p>
          </div>
        )}

        {/* Log List */}
        {!isLoading && allLogs.length > 0 && (
          <>
            <div className="space-y-4">
              {allLogs.map((log, index) => {
                const isFeatured = centerLogIndex === index;
                const isAboveFeatured =
                  centerLogIndex !== null && index < centerLogIndex;

                return (
                  <div
                    key={log.id}
                    ref={(el) => {
                      if (el) {
                        logRefs.current.set(index, el);
                      } else {
                        logRefs.current.delete(index);
                      }
                    }}
                    className={`transition-all duration-300 ${
                      isFeatured
                        ? "border-2 border-trig-green-300 rounded-xl shadow-lg"
                        : "border-2 border-transparent"
                    } ${
                      isAboveFeatured
                        ? "opacity-50 blur-[1.5px]"
                        : "opacity-100 blur-0"
                    }`}
                  >
                    <LogCard log={log} showDistance={centerLat !== null && centerLon !== null} />
                  </div>
                );
              })}
            </div>

            {/* Load More Trigger */}
            <div ref={loadMoreRef} className="py-8 text-center">
              {isFetchingNextPage && (
                <>
                  <Spinner size="md" />
                  <p className="text-gray-600 mt-4">Loading more logs...</p>
                </>
              )}
              {!hasNextPage && allLogs.length > 0 && (
                <p className="text-gray-500">
                  You've reached the end! {allLogs.length.toLocaleString()} log
                  {allLogs.length !== 1 ? "s" : ""} loaded.
                </p>
              )}
            </div>
          </>
        )}

        {/* Empty State */}
        {!isLoading && allLogs.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📝</div>
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              No logs found
            </h3>
            <p className="text-gray-500">
              {hasActiveFilters
                ? "Try adjusting your filters or clearing them to see more logs."
                : "No visit logs are available at this time."}
            </p>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleClearFilters}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 hover:text-blue-800 hover:bg-blue-50 rounded-lg transition-colors"
              >
                Clear all filters
              </button>
            )}
          </div>
        )}

        {/* Floating Map Overlay - Fixed position on desktop */}
        {!isLoading && allLogs.length > 0 && (
          <div
            className="fixed top-22 z-40"
            ref={mapOverlayRef}
            style={
              mapLeftOffset !== null && mapLeftOffset > 0
                ? { left: mapLeftOffset }
                : { right: mapRightOffset }
            }
          >
            <div className="bg-white rounded-lg border-2 border-gray-300 shadow-2xl overflow-hidden">
              <div className="relative">
                <MiniTrigMap
                  trigId={featuredLog?.trig_id ?? null}
                  trigName={featuredLog?.trig_name ?? ""}
                  lat={featuredLog?.trig_lat ?? null}
                  lon={featuredLog?.trig_lon ?? null}
                  className="w-[160px] h-[160px] lg:w-[190px] lg:h-[190px]"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}
