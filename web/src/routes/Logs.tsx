import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import { useAuth0 } from "@auth0/auth0-react";
import { useQueryClient } from "@tanstack/react-query";
import Layout from "../components/layout/Layout";
import LogCard from "../components/logs/LogCard";
import MiniTrigMap from "../components/map/MiniTrigMap";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import { useInfiniteLogs } from "../hooks/useInfiniteLogs";
import { useAreasContaining } from "../hooks/useAreasContaining";
import { useUserProfile, updateUserProfile } from "../hooks/useUserProfile";
import { useConditions, buildConditionMap } from "../hooks/useConditions";
import { conditionsDisagree as checkConditionsDisagree } from "../lib/conditionUtils";
import { LocationSearch } from "../components/trigs/LocationSearch";
import { DistanceFilter } from "../components/trigs/DistanceFilter";
import { StatusFilter } from "../components/trigs/StatusFilter";
import { AreaFilter } from "../components/trigs/AreaFilter";
import { LoggedConditionFilter } from "../components/trigs/LoggedConditionFilter";
import { DateRangePicker, type DateRange } from "../components/ui/DateRangePicker";
import type { Log } from "../hooks/useInfiniteLogs";

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

// Forward mapping: status ID to group code
const STATUS_ID_TO_GROUP_CODE: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "SURVEY_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

// Format date as YYYY-MM-DD in local timezone (not UTC)
function formatLocalDate(date: Date): string {
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  return `${year}-${month}-${day}`;
}

// Parse YYYY-MM-DD string as local date (not UTC)
function parseLocalDate(dateStr: string): Date {
  const [year, month, day] = dateStr.split("-").map(Number);
  return new Date(year, month - 1, day);
}

/**
 * Hardcoded fallback for checking condition disagreements.
 * Used when API condition data is not yet loaded.
 *
 * @deprecated Use conditionsDisagree from conditionUtils with API data
 */
function conditionsDisagreeFallback(
  loggedCondition: string,
  curatedCondition: string | null | undefined
): boolean {
  // Skip logs with N, P, U, Z logged conditions (no definite condition to compare)
  const alwaysIgnoredConditions = ["N", "P", "U", "Z"];
  if (alwaysIgnoredConditions.includes(loggedCondition)) {
    return false;
  }

  // Logged V is only shown if curated is Q, N, X, or U
  if (loggedCondition === "V") {
    const showVForCurated = ["Q", "N", "X", "U"];
    if (!curatedCondition || !showVForCurated.includes(curatedCondition)) {
      return false;
    }
  }

  // If there's no curated condition, we can't compare
  if (!curatedCondition) {
    return false;
  }

  // Check if conditions match (non-transitive relationships)
  const conditionsMatch = (cond1: string, cond2: string): boolean => {
    // Same condition always matches
    if (cond1 === cond2) return true;

    // G and S match
    if ((cond1 === "G" && cond2 === "S") || (cond1 === "S" && cond2 === "G"))
      return true;

    // D and S match (but D and G do not)
    if ((cond1 === "D" && cond2 === "S") || (cond1 === "S" && cond2 === "D"))
      return true;

    // Q and N match
    if ((cond1 === "Q" && cond2 === "N") || (cond1 === "N" && cond2 === "Q"))
      return true;

    return false;
  };

  return !conditionsMatch(loggedCondition, curatedCondition);
}

