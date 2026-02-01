/**
 * TrigsV2 - Experimental trigpoints browser with filter chips UI
 * 
 * This is an experimental version of the /trigs page using a filter chips
 * approach instead of the traditional filter panel. The goal is to evaluate
 * whether this UX pattern works better for the variety of filters we need.
 * 
 * ⚠️ Note: This is experimental and uses mock data for some filters.
 * Not all filters are wired up to the backend yet.
 */

import { useState, useCallback, useEffect, useRef, useMemo } from "react";
import { useSearchParams, Link } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";
import { FlaskConical, RotateCcw, Filter, ArrowUpDown, MapPin, SortAsc, Trophy, Mountain, HelpCircle } from "lucide-react";

import Layout from "../../components/layout/Layout";
import Card from "../../components/ui/Card";
import { TrigCard } from "../../components/trigs/TrigCard";
import { useInfiniteTrigs } from "../../hooks/useInfiniteTrigs";
import { useUserLoggedTrigs } from "../../hooks/useUserLoggedTrigs";
import { useUserProfile } from "../../hooks/useUserProfile";
import type { UserLogStatus } from "../../lib/mapIcons";

// Import all our filter chips
import {
  LocationChip,
  CategoryChip,
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
  HISTORIC_USE_VALUES,
  CURRENT_USE_VALUES,
  CONDITION_VALUES,
  ALL_TYPE_CODES,
  HISTORIC_COUNTIES,
  MOCK_AREAS,
  ALL_LOGGED_CONDITION_CODES,
  type SortDirection,
} from "../../components/experiment/chips";

// Default location: Buxton
const DEFAULT_LAT = 53.2585;
const DEFAULT_LON = -1.9106;
const DEFAULT_LOCATION_NAME = "Buxton";
const ALL_AREA_IDS = Object.values(MOCK_AREAS).flat().map((area) => area.id);
const ALL_COUNTY_IDS = HISTORIC_COUNTIES.map((county) => county.id);

