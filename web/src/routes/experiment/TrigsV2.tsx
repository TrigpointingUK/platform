/**
 * TrigsV2 - Experimental trigpoints browser with filter chips UI
 * 
 * This is an experimental version of the /trigs page using a filter chips
 * approach instead of the traditional filter panel. The goal is to evaluate
 * whether this UX pattern works better for the variety of filters we need.
 */

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { Filter, RotateCcw, FlaskConical, HelpCircle, ArrowUpDown, Mountain, Trophy, SortAsc, MapPin } from "lucide-react";

import Card from "../../components/ui/Card";
import { TrigCard } from "../../components/trigs/TrigCard";
import { useInfiniteTrigs } from "../../hooks/useInfiniteTrigs";
import { useUserLoggedTrigs } from "../../hooks/useUserLoggedTrigs";
import { useUserProfile } from "../../hooks/useUserProfile";
import type { UserLogStatus } from "../../lib/mapIcons";

// Import reference data hooks
import {
  useTrigCategories,
  useConditions,
  useHistoricUseValues,
  useCurrentUseValues,
} from "../../hooks/useReferenceData";

// Import filter chips
import {
  LocationChip,
  RadiusChip,
  HistoricUseChip,
  CurrentUseChip,
  ConditionChip,
  MyLogsChip,
  TypeChip,
  AreaChip,
  HistoricCountyChip,
  SortChip,
  ALL_CATEGORY_IDS,
  HISTORIC_COUNTIES,
  ALL_LOGGED_CONDITION_CODES,
  type SortDirection,
} from "../../components/experiment/chips";

// Default location: Buxton
const DEFAULT_LAT = 53.2585;
const DEFAULT_LON = -1.9106;
const DEFAULT_LOCATION_NAME = "Buxton";
const DEFAULT_MAX_KM = 200;

// Get all county IDs for the historic county chip (still using mock data)
const ALL_COUNTY_IDS = HISTORIC_COUNTIES.map((county) => county.id);