export default function Logs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated, getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();
  const [isFilterCollapsed, setIsFilterCollapsed] = useState(true);

  // Fetch user profile to get default_groups preference
  const { data: userProfile } = useUserProfile("me");

  // Fetch conditions for disagreement checking
  const { data: apiConditions } = useConditions();
  const conditionMap = useMemo(() => {
    if (!apiConditions) return null;
    return buildConditionMap(apiConditions);
  }, [apiConditions]);

  // Parse userId from URL if present
  const userIdParam = searchParams.get("user");
  const userId = userIdParam ? parseInt(userIdParam, 10) : undefined;

  // Fetch filtered user profile if filtering by user (for the header name)
  const { data: filteredUserProfile } = useUserProfile(userId ? userId.toString() : "");

  // Track if statuses have been initialized from user profile
  const statusesInitializedRef = useRef(false);

  // Track if showTrigCondition has been initialized from user profile
  const showTrigConditionInitializedRef = useRef(false);

  // Compute preferred statuses from user profile
  // Uses default_categories (list of category codes) from ui_prefs
  const preferredStatuses = useMemo(() => {
    const defaultCategories = userProfile?.prefs?.ui_prefs?.default_categories;
    if (defaultCategories && defaultCategories.length > 0) {
      return defaultCategories
        .map((code: string) => GROUP_CODE_TO_STATUS_ID[code])
        .filter((id: number | undefined): id is number => id !== undefined);
    }
    
    // Default is PILLAR + FBM only for guests and users without preferences
    return [10, 20]; // PILLAR, FBM
  }, [userProfile?.prefs?.ui_prefs?.default_categories]);

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
    // Default to PILLAR + FBM only (user profile may not be loaded yet)
    return ALL_STATUSES.filter((s) => s <= 20);
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
  // Default to 200km for performance - prevents slow full-table scans
  const DEFAULT_MAX_KM = 200;
  const [maxKm, setMaxKm] = useState<number | null>(() => {
    const km = searchParams.get("maxKm");
    return km ? parseInt(km, 10) : DEFAULT_MAX_KM;
  });

  // Date range filter state
  const [dateRange, setDateRange] = useState<DateRange | undefined>(() => {
    const fromDate = searchParams.get("fromDate");
    const toDate = searchParams.get("toDate");
    if (fromDate || toDate) {
      return {
        from: fromDate ? parseLocalDate(fromDate) : undefined,
        to: toDate ? parseLocalDate(toDate) : undefined,
      };
    }
    return undefined;
  });

  // Log filter state: show logged and not-logged trigpoints (both default to true)
  const [showLogged, setShowLogged] = useState<boolean>(
    () => searchParams.get("showLogged") !== "false"
  );
  const [showNotLogged, setShowNotLogged] = useState<boolean>(
    () => searchParams.get("showNotLogged") !== "false"
  );

  // Display option: show curated trig condition icon (from user prefs, defaults to off)
  const [showTrigCondition, setShowTrigCondition] = useState<boolean>(false);

  // Filter option: show only logs where logged condition disagrees with curated condition
  const [showOnlyDisagreements, setShowOnlyDisagreements] = useState<boolean>(
    () => searchParams.get("disagreements") === "true"
  );

  // Initialize showTrigCondition from user preference when profile loads (once)
  // But if showOnlyDisagreements is already enabled (from URL), keep showTrigCondition on
  useEffect(() => {
    if (
      userProfile?.prefs?.ui_prefs?.show_trig_condition !== undefined &&
      !showTrigConditionInitializedRef.current
    ) {
      showTrigConditionInitializedRef.current = true;
      // If disagreements filter is active, always show curated condition
      const shouldShow = showOnlyDisagreements || userProfile.prefs.ui_prefs.show_trig_condition;
      // eslint-disable-next-line react-hooks/set-state-in-effect -- One-time initialization from async user profile
      setShowTrigCondition(shouldShow);
    }
  }, [userProfile?.prefs?.ui_prefs?.show_trig_condition, showOnlyDisagreements]);

  // Ensure showTrigCondition is enabled when showOnlyDisagreements changes
  useEffect(() => {
    if (showOnlyDisagreements && !showTrigCondition) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Intentional: disagreements filter requires curated condition to be visible
      setShowTrigCondition(true);
    }
  }, [showOnlyDisagreements, showTrigCondition]);

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
    !showLogged ||
    !showNotLogged ||
    dateRange !== undefined ||
    showOnlyDisagreements;

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();

    // Preserve user param if present
    if (userId !== undefined) {
      params.set("user", userId.toString());
    }

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

    // Only add to URL if not showing (default is to show both)
    if (!showLogged) {
      params.set("showLogged", "false");
    }
    if (!showNotLogged) {
      params.set("showNotLogged", "false");
    }

    // Date range filters
    if (dateRange?.from) {
      params.set("fromDate", formatLocalDate(dateRange.from));
    }
    if (dateRange?.to) {
      params.set("toDate", formatLocalDate(dateRange.to));
    }

    // Condition disagreements filter
    if (showOnlyDisagreements) {
      params.set("disagreements", "true");
    }

    // Note: showTrigCondition is stored in user prefs, not URL

    setSearchParams(params, { replace: true });
  }, [
    userId,
    centerLat,
    centerLon,
    locationName,
    selectedStatuses,
    selectedAreaId,
    selectedAreaName,
    maxKm,
    showLogged,
    showNotLogged,
    dateRange,
    showOnlyDisagreements,
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
    groupCodes:
      selectedStatuses.length !== ALL_STATUSES.length
        ? selectedStatuses
            .map((s) => STATUS_ID_TO_GROUP_CODE[s])
            .filter((code): code is string => code !== undefined)
        : undefined,
    areaId: selectedAreaId ?? undefined,
    userId,
    showLogged,
    showNotLogged,
    fromDate: dateRange?.from,
    toDate: dateRange?.to,
  });

  const handleSelectLocation = useCallback(
    (lat: number, lon: number, name: string) => {
      setCenterLat(lat);
      setCenterLon(lon);
      setLocationName(name);
      // Clear area filter when location changes (areas are location-specific)
      setSelectedAreaId(null);
      setSelectedAreaName(null);
      // Default to 20km when location is selected
      setMaxKm(20);
    },
    []
  );

  const handleClearLocation = useCallback(() => {
    setCenterLat(null);
    setCenterLon(null);
    setLocationName("");
    // Clear area filter when location is cleared (areas are location-specific)
    setSelectedAreaId(null);
    setSelectedAreaName(null);
    // Clear distance filter when location is cleared
    setMaxKm(null);
  }, []);

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
    setShowLogged(true);
    setShowNotLogged(true);
    setDateRange(undefined);
    setShowOnlyDisagreements(false);
    // Note: showTrigCondition is a user pref, not a filter - don't reset it
    // Note: We intentionally do NOT clear userId, as that's a context rather than a filter
  }, []);

  // Handle toggling showTrigCondition - updates local state and saves to user prefs
  const handleToggleShowTrigCondition = useCallback(
    async (checked: boolean) => {
      // Update local state immediately for responsiveness
      setShowTrigCondition(checked);

      // If turning off curated condition display, also turn off disagreements filter
      if (!checked) {
        setShowOnlyDisagreements(false);
      }

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
  const filterPanelRef = useRef<HTMLDivElement | null>(null);
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
  // Also apply client-side filtering for condition disagreements
  const allLogs = useMemo<Log[]>(() => {
    const logs = data?.pages.flatMap((page) => page.items) || [];
    if (!showOnlyDisagreements) {
      return logs;
    }
    return logs.filter((log) => {
      // Use API-based disagreement check if condition data is loaded
      if (conditionMap && conditionMap.size > 0) {
        return checkConditionsDisagree(conditionMap, log.condition, log.trig_condition);
      }
      // Fall back to hardcoded logic if API data not yet loaded
      return conditionsDisagreeFallback(log.condition, log.trig_condition);
    });
  }, [data?.pages, showOnlyDisagreements, conditionMap]);

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

      // Calculate visibility threshold as the maximum of map midpoint and filter panel bottom
      // Using map midpoint (not bottom) allows a little overlap with the map
      const mapRect = mapOverlayRef.current?.getBoundingClientRect();
      const mapMidpoint = mapRect ? mapRect.top + mapRect.height / 2 : 0;
      const filterPanelBottom =
        filterPanelRef.current?.getBoundingClientRect().bottom ?? 0;
      const visibilityThreshold = Math.max(mapMidpoint, filterPanelBottom);

      let firstBelowIndex: number | null = null;
      for (let i = 0; i < allLogs.length; i += 1) {
        const element = logRefs.current.get(i);
        if (!element) {
          continue;
        }
        const rect = element.getBoundingClientRect();
        if (rect.top >= visibilityThreshold) {
          firstBelowIndex = i;
          break;
        }
      }

      const targetIndex =
        firstBelowIndex !== null
          ? firstBelowIndex
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
  }, [allLogs.length, allLogs, centerLogIndex, selectedFeaturedLog, isFilterCollapsed]);

  // Derive effective featured log: user selection or default to first log
  const featuredLog =
    selectedFeaturedLog ?? (allLogs.length > 0 ? allLogs[0] : null);

  const pageTitle = filteredUserProfile?.name 
    ? `${filteredUserProfile.name}'s Logs | TrigpointingUK`
    : "Recent Logs | TrigpointingUK";

  const headerTitle = filteredUserProfile?.name
    ? `${filteredUserProfile.name}'s Logs`
    : "Visit Logs";

  if (error) {
    return (
      <Layout>
        <title>{pageTitle}</title>
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-6">{headerTitle}</h1>
          <div className="bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-700 rounded-lg p-6 text-center">
            <p className="text-red-600 dark:text-red-300 mb-4">
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
      <title>{pageTitle}</title>
      <div className="max-w-4xl mx-auto relative" ref={containerRef}>
        {/* Page Header */}
        <div className="mb-6">
          {userId && (
            <Link
              to={`/profile/${userId}`}
              className="text-trig-green-600 hover:underline mb-2 inline-block"
            >
              ← Back to profile
            </Link>
          )}
          <h1 className="text-3xl font-bold text-gray-900 dark:text-gray-100 mb-2">{headerTitle}</h1>
          <p className="text-gray-600 dark:text-gray-400">
            {userId && filteredUserProfile
              ? `Browse visit logs by ${filteredUserProfile.name}`
              : "Browse recent visit logs from trigpointers across the UK"}
          </p>
        </div>

        {/* Filter Panel */}
        <div
          ref={filterPanelRef}
          className="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 shadow-md dark:shadow-gray-900/50 rounded-lg p-4 mb-6 sticky top-16 z-40"
        >
          {/* Toggle button and results summary when collapsed */}
          <div
            className={`flex items-center gap-3 ${isFilterCollapsed ? "" : "mb-2"}`}
          >
            <button
              type="button"
              onClick={() => setIsFilterCollapsed(!isFilterCollapsed)}
              className="p-1.5 rounded-md hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200"
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
              <span className="text-sm text-gray-600 dark:text-gray-400">
                {hasActiveFilters
                  ? `Filtered${locationName ? ` near ${locationName}` : ""}${selectedAreaName ? ` in ${selectedAreaName}` : ""}${!locationName && !selectedAreaName && selectedStatuses.length !== ALL_STATUSES.length ? " by type" : ""}`
                  : "Expand to filter logs by area"}
              </span>
            ) : (
              <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                Filter Logs
              </span>
            )}
          </div>

          {/* Collapsible filter content */}
          <div className={`space-y-4 ${isFilterCollapsed ? "hidden" : ""}`}>
            {/* Location search */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Location
              </label>
              <LocationSearch
                onSelectLocation={handleSelectLocation}
                onClear={handleClearLocation}
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

            {/* Status filter, logged filter and distance filter */}
            <div className="flex flex-wrap items-end gap-4">
              <div className="flex-shrink-0">
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                  Trigpoint types
                </label>
                <StatusFilter
                  selectedStatuses={selectedStatuses}
                  onToggleStatus={handleToggleStatus}
                />
              </div>

              {/* Logged condition filter - only for authenticated users AND when not viewing a specific user's logs */}
              {isAuthenticated && !userId && (
                <div className="flex-shrink-0">
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
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
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
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
                <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
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
            <div className="flex flex-wrap items-center gap-x-6 gap-y-2">
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="showTrigCondition"
                  checked={showTrigCondition}
                  onChange={(e) => handleToggleShowTrigCondition(e.target.checked)}
                  className="h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-trig-green-600 focus:ring-trig-green-500 dark:bg-gray-700"
                />
                <label
                  htmlFor="showTrigCondition"
                  className="text-sm text-gray-700 dark:text-gray-300 select-none cursor-pointer"
                >
                  Show curated trigpoint condition
                </label>
              </div>

              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  id="showOnlyDisagreements"
                  checked={showOnlyDisagreements}
                  onChange={(e) => {
                    setShowOnlyDisagreements(e.target.checked);
                    // Also enable showing curated condition when filtering by disagreements
                    if (e.target.checked && !showTrigCondition) {
                      handleToggleShowTrigCondition(true);
                    }
                  }}
                  className="h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-trig-green-600 focus:ring-trig-green-500 dark:bg-gray-700"
                />
                <label
                  htmlFor="showOnlyDisagreements"
                  className="text-sm text-gray-700 dark:text-gray-300 select-none cursor-pointer"
                  title="Compare logged condition with curated condition. Treats G/S as matching, Q/N as matching. Ignores logs with P, U, or Z conditions."
                >
                  Show only condition disagreements
                </label>
              </div>
            </div>

            {/* Results count and clear filters */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600 dark:text-gray-400">
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
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 font-medium hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
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
            <p className="text-center text-gray-600 dark:text-gray-400 mt-4">Loading logs...</p>
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
                        ? "border-2 border-trig-green-300 dark:border-trig-green-600 rounded-xl shadow-lg dark:shadow-gray-900/50"
                        : "border-2 border-transparent"
                    } ${
                      isAboveFeatured
                        ? "opacity-50 blur-[1.5px]"
                        : "opacity-100 blur-0"
                    }`}
                  >
                    <LogCard
                      log={log}
                      isCurrentUserLog={!!userProfile && log.user_id === userProfile.id}
                      showDistance={centerLat !== null && centerLon !== null}
                      showTrigCondition={showTrigCondition}
                    />
                  </div>
                );
              })}
            </div>

            {/* Load More Trigger */}
            <div ref={loadMoreRef} className="py-8 text-center">
              {isFetchingNextPage && (
                <>
                  <Spinner size="md" />
                  <p className="text-gray-600 dark:text-gray-400 mt-4">Loading more logs...</p>
                </>
              )}
              {!hasNextPage && allLogs.length > 0 && (
                <p className="text-gray-500 dark:text-gray-400">
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
            <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
              No logs found
            </h3>
            <p className="text-gray-500 dark:text-gray-400">
              {hasActiveFilters
                ? "Try adjusting your filters or clearing them to see more logs."
                : "No visit logs are available at this time."}
            </p>
            {hasActiveFilters && (
              <button
                type="button"
                onClick={handleClearFilters}
                className="mt-4 inline-flex items-center gap-2 px-4 py-2 text-sm font-medium text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-200 hover:bg-blue-50 dark:hover:bg-blue-900/30 rounded-lg transition-colors"
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
            <div className="bg-white dark:bg-gray-800 rounded-lg border-2 border-gray-300 dark:border-gray-600 shadow-2xl dark:shadow-gray-900/70 overflow-hidden">
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