export default function TrigsV2() {
  const [searchParams] = useSearchParams();
  const { isAuthenticated } = useAuth0();
  
  // Fetch user profile to get preferences
  const { data: userProfile } = useUserProfile("me");
  
  // Fetch user's logged trigpoints for badge indicator
  const { data: loggedTrigsMap } = useUserLoggedTrigs();

  // Track if we've attempted to get user location
  const locationAttemptedRef = useRef(false);

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
    const statuses = searchParams.get("statuses");
    if (statuses) return statuses.split(",").map(Number);
    return [10, 20]; // Default to Pillar + FBM
  });

  // Distance/radius
  const DEFAULT_MAX_KM = 200;
  const [maxKm, setMaxKm] = useState<number | null>(() => {
    const km = searchParams.get("maxKm");
    return km ? parseInt(km, 10) : DEFAULT_MAX_KM;
  });

  // Historic use filter (from trig.historic_use)
  const [selectedHistoricUse, setSelectedHistoricUse] = useState<string[]>(
    () => HISTORIC_USE_VALUES.map((v) => v.value)
  );

  // Current/recent use filter (from trig.current_use)
  const [selectedCurrentUse, setSelectedCurrentUse] = useState<string[]>(
    () => CURRENT_USE_VALUES.map((v) => v.value)
  );

  // Condition filter
  const [selectedConditions, setSelectedConditions] = useState<string[]>(
    () => CONDITION_VALUES.map((v) => v.code)
  );

  // My logs filter - now with individual conditions for logged trigs
  const [selectedLoggedConditions, setSelectedLoggedConditions] = useState<string[]>(
    () => [...ALL_LOGGED_CONDITION_CODES]
  );
  const [showNotLogged, setShowNotLogged] = useState<boolean>(true);

  // Handlers for logged conditions
  const handleToggleLoggedCondition = useCallback((code: string) => {
    setSelectedLoggedConditions((prev) =>
      prev.includes(code)
        ? prev.filter((c) => c !== code)
        : [...prev, code]
    );
  }, []);

  // Type filter (detailed types within categories)
  const [selectedTypes, setSelectedTypes] = useState<string[]>(
    () => [...ALL_TYPE_CODES]
  );

  // Area filter (for full area chip) - start with all selected (unfiltered)
  const [selectedAreaIds, setSelectedAreaIds] = useState<number[]>(
    () => [...ALL_AREA_IDS]
  );

  // Historic county filter (for dedicated county chip) - start with all selected (unfiltered)
  const [selectedCountyIds, setSelectedCountyIds] = useState<number[]>(
    () => [...ALL_COUNTY_IDS]
  );

  // ==========================================================================
  // Sort State
  // ==========================================================================
  
  // Sort key: "distance" | "name" | "score" | "height"
  const [sortKey, setSortKey] = useState<string>("distance");
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");

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
    setSelectedHistoricUse(HISTORIC_USE_VALUES.map((v) => v.value));
    setSelectedCurrentUse(CURRENT_USE_VALUES.map((v) => v.value));
    setSelectedConditions(CONDITION_VALUES.map((v) => v.code));
    setSelectedLoggedConditions([...ALL_LOGGED_CONDITION_CODES]);
    setShowNotLogged(true);
    setSelectedTypes([...ALL_TYPE_CODES]);
    setSelectedAreaIds([...ALL_AREA_IDS]);
    setSelectedCountyIds([...ALL_COUNTY_IDS]);
  }, []);

  // ==========================================================================
  // Data Fetching
  // ==========================================================================

  // For now, only use the filters that are supported by the existing API
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
    showLogged: selectedLoggedConditions.length > 0,
    showNotLogged,
    maxKm: maxKm ?? undefined,
    // Note: historic_use, current_use, condition, type, area filters
    // are NOT yet supported by the API - they'll need backend work
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
  const activeFilterCount = useMemo(() => {
    let count = 0;
    if (selectedCategories.length !== ALL_CATEGORY_IDS.length) count++;
    if (maxKm !== null) count++;
    if (selectedHistoricUse.length !== HISTORIC_USE_VALUES.length) count++;
    if (selectedCurrentUse.length !== CURRENT_USE_VALUES.length) count++;
    if (selectedConditions.length !== CONDITION_VALUES.length) count++;
    if (selectedLoggedConditions.length !== ALL_LOGGED_CONDITION_CODES.length || !showNotLogged) count++;
    if (selectedTypes.length !== ALL_TYPE_CODES.length) count++;
    if (selectedAreaIds.length !== ALL_AREA_IDS.length) count++;
    if (selectedCountyIds.length !== ALL_COUNTY_IDS.length) count++;
    return count;
  }, [
    selectedCategories, maxKm, selectedHistoricUse, selectedCurrentUse,
    selectedConditions, selectedLoggedConditions, showNotLogged, selectedTypes,
    selectedAreaIds, selectedCountyIds
  ]);

  return (
    <Layout>
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
            for the trigs browser. Not all filters are connected to the backend yet - some show 
            mock data. <Link to="/experiment" className="underline hover:text-amber-600">View all experiments</Link>
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
                <CategoryChip
                  selectedCategories={selectedCategories}
                  onToggleCategory={handleToggleCategory}
                  onSelectAll={() => setSelectedCategories(ALL_CATEGORY_IDS)}
                  onSelectNone={() => setSelectedCategories([])}
                />

                <HistoricUseChip
                  selectedValues={selectedHistoricUse}
                  onToggle={handleToggleHistoricUse}
                  onSelectAll={() => setSelectedHistoricUse(HISTORIC_USE_VALUES.map((v) => v.value))}
                  onSelectNone={() => setSelectedHistoricUse([])}
                />
                
                <CurrentUseChip
                  selectedValues={selectedCurrentUse}
                  onToggle={handleToggleCurrentUse}
                  onSelectAll={() => setSelectedCurrentUse(CURRENT_USE_VALUES.map((v) => v.value))}
                  onSelectNone={() => setSelectedCurrentUse([])}
                />
                
                <ConditionChip
                  selectedConditions={selectedConditions}
                  onToggle={handleToggleCondition}
                  onSelectAll={() => setSelectedConditions(CONDITION_VALUES.map((v) => v.code))}
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
                
                <TypeChip
                  selectedTypes={selectedTypes}
                  selectedCategories={selectedCategories}
                  onToggleType={handleToggleType}
                  onToggleCategory={handleToggleCategory}
                  onSelectAll={() => setSelectedTypes([...ALL_TYPE_CODES])}
                  onSelectNone={() => setSelectedTypes([])}
                />
                
                {/* Area chips */}
                <AreaChip
                  selectedAreaIds={selectedAreaIds}
                  onToggleArea={handleToggleArea}
                  onSelectAll={() => setSelectedAreaIds([...ALL_AREA_IDS])}
                  onSelectNone={() => setSelectedAreaIds([])}
                  centerLat={centerLat}
                  centerLon={centerLon}
                  containingAreaId={null} // Would come from API
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
                  containingCountyId={null} // Would come from API
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
              
              {/* Backend filter warning */}
              <div className="text-xs text-amber-600 dark:text-amber-400">
                ⚠️ Some filters (historic use, condition, type, area) are not yet connected to backend
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
    </Layout>
  );
}

