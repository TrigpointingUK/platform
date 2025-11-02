import { useState, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { useInfiniteTrigs } from "../hooks/useInfiniteTrigs";
import { LocationSearch } from "../components/trigs/LocationSearch";
import { PhysicalTypeFilter } from "../components/trigs/PhysicalTypeFilter";
import { TrigCard } from "../components/trigs/TrigCard";
import { useAuth0 } from "@auth0/auth0-react";

// Default location: Buxton
const DEFAULT_LAT = 53.2585;
const DEFAULT_LON = -1.9106;
const DEFAULT_LOCATION_NAME = "Buxton";

// All physical types (default: all enabled)
const ALL_PHYSICAL_TYPES = [
  "Pillar",
  "Bolt",
  "FBM",
  "Passive Station",
  "Active Station",
  "Intersection",
  "Other",
];

export default function FindTrigs() {
  const [searchParams, setSearchParams] = useSearchParams();
  const { isAuthenticated } = useAuth0();

  // Parse URL params or use defaults
  const [centerLat, setCenterLat] = useState<number>(
    () => parseFloat(searchParams.get("lat") || "") || DEFAULT_LAT
  );
  const [centerLon, setCenterLon] = useState<number>(
    () => parseFloat(searchParams.get("lon") || "") || DEFAULT_LON
  );
  const [locationName, setLocationName] = useState<string>(
    () => searchParams.get("location") || DEFAULT_LOCATION_NAME
  );
  
  const [selectedPhysicalTypes, setSelectedPhysicalTypes] = useState<string[]>(
    () => {
      const types = searchParams.get("types");
      return types ? types.split(",") : ALL_PHYSICAL_TYPES;
    }
  );
  
  const [excludeFound, setExcludeFound] = useState<boolean>(
    () => searchParams.get("excludeFound") === "true"
  );

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();
    params.set("lat", centerLat.toString());
    params.set("lon", centerLon.toString());
    params.set("location", locationName);
    
    if (selectedPhysicalTypes.length !== ALL_PHYSICAL_TYPES.length) {
      params.set("types", selectedPhysicalTypes.join(","));
    }
    
    if (excludeFound) {
      params.set("excludeFound", "true");
    }
    
    setSearchParams(params, { replace: true });
  }, [centerLat, centerLon, locationName, selectedPhysicalTypes, excludeFound, setSearchParams]);

  // Fetch trigpoints with current filters
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteTrigs({
    lat: centerLat,
    lon: centerLon,
    physicalTypes: selectedPhysicalTypes.length > 0 ? selectedPhysicalTypes : undefined,
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
    setCenterLat(DEFAULT_LAT);
    setCenterLon(DEFAULT_LON);
    setLocationName(DEFAULT_LOCATION_NAME);
  }, []);

  const allTrigs = data?.pages.flatMap((page) => page.items) || [];
  const totalCount = data?.pages[0]?.pagination.total || 0;

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Fixed filter header */}
      <div className="bg-white border-b border-gray-200 sticky top-0 z-10 shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 space-y-4">
          <h1 className="text-2xl font-bold text-gray-900">Find Trigpoints</h1>
          
          {/* Location search */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Location
            </label>
            <LocationSearch
              onSelectLocation={handleSelectLocation}
              defaultLocation={{
                lat: centerLat,
                lon: centerLon,
                name: locationName,
              }}
            />
          </div>

          {/* Physical type filter */}
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-2">
              Physical Types
            </label>
            <PhysicalTypeFilter
              selectedTypes={selectedPhysicalTypes}
              onToggleType={handleTogglePhysicalType}
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
            {isLoading ? (
              <span>Loading...</span>
            ) : (
              <span>
                Showing {allTrigs.length} of {totalCount} trigpoints
                {centerLat && centerLon && ` near ${locationName}`}
              </span>
            )}
          </div>
        </div>
      </div>

      {/* Trigpoint list */}
      <div className="max-w-7xl mx-auto">
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
          <div className="bg-white mx-4 mt-4 rounded-lg shadow overflow-hidden">
            {allTrigs.map((trig) => (
              <TrigCard
                key={trig.id}
                trig={trig}
                showDistance={!!centerLat && !!centerLon}
              />
            ))}
          </div>
        )}

        {/* Load more button */}
        {hasNextPage && (
          <div className="mx-4 my-6 text-center">
            <button
              type="button"
              onClick={() => fetchNextPage()}
              disabled={isFetchingNextPage}
              className="px-6 py-3 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors font-medium"
            >
              {isFetchingNextPage ? "Loading..." : "Load More"}
            </button>
          </div>
        )}

        {/* Loading indicator */}
        {isLoading && (
          <div className="mx-4 my-12 text-center">
            <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"></div>
            <p className="mt-4 text-gray-500">Loading trigpoints...</p>
          </div>
        )}
      </div>
    </div>
  );
}

