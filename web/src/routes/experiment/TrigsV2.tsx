/**
 * TrigsV2 - Experimental trigpoints browser with filter chips UI
 * 
 * This is an experimental version of the /trigs page using a filter chips
 * approach instead of the traditional filter panel. The goal is to evaluate
 * whether this UX pattern works better for the variety of filters we need.
 */

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { Filter, RotateCcw, ArrowUpDown, Mountain, Trophy, SortAsc, MapPin, CalendarCheck, List, Map as MapIcon, ChevronDown, ChevronUp } from "lucide-react";

import Card from "../../components/ui/Card";
import { TrigCard } from "../../components/trigs/TrigCard";
import { DownloadButton } from "../../components/trigs/DownloadButton";
import { TrigsV2Map } from "../../components/experiment/TrigsV2Map";
import { useInfiniteTrigs } from "../../hooks/useInfiniteTrigs";
import { useTrigPoints } from "../../hooks/useTrigPoints";
import { buildTrigFilterParams, type TrigFilterOptions } from "../../lib/trigFilterParams";
import { readAreaIds, readSelection, writeSelection } from "../../lib/trigsPageParams";
import { useUserLoggedTrigs } from "../../hooks/useUserLoggedTrigs";
import { useUserProfile } from "../../hooks/useUserProfile";
import AddToListButton from "../../components/lists/AddToListButton";
import type { UserLogStatus } from "../../lib/mapIcons";

// Import reference data hooks
import {
  useTrigCategories,
  useConditions,
  useHistoricUseValues,
  useCurrentUseValues,
  useAreasByIds,
} from "../../hooks/useReferenceData";

// Import filter chips
import {
  LocationChip,
  RadiusChip,
  HistoricUseChip,
  CurrentUseChip,
  ConditionChip,
  LogsChip,
  TypeChip,
  AreaChip,
  toggleAreaSelection,
  SortChip,
  ALL_CATEGORY_IDS,
  type SortDirection,
  type LogUser,
  type SelectedArea,
} from "../../components/experiment/chips";

// Default location: Buxton
const DEFAULT_LAT = 53.2585;
const DEFAULT_LON = -1.9106;
const DEFAULT_LOCATION_NAME = "Buxton";

// What LocationSearch calls the device's own location
const DEVICE_LOCATION_NAME = "Current location";

const FILTERS_COLLAPSED_KEY = "trigsV2.filtersCollapsed";
const FILTER_TOGGLE_CLASSES =
  "shrink-0 p-1 -m-1 rounded text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-700";

