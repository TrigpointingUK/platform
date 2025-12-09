import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import { useAuth0 } from "@auth0/auth0-react";
import { useQueryClient } from "@tanstack/react-query";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import LogList from "../components/logs/LogList";
import { useUserLogs } from "../hooks/useUserLogs";
import { useUserProfile, updateUserProfile } from "../hooks/useUserProfile";
import { useAreasContaining } from "../hooks/useAreasContaining";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { DateRangePicker, type DateRange } from "../components/ui/DateRangePicker";
import { LocationSearch } from "../components/trigs/LocationSearch";
import { DistanceFilter } from "../components/trigs/DistanceFilter";
import { StatusFilter } from "../components/trigs/StatusFilter";
import { AreaFilter } from "../components/trigs/AreaFilter";

// All status levels (default: all enabled)
const ALL_STATUSES = [10, 20, 30, 40, 50, 60];

export default function UserLogs() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();
  const [isFilterCollapsed, setIsFilterCollapsed] = useState(true);

  // Fetch current user profile to get status_max preference
  const { data: currentUserProfile } = useUserProfile("me");

  // Track if statuses have been initialized from user profile
  const statusesInitializedRef = useRef(false);

  // Track if showTrigCondition has been initialized from user profile
  const showTrigConditionInitializedRef = useRef(false);

  // Compute preferred statuses from user profile
  const preferredStatuses = useMemo(() => {
    const userStatusMax = currentUserProfile?.prefs?.status_max || 30;
    return ALL_STATUSES.filter((s) => s <= userStatusMax);
  }, [currentUserProfile?.prefs?.status_max]);

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
    // Default based on fallback (user profile may not be loaded yet)
    return ALL_STATUSES.filter((s) => s <= 30);
  });

  // Initialize selected statuses from user preference when profile loads (once)
  useEffect(() => {
    // Only apply user preference if no URL params are set and not already initialized
    if (
      !searchParams.get("statuses") &&
      preferredStatuses.length > 0 &&
      !statusesInitializedRef.current
    ) {
      statusesInitializedRef.current = true;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time initialization from async user profile
      setSelectedStatuses(preferredStatuses);
    }
  }, [preferredStatuses, searchParams]);

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

  // Date range filter state
  const [dateRange, setDateRange] = useState<DateRange | undefined>(() => {
    const fromDate = searchParams.get("fromDate");
    const toDate = searchParams.get("toDate");
    if (fromDate || toDate) {
      return {
        from: fromDate ? new Date(fromDate) : undefined,
        to: toDate ? new Date(toDate) : undefined,
      };
    }
    return undefined;
  });

  // Display option: show curated trig condition icon (from user prefs, defaults to off)
  const [showTrigCondition, setShowTrigCondition] = useState<boolean>(false);

  // Initialize showTrigCondition from user preference when profile loads (once)
  useEffect(() => {
    if (
      currentUserProfile?.prefs?.ui_prefs?.show_trig_condition !== undefined &&
      !showTrigConditionInitializedRef.current
    ) {
      showTrigConditionInitializedRef.current = true;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time initialization from async user profile
      setShowTrigCondition(currentUserProfile.prefs.ui_prefs.show_trig_condition);
    }
  }, [currentUserProfile?.prefs?.ui_prefs?.show_trig_condition]);

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
    selectedAreaId !== null ||
    dateRange !== undefined;

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

    // Date range filters
    if (dateRange?.from) {
      params.set("fromDate", dateRange.from.toISOString().split("T")[0]);
    }
    if (dateRange?.to) {
      params.set("toDate", dateRange.to.toISOString().split("T")[0]);
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
    dateRange,
    setSearchParams,
  ]);

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
    setDateRange(undefined);
    // Note: showTrigCondition is a user pref, not a filter - don't reset it
  }, []);

  // Handle toggling showTrigCondition - updates local state and saves to user prefs
  const handleToggleShowTrigCondition = useCallback(
    async (checked: boolean) => {
      // Update local state immediately for responsiveness
      setShowTrigCondition(checked);

      // Save to user prefs if authenticated
      if (isAuthenticated) {
        try {
          await updateUserProfile(
            { ui_prefs: { show_trig_condition: checked } } as Parameters<
              typeof updateUserProfile
            >[0],
            getAccessTokenSilently
          );
          // Invalidate user profile cache
          queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
        } catch (error) {
          console.error("Failed to save show_trig_condition preference:", error);
          // Don't revert local state - let user continue with their choice
        }
      }
    },
    [isAuthenticated, getAccessTokenSilently, queryClient]
  );

  const {
    data: logsData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useUserLogs(userId!, {
    lat: centerLat ?? undefined,
    lon: centerLon ?? undefined,
    maxKm: maxKm ?? undefined,
    statusIds:
      selectedStatuses.length !== ALL_STATUSES.length
        ? selectedStatuses
        : undefined,
    areaId: selectedAreaId ?? undefined,
    fromDate: dateRange?.from,
    toDate: dateRange?.to,
  });

  const { data: user } = useUserProfile(userId!);

  // Update document title when user data loads
  useDocumentTitle(user?.name ? `${user.name}'s Logs` : null);

  // Intersection observer for infinite scroll
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
    rootMargin: "200px",
  });

  // Auto-fetch when scrolling into view
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Flatten all pages into a single array
  const allLogs = logsData?.pages.flatMap((page) => page.items) || [];
  const totalLogs = logsData?.pages[0]?.total || 0;

  if (error) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600">Failed to load user logs</p>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate(-1)}
            className="text-trig-green-600 hover:underline mb-2 inline-block"
          >
            ← Back
          </button>
          <h1 className="text-3xl font-bold text-gray-800">
            {user?.name ? `${user.name}'s Logs` : "User Logs"}
          </h1>
        </div>

        {/* Filter Panel */}
        <div className="bg-white border-b border-gray-200 shadow-md rounded-lg p-4 mb-6">
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
                  ? `Filtered${locationName ? ` near ${locationName}` : ""}${selectedAreaName ? ` in ${selectedAreaName}` : ""}${!locationName && !selectedAreaName && selectedStatuses.length !== ALL_STATUSES.length ? " by type" : ""}`
                  : "Expand to filter logs by location, type, or date"}
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

            {/* Area filter and Date range filter */}
            <div className="flex flex-wrap items-end gap-4">
              <div className="flex-1 min-w-[300px]">
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

              <div className="flex-1 min-w-[300px]">
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Filter by date range
                </label>
                <DateRangePicker
                  value={dateRange}
                  onChange={setDateRange}
                  placeholder="Select date range"
                  maxValue={new Date()}
                  presets={[
                    {
                      label: "Today",
                      dateRange: {
                        from: new Date(),
                        to: new Date(),
                      },
                    },
                    {
                      label: "Last 7 days",
                      dateRange: {
                        from: new Date(new Date().setDate(new Date().getDate() - 7)),
                        to: new Date(),
                      },
                    },
                    {
                      label: "Last 30 days",
                      dateRange: {
                        from: new Date(new Date().setDate(new Date().getDate() - 30)),
                        to: new Date(),
                      },
                    },
                    {
                      label: "Last 3 months",
                      dateRange: {
                        from: new Date(new Date().setMonth(new Date().getMonth() - 3)),
                        to: new Date(),
                      },
                    },
                    {
                      label: "Last 6 months",
                      dateRange: {
                        from: new Date(new Date().setMonth(new Date().getMonth() - 6)),
                        to: new Date(),
                      },
                    },
                    {
                      label: "This year",
                      dateRange: {
                        from: new Date(new Date().getFullYear(), 0, 1),
                        to: new Date(),
                      },
                    },
                    {
                      label: "Last year",
                      dateRange: {
                        from: new Date(new Date().getFullYear() - 1, 0, 1),
                        to: new Date(new Date().getFullYear() - 1, 11, 31),
                      },
                    },
                  ]}
                />
              </div>
            </div>

            {/* Display options */}
            <div className="flex items-center gap-2">
              <input
                type="checkbox"
                id="showTrigCondition"
                checked={showTrigCondition}
                onChange={(e) => handleToggleShowTrigCondition(e.target.checked)}
                className="h-4 w-4 rounded border-gray-300 text-trig-green-600 focus:ring-trig-green-500"
              />
              <label
                htmlFor="showTrigCondition"
                className="text-sm text-gray-700 select-none cursor-pointer"
              >
                Show curated trigpoint condition
              </label>
            </div>

            {/* Results count and clear filters */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {isLoading ? (
                  <span>Loading...</span>
                ) : (
                  <span>
                    Showing {allLogs.length} of {totalLogs.toLocaleString()}{" "}
                    log
                    {totalLogs !== 1 ? "s" : ""}
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

        {/* Logs List */}
        <Card>
          {error && <p className="text-red-600">Failed to load logs</p>}

          {!error && (
            <>
              <LogList
                logs={allLogs}
                isLoading={isLoading}
                emptyMessage={
                  hasActiveFilters
                    ? "No logs found matching your filters"
                    : "No logs found"
                }
                showTrigCondition={showTrigCondition}
              />

              {/* Load More Trigger */}
              {allLogs.length > 0 && (
                <div ref={loadMoreRef} className="py-8 text-center">
                  {isFetchingNextPage && (
                    <>
                      <Spinner size="md" />
                      <p className="text-gray-600 mt-4">Loading more logs...</p>
                    </>
                  )}
                  {!hasNextPage && (
                    <p className="text-gray-500">
                      All {allLogs.length.toLocaleString()} log
                      {allLogs.length !== 1 ? "s" : ""} loaded
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </Layout>
  );
}