export default function TrigsV2() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth0();
  
  // Fetch user profile to get preferences
  const { data: userProfile } = useUserProfile("me");
  
  // Fetch user's logged trigpoints for badge indicator
  const { data: loggedTrigsMap } = useUserLoggedTrigs();

  // Track if we've attempted to get user location
  const locationAttemptedRef = useRef(false);
  
  // Track if we've initialized filters from API data
  const filtersInitializedRef = useRef(false);

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

  // Location
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

  // Categories (status IDs: 10=Pillar, 20=FBM, etc.)
  const [selectedCategories, setSelectedCategories] = useState<number[]>(() => {
    const categories = searchParams.get("categories");
    if (categories) return categories.split(",").map(Number).filter((n) => !isNaN(n));
    return [...ALL_CATEGORY_IDS]; // Default to all categories
  });

  // Distance/radius
  const [maxKm, setMaxKm] = useState<number | null>(() => {
    const km = searchParams.get("maxKm");
    return km ? parseInt(km, 10) : DEFAULT_MAX_KM;
  });

  // Historic use filter - starts empty, populated when API data loads
  const [selectedHistoricUse, setSelectedHistoricUse] = useState<string[]>([]);

  // Current/recent use filter - starts empty, populated when API data loads
  const [selectedCurrentUse, setSelectedCurrentUse] = useState<string[]>([]);

  // Condition filter - starts empty, populated when API data loads
  const [selectedConditions, setSelectedConditions] = useState<string[]>([]);

  // Type filter - starts empty, populated when API data loads
  const [selectedTypes, setSelectedTypes] = useState<string[]>([]);

  // My logs filter - now with individual conditions for logged trigs
  const [selectedLoggedConditions, setSelectedLoggedConditions] = useState<string[]>(
    () => [...ALL_LOGGED_CONDITION_CODES]
  );
  const [showNotLogged, setShowNotLogged] = useState<boolean>(true);

  // Area filter (for full area chip) - start with empty (will be managed by chip)
  const [selectedAreaIds, setSelectedAreaIds] = useState<number[]>([]);

  // Historic county filter (for dedicated county chip) - start with all selected
  const [selectedCountyIds, setSelectedCountyIds] = useState<number[]>(
    () => [...ALL_COUNTY_IDS]
  );

  // ==========================================================================
  // Initialize filters when API data loads
  // ==========================================================================
  
  useEffect(() => {
    if (filtersInitializedRef.current) return;
    
    // Wait until all reference data is loaded
    if (!categories || !conditions || !historicUseValues || !currentUseValues) return;
    
    filtersInitializedRef.current = true;
    
    // Check URL params for types filter
    const typesParam = searchParams.get("types");
    if (typesParam) {
      const urlTypes = typesParam.split(",").filter((t) => allTypeCodes.includes(t));
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Initialising state from URL params on first data load
      setSelectedTypes(urlTypes.length > 0 ? urlTypes : allTypeCodes);
    } else {
      setSelectedTypes(allTypeCodes);
    }
    
    // Initialize other filters to "all" (unfiltered) state
    setSelectedConditions(allConditionCodes);
    setSelectedHistoricUse(allHistoricUseValues);
    setSelectedCurrentUse(allCurrentUseValues);
  }, [categories, conditions, historicUseValues, currentUseValues, allTypeCodes, allConditionCodes, allHistoricUseValues, allCurrentUseValues, searchParams]);

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
        setLocationName("Current location");
      },
      () => {
        setCenterLat(DEFAULT_LAT);
        setCenterLon(DEFAULT_LON);
        setLocationName(DEFAULT_LOCATION_NAME);
      }
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
    setSelectedLoggedConditions((prev) =>
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

  const handleToggleArea = useCallback((areaId: number) => {
    setSelectedAreaIds((prev) => {
      if (prev.includes(areaId)) {
        return prev.filter((a) => a !== areaId);
      } else {
        return [...prev, areaId];
      }
    });
  }, []);

  const handleToggleCounty = useCallback((countyId: number) => {
    setSelectedCountyIds((prev) => {
      if (prev.includes(countyId)) {
        return prev.filter((c) => c !== countyId);
      } else {
        return [...prev, countyId];
      }
    });
  }, []);

  const handleClearAllFilters = useCallback(() => {
    setSelectedCategories(ALL_CATEGORY_IDS);
    setMaxKm(DEFAULT_MAX_KM);
    setSelectedHistoricUse(allHistoricUseValues);
    setSelectedCurrentUse(allCurrentUseValues);
    setSelectedConditions(allConditionCodes);
    setSelectedLoggedConditions([...ALL_LOGGED_CONDITION_CODES]);
    setShowNotLogged(true);
    setSelectedTypes(allTypeCodes);
    setSelectedAreaIds([]); // Area chip manages its own "all" state
    setSelectedCountyIds([...ALL_COUNTY_IDS]);
  }, [allTypeCodes, allConditionCodes, allHistoricUseValues, allCurrentUseValues]);

  // ==========================================================================
  // URL Parameter Sync
  // ==========================================================================
  
  // Update URL when filter/sort state changes
  useEffect(() => {
    const params = new URLSearchParams();
    
    // Location
    if (centerLat !== null) {
      params.set("lat", centerLat.toFixed(5));
    }
    if (centerLon !== null) {
      params.set("lon", centerLon.toFixed(5));
    }
    if (locationName) {
      params.set("location", locationName);
    }
    
    // Radius (only if not default)
    if (maxKm !== null && maxKm !== DEFAULT_MAX_KM) {
      params.set("maxKm", maxKm.toString());
    }
    
    // Sort (only if not default)
    if (sortKey !== "distance") {
      params.set("sort", sortKey);
    }
    if (sortDirection !== "asc") {
      params.set("dir", sortDirection);
    }
    
    // Categories (only if not all selected)
    if (selectedCategories.length > 0 && selectedCategories.length < ALL_CATEGORY_IDS.length) {
      params.set("categories", selectedCategories.join(","));
    }
    
    // Types (only if filtering and not all selected)
    if (selectedTypes.length > 0 && selectedTypes.length < allTypeCodes.length) {
      params.set("types", selectedTypes.join(","));
    }
    
    // Update URL without triggering navigation
    setSearchParams(params, { replace: true });
  }, [
    centerLat, centerLon, locationName, maxKm, sortKey, sortDirection,
    selectedCategories, selectedTypes, allTypeCodes.length, setSearchParams
  ]);

  // ==========================================================================
  // Data Fetching
  // ==========================================================================

  // Build order string with direction prefix
  const orderParam = sortDirection === "desc" ? `-${sortKey}` : sortKey;

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
    statusIds: selectedCategories.length > 0 ? selectedCategories : undefined,
    types: typesFilter,
    historicUse: historicUseFilter,
    currentUse: currentUseFilter,
    conditions: conditionsFilter,
    showLogged: selectedLoggedConditions.length > 0,
    showNotLogged,
    loggedConditions: selectedLoggedConditions.length > 0 ? selectedLoggedConditions : undefined,
    maxKm: maxKm ?? undefined,
    order: orderParam,
    areaIds: selectedAreaIds.length > 0 ? selectedAreaIds : undefined,
  });

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
    if (selectedLoggedConditions.length !== ALL_LOGGED_CONDITION_CODES.length || !showNotLogged) count++;
    if (selectedTypes.length !== allTypeCodes.length) count++;
    if (selectedAreaIds.length > 0) count++; // Area is active when any specific areas selected
    if (selectedCountyIds.length !== ALL_COUNTY_IDS.length) count++;
    return count;
  }, [
    selectedCategories, maxKm, selectedHistoricUse, selectedCurrentUse,
    selectedConditions, selectedLoggedConditions, showNotLogged, selectedTypes,
    selectedAreaIds, selectedCountyIds, allTypeCodes.length, allConditionCodes.length,
    allHistoricUseValues.length, allCurrentUseValues.length
  ]);

  return (
    <>
      <title>Trigs v2 (Experiment) | TrigpointingUK</title>
      <div className="max-w-7xl mx-auto">
        {/* Page Header */}
        <div className="mb-6">
          <div className="flex items-center gap-3 mb-2">
            <div className="p-2 bg-gradient-to-br from-amber-400 to-orange-500 rounded-lg">
              <FlaskConical className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Trigs v2 <span className="text-amber-600 dark:text-amber-400">(Experiment)</span>
              </h1>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Exploring filter chips UI pattern
              </p>
            </div>
          </div>
          
          {/* Experiment notice */}
          <div className="p-3 bg-amber-50 dark:bg-amber-900/20 border border-amber-200 dark:border-amber-800 rounded-lg text-sm text-amber-800 dark:text-amber-200">
            <strong>This is an experimental page.</strong> We're testing a filter chips approach 
            for the trigs browser. <Link to="/experiment" className="underline hover:text-amber-600">View all experiments</Link>
          </div>
        </div>

        {/* Main Filter Panel */}
        <Card className="mb-6">
          <div className="p-4">
            {/* Row 1: Location chips */}
            <div className="mb-4">
              <div className="flex items-center gap-2 mb-3">
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
                
                <MyLogsChip
                  selectedLoggedConditions={selectedLoggedConditions}
                  showNotLogged={showNotLogged}
                  onToggleLoggedCondition={handleToggleLoggedCondition}
                  onToggleNotLogged={() => setShowNotLogged((prev) => !prev)}
                  onSelectAllLogged={() => setSelectedLoggedConditions([...ALL_LOGGED_CONDITION_CODES])}
                  onSelectNoneLogged={() => setSelectedLoggedConditions([])}
                  isAuthenticated={isAuthenticated}
                />
                
                {/* Area chip */}
                <AreaChip
                  selectedAreaIds={selectedAreaIds}
                  onToggleArea={handleToggleArea}
                  onClear={() => setSelectedAreaIds([])}
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
                  activeSortKey={sortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<MapPin className="w-3.5 h-3.5" />}
                  requiresLocation
                  hasLocation={centerLat !== null}
                />
                
                <SortChip
                  label="Alphabetically"
                  sortKey="name"
                  activeSortKey={sortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<SortAsc className="w-3.5 h-3.5" />}
                />
                
                <SortChip
                  label="Score"
                  sortKey="score"
                  activeSortKey={sortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<Trophy className="w-3.5 h-3.5" />}
                />
                
                <SortChip
                  label="Height"
                  sortKey="height"
                  activeSortKey={sortKey}
                  sortDirection={sortDirection}
                  onSort={handleSort}
                  icon={<Mountain className="w-3.5 h-3.5" />}
                />
              </div>
            </div>

            {/* Row 4: Alternatives - chips under consideration */}
            <div className="border-t border-gray-200 dark:border-gray-700 pt-4">
              <div className="flex items-center gap-2 mb-3">
                <HelpCircle className="w-4 h-4 text-amber-500" />
                <span className="text-sm font-medium text-amber-600 dark:text-amber-400">
                  Alternatives
                </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  (seeking feedback on these)
                </span>
              </div>
              
              {/* Alternative chips */}
              <div className="flex flex-wrap gap-2">
                <HistoricCountyChip
                  selectedCountyIds={selectedCountyIds}
                  onToggleCounty={handleToggleCounty}
                  onSelectAll={() => setSelectedCountyIds([...ALL_COUNTY_IDS])}
                  onSelectNone={() => setSelectedCountyIds([])}
                  containingCountyId={null}
                />
              </div>
            </div>

            {/* Results summary */}
            <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700 flex items-center justify-between">
              <div className="text-sm text-gray-600 dark:text-gray-400">
                {isLoading || centerLat === null || centerLon === null ? (
                  <span>Loading...</span>
                ) : (
                  <span>
                    Showing <strong>{allTrigs.length}</strong> of <strong>{totalCount}</strong> trigpoints
                    {locationName && ` near ${locationName}`}
                  </span>
                )}
              </div>
            </div>
          </div>
        </Card>

        {/* Trigpoint List */}
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
      </div>
    </>
  );
}