export default function TrigsV2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth0();
  
  const showListActions = isAuthenticated;
  
  // Fetch user profile to get preferences
  const { data: userProfile } = useUserProfile("me");
  
  // Fetch user's logged trigpoints for badge indicator
  const { data: loggedTrigsMap } = useUserLoggedTrigs();

  // Track if we've attempted to get user location
  const locationAttemptedRef = useRef(false);
  
  // The URL as the page was opened. Filters whose options come from the API
  // are restored from this once those options have loaded.
  const [initialParams] = useState(() => new URLSearchParams(searchParams));

  // Whether those filters have been restored. Until then the URL is left
  // alone, so it can't be rewritten before it has been read.
  const [filtersReady, setFiltersReady] = useState(false);

  // ==========================================================================
  // Reference Data (from API)
  // ==========================================================================
  
  const { data: categories } = useTrigCategories();
  const { data: conditions } = useConditions();
  const { data: historicUseValues } = useHistoricUseValues();
  const { data: currentUseValues } = useCurrentUseValues();

  // Computed "all" values from API data
  const allTypeCodes = useMemo(() => {
    if (!categories) return [];
    return categories.flatMap((c) => c.types.map((t) => t.code));
  }, [categories]);

  const allConditionCodes = useMemo(() => {
    if (!conditions) return [];
    return conditions.map((c) => c.code);
  }, [conditions]);

  const allHistoricUseValues = useMemo(() => {
    if (!historicUseValues) return [];
    return historicUseValues.map((v) => v.value);
  }, [historicUseValues]);

  const allCurrentUseValues = useMemo(() => {
    if (!currentUseValues) return [];
    return currentUseValues.map((v) => v.value);
  }, [currentUseValues]);

  // ==========================================================================
  // Filter State
  // ==========================================================================

  // Location. Only a place the user picked is kept in the URL; otherwise the
  // page uses the device's location afresh on each visit (falling back to
  // Buxton), so refreshes follow the device and shared links don't carry the
  // sharer's whereabouts. Older links saved "Current location" coordinates -
  // those are ignored in favour of the device.
  const [urlLocation] = useState(() => {
    const lat = parseFloat(searchParams.get("lat") || "");
    const lon = parseFloat(searchParams.get("lon") || "");
    const name = searchParams.get("location") || "";
    return lat && lon && name !== DEVICE_LOCATION_NAME ? { lat, lon, name } : null;
  });
  const [centerLat, setCenterLat] = useState<number | null>(urlLocation?.lat ?? null);
  const [centerLon, setCenterLon] = useState<number | null>(urlLocation?.lon ?? null);
  const [locationName, setLocationName] = useState<string>(urlLocation?.name ?? "");
  const [locationChosen, setLocationChosen] = useState(urlLocation !== null);

  // Categories (status IDs: 10=Pillar, 20=FBM, etc.)
  const [selectedCategories, setSelectedCategories] = useState<number[]>(() =>
    readSelection(searchParams, "categories", ALL_CATEGORY_IDS)
  );

  // Distance/radius - unlimited by default; the location still sets the
  // origin for sorting by distance
  const [maxKm, setMaxKm] = useState<number | null>(() => {
    const km = parseInt(searchParams.get("maxKm") || "", 10);
    return km > 0 ? km : null;
  });

  // List or map view
  const [view, setView] = useState<"list" | "map">(() =>
    searchParams.get("view") === "map" ? "map" : "list"
  );

  // Bumped to make the map zoom back out to fit all the trigs
  const [mapFitRequest, setMapFitRequest] = useState(0);

  // Filter panel collapsed to just the results row, to leave room on small
  // screens. Remembered per browser.
  const [filtersCollapsed, setFiltersCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(FILTERS_COLLAPSED_KEY) === "1";
    } catch {
      return false;
    }
  });
  const toggleFiltersCollapsed = useCallback(() => {
    setFiltersCollapsed((prev) => {
      try {
        localStorage.setItem(FILTERS_COLLAPSED_KEY, prev ? "0" : "1");
      } catch {
        // Storage unavailable - just don't remember it
      }
      return !prev;
    });
  }, []);

  // Historic use filter - starts empty, populated when API data loads
  const [selectedHistoricUse, setSelectedHistoricUse] = useState<string[]>([]);

  // Current/recent use filter - starts empty, populated when API data loads
  const [selectedCurrentUse, setSelectedCurrentUse] = useState<string[]>([]);

  // Condition filter - starts empty, populated when API data loads
  const [selectedConditions, setSelectedConditions] = useState<string[]>([]);

  // Type filter - starts empty, populated when API data loads
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);

  // Logs filter, with individual conditions for logged trigs. Stored as the
  // conditions switched *off*, so "all conditions" holds before the list has
  // loaded from the API and covers every code the API returns.
  const [deselectedLoggedConditions, setDeselectedLoggedConditions] = useState<string[]>(
    () => searchParams.get("loggedExclude")?.split(",").filter(Boolean) ?? []
  );
  const selectedLoggedConditions = allConditionCodes.filter(
    (code) => !deselectedLoggedConditions.includes(code)
  );
  const noLoggedConditions =
    allConditionCodes.length > 0 && selectedLoggedConditions.length === 0;
  const [showNotLogged, setShowNotLogged] = useState<boolean>(
    () => searchParams.get("notLogged") !== "0"
  );

  // Whose logs the log filters and "logged date" sort refer to: null means
  // the signed-in user
  const [logUser, setLogUser] = useState<LogUser | null>(() => {
    const id = parseInt(searchParams.get("loggedBy") || "", 10);
    const name = searchParams.get("loggedByName");
    return id > 0 && name ? { id, name } : null;
  });
  const hasLogUser = logUser !== null || isAuthenticated;

  // Area filter (for full area chip) - empty means no area filter. All
  // selected areas are of one area type (see toggleAreaSelection).
  const [selectedAreas, setSelectedAreas] = useState<SelectedArea[]>([]);
  const selectedAreaIds = useMemo(() => selectedAreas.map((a) => a.id), [selectedAreas]);

  // Areas from the URL, looked up for their names and types
  const [initialAreaIds] = useState(() => readAreaIds(initialParams));
  const initialAreas = useAreasByIds(initialAreaIds);

  // ==========================================================================
  // Initialize filters when API data loads
  // ==========================================================================
  
  useEffect(() => {
    if (filtersReady) return;

    // Wait until all reference data, and any areas from the URL, have loaded
    if (!categories || !conditions || !historicUseValues || !currentUseValues || !initialAreas) return;

    // eslint-disable-next-line react-hooks/set-state-in-effect -- Initialising state from URL params on first data load
    setSelectedTypes(readSelection(initialParams, "types", allTypeCodes));
    setSelectedConditions(readSelection(initialParams, "conditions", allConditionCodes));
    setSelectedHistoricUse(readSelection(initialParams, "historicUse", allHistoricUseValues));
    setSelectedCurrentUse(readSelection(initialParams, "currentUse", allCurrentUseValues));

    // Areas of one type only, as the chip allows (see toggleAreaSelection)
    const areaTypeId = initialAreas[0]?.area_type?.id ?? initialAreas[0]?.area_type_id;
    setSelectedAreas(
      initialAreas
        .map((area) => ({
          id: area.id,
          name: area.name,
          areaTypeId: area.area_type?.id ?? area.area_type_id,
          areaTypeName: area.area_type?.name ?? "",
        }))
        .filter((area) => area.areaTypeId === areaTypeId)
    );

    setFiltersReady(true);
  }, [filtersReady, categories, conditions, historicUseValues, currentUseValues, initialAreas, initialParams, allTypeCodes, allConditionCodes, allHistoricUseValues, allCurrentUseValues]);

  // ==========================================================================
  // Sort State
  // ==========================================================================
  
  const [sortKey, setSortKey] = useState<string>(() => {
    return searchParams.get("sort") || "distance";
  });
  const [sortDirection, setSortDirection] = useState<SortDirection>(() => {
    const dir = searchParams.get("dir");
    return dir === "desc" ? "desc" : "asc";
  });

  const handleSort = useCallback((newSortKey: string, newDirection: SortDirection) => {
    setSortKey(newSortKey);
    setSortDirection(newDirection);
  }, []);

  // "Logged date" needs someone's logs to sort by
  const effectiveSortKey = sortKey === "logged" && !hasLogUser ? "distance" : sortKey;

  // ==========================================================================
  // Location Geolocation
  // ==========================================================================

  useEffect(() => {
    if (centerLat !== null || locationAttemptedRef.current) {
      return;
    }

    locationAttemptedRef.current = true;

    if (!navigator.geolocation) {
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Responding to external geolocation API check
      setCenterLat(DEFAULT_LAT);
      setCenterLon(DEFAULT_LON);
      setLocationName(DEFAULT_LOCATION_NAME);
      return;
    }

    navigator.geolocation.getCurrentPosition(
      (position) => {
        setCenterLat(position.coords.latitude);
        setCenterLon(position.coords.longitude);
        setLocationName(DEVICE_LOCATION_NAME);
      },
      // Blocked, or no fix in time
      () => {
        setCenterLat(DEFAULT_LAT);
        setCenterLon(DEFAULT_LON);
        setLocationName(DEFAULT_LOCATION_NAME);
      },
      // A fix from the last few minutes is fine; don't hang on a slow one
      { maximumAge: 5 * 60 * 1000, timeout: 15 * 1000 }
    );
  }, [centerLat]);

  // ==========================================================================
  // Filter Handlers
  // ==========================================================================

  const handleSelectLocation = useCallback(
    (lat: number, lon: number, name: string) => {
      setCenterLat(lat);
      setCenterLon(lon);
      setLocationName(name);
      setLocationChosen(name !== DEVICE_LOCATION_NAME);
    },
    []
  );

  const handleToggleCategory = useCallback((categoryId: number) => {
    setSelectedCategories((prev) => {
      if (prev.includes(categoryId)) {
        return prev.filter((c) => c !== categoryId);
      } else {
        return [...prev, categoryId];
      }
    });
  }, []);

  const handleToggleHistoricUse = useCallback((value: string) => {
    setSelectedHistoricUse((prev) => {
      if (prev.includes(value)) {
        return prev.filter((v) => v !== value);
      } else {
        return [...prev, value];
      }
    });
  }, []);

  const handleToggleCurrentUse = useCallback((value: string) => {
    setSelectedCurrentUse((prev) => {
      if (prev.includes(value)) {
        return prev.filter((v) => v !== value);
      } else {
        return [...prev, value];
      }
    });
  }, []);

  const handleToggleCondition = useCallback((code: string) => {
    setSelectedConditions((prev) => {
      if (prev.includes(code)) {
        return prev.filter((c) => c !== code);
      } else {
        return [...prev, code];
      }
    });
  }, []);

  const handleToggleLoggedCondition = useCallback((code: string) => {
    setDeselectedLoggedConditions((prev) =>
      prev.includes(code)
        ? prev.filter((c) => c !== code)
        : [...prev, code]
    );
  }, []);

  const handleToggleType = useCallback((typeCode: string) => {
    setSelectedTypes((prev) => {
      if (prev.includes(typeCode)) {
        return prev.filter((t) => t !== typeCode);
      } else {
        return [...prev, typeCode];
      }
    });
  }, []);

  const handleToggleArea = useCallback((area: SelectedArea) => {
    setSelectedAreas((prev) => toggleAreaSelection(prev, area));
  }, []);

  const handleLogUserChange = useCallback((user: LogUser | null) => {
    setLogUser(user);
    if (user === null && !isAuthenticated) {
      // Nobody's logs to filter on any more, so drop the log filters
      setDeselectedLoggedConditions([]);
      setShowNotLogged(true);
    }
  }, [isAuthenticated]);

  const handleClearAllFilters = useCallback(() => {
    setSelectedCategories(ALL_CATEGORY_IDS);
    setMaxKm(null);
    setSelectedHistoricUse(allHistoricUseValues);
    setSelectedCurrentUse(allCurrentUseValues);
    setSelectedConditions(allConditionCodes);
    setDeselectedLoggedConditions([]);
    setShowNotLogged(true);
    setLogUser(null);
    setSelectedTypes(allTypeCodes);
    setSelectedAreas([]);
  }, [allTypeCodes, allConditionCodes, allHistoricUseValues, allCurrentUseValues]);

  // ==========================================================================
  // URL Parameter Sync
  // ==========================================================================
  
  // Update URL when filter/sort state changes
  useEffect(() => {
    if (!filtersReady) return;

    const params = new URLSearchParams();
    
    // Location, only if the user picked it
    if (locationChosen && centerLat !== null && centerLon !== null) {
      params.set("lat", centerLat.toFixed(5));
      params.set("lon", centerLon.toFixed(5));
      params.set("location", locationName);
    }
    
    // Radius (only if limited)
    if (maxKm !== null) {
      params.set("maxKm", maxKm.toString());
    }

    // Whose logs
    if (logUser) {
      params.set("loggedBy", logUser.id.toString());
      params.set("loggedByName", logUser.name);
    }

    // Logs filter (only if narrowed)
    if (deselectedLoggedConditions.length > 0) {
      params.set("loggedExclude", deselectedLoggedConditions.join(","));
    }
    if (!showNotLogged) {
      params.set("notLogged", "0");
    }

    // View
    if (view === "map") {
      params.set("view", "map");
    }
    
    // Sort (only if not default)
    if (sortKey !== "distance") {
      params.set("sort", sortKey);
    }
    if (sortDirection !== "asc") {
      params.set("dir", sortDirection);
    }
    
    // Multi-select filters (only if not all selected)
    writeSelection(params, "categories", selectedCategories, ALL_CATEGORY_IDS);
    writeSelection(params, "types", selectedTypes, allTypeCodes);
    writeSelection(params, "conditions", selectedConditions, allConditionCodes);
    writeSelection(params, "historicUse", selectedHistoricUse, allHistoricUseValues);
    writeSelection(params, "currentUse", selectedCurrentUse, allCurrentUseValues);

    // Areas
    if (selectedAreaIds.length > 0) {
      params.set("areas", selectedAreaIds.join(","));
    }
    
    // Update URL without triggering navigation
    setSearchParams(params, { replace: true });
  }, [
    filtersReady, locationChosen, centerLat, centerLon, locationName, maxKm, sortKey, sortDirection,
    selectedCategories, selectedTypes, selectedConditions, selectedHistoricUse,
    selectedCurrentUse, selectedAreaIds, allTypeCodes, allConditionCodes,
    allHistoricUseValues, allCurrentUseValues, logUser, view,
    deselectedLoggedConditions, showNotLogged, setSearchParams
  ]);

  // ==========================================================================
  // Data Fetching
  // ==========================================================================

  // Build order string with direction prefix
  const orderParam = sortDirection === "desc" ? `-${effectiveSortKey}` : effectiveSortKey;

  // Only send types filter when not all types are selected
  const typesFilter = useMemo(() => {
    if (selectedTypes.length === 0) return []; // Show nothing
    if (selectedTypes.length === allTypeCodes.length) return undefined; // Show all (no filter)
    return selectedTypes;
  }, [selectedTypes, allTypeCodes.length]);

  // Only send historic use filter when not all values are selected
  const historicUseFilter = useMemo(() => {
    if (selectedHistoricUse.length === 0) return []; // Show nothing
    if (selectedHistoricUse.length === allHistoricUseValues.length) return undefined; // Show all (no filter)
    return selectedHistoricUse;
  }, [selectedHistoricUse, allHistoricUseValues.length]);

  // Only send current use filter when not all values are selected
  const currentUseFilter = useMemo(() => {
    if (selectedCurrentUse.length === 0) return []; // Show nothing
    if (selectedCurrentUse.length === allCurrentUseValues.length) return undefined; // Show all (no filter)
    return selectedCurrentUse;
  }, [selectedCurrentUse, allCurrentUseValues.length]);

  // Only send conditions filter when not all conditions are selected
  const conditionsFilter = useMemo(() => {
    if (selectedConditions.length === 0) return []; // Show nothing
    if (selectedConditions.length === allConditionCodes.length) return undefined; // Show all (no filter)
    return selectedConditions;
  }, [selectedConditions, allConditionCodes.length]);

  // The complete filter set, shared by the list, the map and downloads
  const filterOptions: TrigFilterOptions = {
    lat: centerLat ?? undefined,
    lon: centerLon ?? undefined,
    maxKm: maxKm ?? undefined,
    statusIds: selectedCategories.length > 0 ? selectedCategories : undefined,
    types: typesFilter,
    historicUse: historicUseFilter,
    currentUse: currentUseFilter,
    conditions: conditionsFilter,
    ...(hasLogUser && {
      loggedBy: logUser?.id,
      showLogged: !noLoggedConditions,
      showNotLogged,
      // Only narrow by logged condition for a partial selection - "all" means
      // any log, whatever its condition code
      loggedConditions:
        deselectedLoggedConditions.length > 0 && !noLoggedConditions
          ? selectedLoggedConditions
          : undefined,
    }),
    areaIds: selectedAreaIds.length > 0 ? selectedAreaIds : undefined,
  };

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteTrigs({ ...filterOptions, order: orderParam });

  // The map plots the whole filtered set. The centre only matters to it
  // when it limits the radius, so leave it out otherwise (better caching).
  const {
    data: mapPoints,
    isLoading: isMapLoading,
    error: mapError,
  } = useTrigPoints(
    maxKm === null ? { ...filterOptions, lat: undefined, lon: undefined } : filterOptions,
    view === "map",
  );

  // Number the rows when the list is someone's logged trigs in logging order,
  // so e.g. #1000 of their pillars is their 1000th pillar
  const showPositions = effectiveSortKey === "logged" && hasLogUser && !showNotLogged;

  const allTrigs = data?.pages.flatMap((page) => page.items) || [];
  const totalCount = data?.pages[0]?.pagination.total || 0;

  // Infinite scroll sentinel
  const sentinelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const sentinel = sentinelRef.current;
    if (!sentinel) return;

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasNextPage && !isFetchingNextPage) {
          fetchNextPage();
        }
      },
      { rootMargin: "400px" }
    );

    observer.observe(sentinel);
    return () => observer.disconnect();
  }, [hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Helper to get log status for a trigpoint
  const getLogStatus = (trigId: number): UserLogStatus | null => {
    if (!loggedTrigsMap) return null;
    const condition = loggedTrigsMap.get(trigId);
    return condition 
      ? { hasLogged: true, condition }
      : { hasLogged: false };
  };

  // Count active filters (filters that are not at their default "all" state)
  // Note: Location is not counted. Radius counts when it's not infinity (null).
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (selectedCategories.length !== ALL_CATEGORY_IDS.length) count++;
    if (maxKm !== null) count++; // Count when radius is limited (not infinity)
    if (selectedHistoricUse.length !== allHistoricUseValues.length) count++;
    if (selectedCurrentUse.length !== allCurrentUseValues.length) count++;
    if (selectedConditions.length !== allConditionCodes.length) count++;
    if (
      hasLogUser &&
      (deselectedLoggedConditions.length > 0 || !showNotLogged || logUser !== null)
    ) count++;
    if (selectedTypes.length !== allTypeCodes.length) count++;
    if (selectedAreas.length > 0) count++; // Area is active when any specific areas selected
    return count;
  }, [
    selectedCategories, maxKm, selectedHistoricUse, selectedCurrentUse,
    selectedConditions, deselectedLoggedConditions, showNotLogged, hasLogUser, logUser, selectedTypes,
    selectedAreas, allTypeCodes.length, allConditionCodes.length,
    allHistoricUseValues.length, allCurrentUseValues.length
  ]);

  return (
    <>
      <title>Trigpoints | TrigpointingUK</title>
      <div className="max-w-7xl mx-auto">
        {/* Main Filter Panel */}
        <Card className={filtersCollapsed ? "mb-3 p-0!" : "mb-6"}>
          <div className={filtersCollapsed ? "px-3 py-1.5" : "p-4"}>
            {/* Hidden rather than unmounted when collapsed, so the chips keep
                any state of their own */}
            <div id="trigs-filter-rows" hidden={filtersCollapsed}>
            {/* Row 1: Location chips */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
                {/* Collapse at the top of the open form; expand is on the results row */}
                <button
                  type="button"
                  onClick={toggleFiltersCollapsed}
                  aria-expanded={true}
                  aria-controls="trigs-filter-rows"
                  aria-label="Hide filters"
                  title="Hide filters"
                  className={FILTER_TOGGLE_CLASSES}
                >
                  <ChevronUp className="w-5 h-5" />
                </button>
                <MapPin className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Location
                </span>
              </div>
              
              {/* Location chips */}
              <div className="flex flex-wrap gap-2">
                <LocationChip
                  locationName={locationName}
                  lat={centerLat}
                  lon={centerLon}
                  onSelectLocation={handleSelectLocation}
                />
                
                <RadiusChip
                  maxKm={maxKm}
                  onChange={setMaxKm}
                  disabled={centerLat === null}
                />
              </div>
            </div>

            {/* Row 2: Filter chips */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <div className="flex items-center gap-2 mb-3">
                <Filter className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Filters
                </span>
                {activeFilterCount > 0 && (
                  <span className="px-2 py-0.5 text-xs font-medium bg-trig-green-100 dark:bg-trig-green-900/30 text-trig-green-700 dark:text-trig-green-300 rounded-full">
                    {activeFilterCount} active
                  </span>
                )}
                {activeFilterCount > 0 && (
                  <button
                    type="button"
                    onClick={handleClearAllFilters}
                    className="ml-auto text-sm text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 flex items-center gap-1"
                  >
                    <RotateCcw className="w-3.5 h-3.5" />
                    Clear all
                  </button>
                )}
              </div>
              
              {/* Filter chips grid */}
              <div className="flex flex-wrap gap-2">
                <TypeChip
                  selectedTypes={selectedTypes}
                  selectedCategories={selectedCategories}
                  onToggleType={handleToggleType}
                  onToggleCategory={handleToggleCategory}
                  onSelectAll={() => setSelectedTypes([...allTypeCodes])}
                  onSelectNone={() => setSelectedTypes([])}
                />

                <HistoricUseChip
                  selectedValues={selectedHistoricUse}
                  onToggle={handleToggleHistoricUse}
                  onSelectAll={() => setSelectedHistoricUse([...allHistoricUseValues])}
                  onSelectNone={() => setSelectedHistoricUse([])}
                />
                
                <CurrentUseChip
                  selectedValues={selectedCurrentUse}
                  onToggle={handleToggleCurrentUse}
                  onSelectAll={() => setSelectedCurrentUse([...allCurrentUseValues])}
                  onSelectNone={() => setSelectedCurrentUse([])}
                />
                
                <ConditionChip
                  selectedConditions={selectedConditions}
                  onToggle={handleToggleCondition}
                  onSelectAll={() => setSelectedConditions([...allConditionCodes])}
                  onSelectNone={() => setSelectedConditions([])}
                />
                
                <LogsChip
                  selectedLoggedConditions={selectedLoggedConditions}
                  showNotLogged={showNotLogged}
                  onToggleLoggedCondition={handleToggleLoggedCondition}
                  onToggleNotLogged={() => setShowNotLogged((prev) => !prev)}
                  onSelectAllLogged={() => setDeselectedLoggedConditions([])}
                  onSelectNoneLogged={() => setDeselectedLoggedConditions([...allConditionCodes])}
                  isAuthenticated={isAuthenticated}
                  logUser={logUser}
                  onLogUserChange={handleLogUserChange}
                />
                
                {/* Area chip */}
                <AreaChip
                  selectedAreas={selectedAreas}
                  onToggleArea={handleToggleArea}
                  onClear={() => setSelectedAreas([])}
                  centerLat={centerLat}
                  centerLon={centerLon}
                  containingAreaId={null}
                />
              </div>
            </div>

            {/* Row 3: Sort chips */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <div className="flex items-center gap-2 mb-3">
                <ArrowUpDown className="w-4 h-4 text-gray-400" />
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Sort
                </span>
              </div>
              
              {/* Sort chips */}
              <div className="flex flex-wrap gap-2">
                <SortChip
                  label="Distance"
                  sortKey="distance"
                  activeSortKey={effectiveSortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<MapPin className="w-3.5 h-3.5" />}
                  requiresLocation
                  hasLocation={centerLat !== null}
                />
                
                <SortChip
                  label="Alphabetically"
                  sortKey="name"
                  activeSortKey={effectiveSortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<SortAsc className="w-3.5 h-3.5" />}
                />
                
                <SortChip
                  label="Score"
                  sortKey="score"
                  activeSortKey={effectiveSortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<Trophy className="w-3.5 h-3.5" />}
                />
                
                <SortChip
                  label="Height"
                  sortKey="height"
                  activeSortKey={effectiveSortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<Mountain className="w-3.5 h-3.5" />}
                />

                <SortChip
                  label="Logged date"
                  sortKey="logged"
                  activeSortKey={effectiveSortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<CalendarCheck className="w-3.5 h-3.5" />}
                  disabled={!hasLogUser}
                  disabledReason="Sign in, or pick a user in the Logs filter"
                />
              </div>
            </div>

            </div>

            {/* Results summary */}
            <div
              className={`flex flex-wrap items-center justify-between gap-3 ${
                filtersCollapsed ? "" : "mt-4 pt-4 border-t border-gray-200 dark:border-gray-700"
              }`}
            >
              <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                {filtersCollapsed && (
                  <button
                    type="button"
                    onClick={toggleFiltersCollapsed}
                    aria-expanded={false}
                    aria-controls="trigs-filter-rows"
                    aria-label="Show filters"
                    title="Show filters"
                    className={FILTER_TOGGLE_CLASSES}
                  >
                    <ChevronDown className="w-5 h-5" />
                  </button>
                )}
                {filtersCollapsed && activeFilterCount > 0 && (
                  <span className="shrink-0 px-2 py-0.5 text-xs font-medium bg-trig-green-100 dark:bg-trig-green-900/30 text-trig-green-700 dark:text-trig-green-300 rounded-full">
                    {activeFilterCount} {activeFilterCount === 1 ? "filter" : "filters"}
                  </span>
                )}
                {isLoading || centerLat === null || centerLon === null ? (
                  <span>Loading...</span>
                ) : (
                  <span>
                    <strong>{totalCount.toLocaleString("en-GB")}</strong> trigpoints
                    {maxKm !== null && locationName && ` within ${maxKm} km of ${locationName}`}
                    {logUser && ` · logs by ${logUser.name}`}
                    {view === "list" && totalCount > allTrigs.length && (
                      <> · showing {allTrigs.length.toLocaleString("en-GB")}</>
                    )}
                  </span>
                )}
              </div>

              <div className="flex items-center gap-2">
                {/* List / map toggle */}
                <div className="inline-flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden" role="group" aria-label="View">
                  {([
                    { value: "list", label: "List", Icon: List },
                    { value: "map", label: "Map", Icon: MapIcon },
                  ] as const).map(({ value, label, Icon }) => (
                    <button
                      key={value}
                      type="button"
                      onClick={() => {
                        // Map again while on the map: zoom back out to fit all the trigs
                        if (value === "map" && view === "map") setMapFitRequest((n) => n + 1);
                        setView(value);
                      }}
                      aria-pressed={view === value}
                      aria-label={label}
                      className={`inline-flex items-center gap-1.5 px-3 py-1.5 text-sm font-medium transition-colors ${
                        view === value
                          ? "bg-trig-green-50 dark:bg-trig-green-900/30 text-trig-green-700 dark:text-trig-green-300"
                          : "bg-white dark:bg-gray-800 text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700"
                      }`}
                    >
                      <Icon className="w-4 h-4" />
                      <span className="hidden sm:inline">{label}</span>
                    </button>
                  ))}
                </div>

                {isAuthenticated && (
                  <DownloadButton
                    filterParams={buildTrigFilterParams(filterOptions)}
                    order={orderParam}
                    logUserName={logUser?.name}
                    variant="subtle"
                  />
                )}
              </div>
            </div>
          </div>
        </Card>

        {view === "map" && (
          <TrigsV2Map
            trigs={mapPoints?.trigs ?? []}
            isLoading={isMapLoading}
            error={mapError}
            truncated={mapPoints?.truncated ?? false}
            showListActions={showListActions}
            areaIds={selectedAreaIds}
            fitRequest={mapFitRequest}
            centre={
              centerLat !== null && centerLon !== null
                ? { lat: centerLat, lon: centerLon, name: locationName }
                : undefined
            }
          />
        )}

        {/* Trigpoint List */}
        {view === "list" && (
          <div>
            {error && (
              <div className="mx-4 mt-4 p-4 bg-red-50 dark:bg-red-900/30 border border-red-200 dark:border-red-800 rounded-lg text-red-700 dark:text-red-300">
                Error loading trigpoints: {error.message}
              </div>
            )}

            {!isLoading && allTrigs.length === 0 && (
              <div className="mx-4 mt-8 text-center py-12">
                <div className="text-gray-400 dark:text-gray-500 text-5xl mb-4">📍</div>
                <h3 className="text-lg font-medium text-gray-900 dark:text-gray-100 mb-2">
                  No trigpoints found
                </h3>
                <p className="text-gray-500 dark:text-gray-400">
                  Try adjusting your filters or selecting a different location.
                </p>
              </div>
            )}

            {allTrigs.length > 0 && (
              <>
                {/* Trigpoint cards */}
                <div className="bg-white dark:bg-gray-800 mx-4 mt-4 rounded-lg shadow dark:shadow-gray-900/50 overflow-hidden">
                  {allTrigs.map((trig, index) => (
                    <TrigCard
                      key={trig.id}
                      trig={trig}
                      position={
                        showPositions
                          ? sortDirection === "asc" ? index + 1 : totalCount - index
                          : undefined
                      }
                      firstLoggedDate={trig.first_logged_date}
                      showDistance={centerLat !== null && centerLon !== null}
                      centerLat={centerLat ?? 0}
                      centerLon={centerLon ?? 0}
                      distanceUnit={(userProfile?.prefs?.distance_ind as 'K' | 'M') || 'K'}
                      logStatus={getLogStatus(trig.id)}
                      actions={showListActions ? <AddToListButton trigId={trig.id} /> : undefined}
                    />
                  ))}
                </div>

                {/* Infinite scroll sentinel */}
                {hasNextPage && <div ref={sentinelRef} className="h-px" />}

                {/* Loading indicator */}
                {isFetchingNextPage && (
                  <div className="mx-4 my-6 text-center">
                    <div className="inline-block animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600 dark:border-blue-400"></div>
                    <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">Loading more...</p>
                  </div>
                )}
              </>
            )}

            {/* Initial loading indicator */}
            {isLoading && (
              <div className="mx-4 my-12 text-center">
                <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 dark:border-blue-400"></div>
                <p className="mt-4 text-gray-500 dark:text-gray-400">Loading trigpoints...</p>
              </div>
            )}
          </div>
        )}
      </div>
    </>
  );
}
