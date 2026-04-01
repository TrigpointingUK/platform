/**
 * AreaChip - Full-featured filter chip for geographic areas
 * 
 * Features:
 * - Area type selector at top
 * - Toggleable list of all areas of that type
 * - Sort by alphabetical or distance from search location
 * - Current location's area highlighted at top
 */

import { useState, useMemo, useEffect } from "react";
import { MapIcon, SortAsc, Navigation, Loader2 } from "lucide-react";
import { FilterChip, FilterListItem } from "../FilterChip";
import { useAreaTypes, useAreasByType } from "../../../hooks/useReferenceData";

type SortMode = "name" | "distance";

export interface AreaChipProps {
  selectedAreaIds: number[];
  onToggleArea: (areaId: number) => void;
  onClear: () => void;
  /** Current search location for distance sorting */
  centerLat?: number | null;
  centerLon?: number | null;
  /** ID of the area containing the current location (to highlight) */
  containingAreaId?: number | null;
}

export function AreaChip({
  selectedAreaIds,
  onToggleArea,
  onClear,
  centerLat,
  centerLon,
  containingAreaId,
}: AreaChipProps) {
  const [selectedAreaTypeId, setSelectedAreaTypeId] = useState<number | null>(null);
  const [sortMode, setSortMode] = useState<SortMode>("name");

  // Fetch area types
  const { data: areaTypes, isLoading: isLoadingTypes } = useAreaTypes();

  // Set default area type when loaded
  useEffect(() => {
    if (areaTypes && areaTypes.length > 0 && selectedAreaTypeId === null) {
      // Try to find "historic_county" or use first type
      const historicCounty = areaTypes.find((t) => t.code === "historic_county");
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Initializing default from async API data
      setSelectedAreaTypeId(historicCounty?.id || areaTypes[0].id);
    }
  }, [areaTypes, selectedAreaTypeId]);

  // Fetch areas for the selected type
  const hasLocation = centerLat != null && centerLon != null;
  const { data: areas, isLoading: isLoadingAreas } = useAreasByType({
    typeId: selectedAreaTypeId,
    lat: hasLocation ? centerLat! : undefined,
    lon: hasLocation ? centerLon! : undefined,
    order: sortMode,
  });

  // Areas with containing area at top
  const sortedAreas = useMemo(() => {
    if (!areas) return [];
    
    const sorted = [...areas];
    
    // Always put the containing area at the top
    if (containingAreaId) {
      const containingIndex = sorted.findIndex((a) => a.id === containingAreaId);
      if (containingIndex > 0) {
        const [containingArea] = sorted.splice(containingIndex, 1);
        sorted.unshift(containingArea);
      }
    }

    return sorted;
  }, [areas, containingAreaId]);

  const selectedCount = selectedAreaIds.length;
  const selectedInType = (areas || []).filter((a) => selectedAreaIds.includes(a.id));

  // For area filter: empty = all (no filter), specific IDs = filter
  let summary: string;
  if (isLoadingTypes || isLoadingAreas) {
    summary = "Loading...";
  } else if (selectedCount === 0) {
    summary = "All"; // Empty array = no filter = all areas
  } else if (selectedInType.length === 1) {
    summary = selectedInType[0].name;
  } else if (selectedInType.length > 0) {
    summary = `${selectedInType.length} areas`;
  } else {
    summary = `${selectedCount} selected`;
  }

  // Active when any specific areas are selected (filtering is happening)
  const isActive = selectedCount > 0;
  // No warning state for area - empty means "all", not "none"
  const isWarning = false;

  return (
    <FilterChip
      label="Area"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onClear}
      popoverWidth="xl"
      icon={<MapIcon className="w-3.5 h-3.5" />}
    >
      {isLoadingTypes ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : (
        <>
          {/* Area type selector */}
          <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
            <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">
              Area type
            </label>
            <select
              value={selectedAreaTypeId || ""}
              onChange={(e) => setSelectedAreaTypeId(parseInt(e.target.value, 10))}
              className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 
                         rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                         focus:ring-1 focus:ring-trig-green-500 focus:border-trig-green-500"
            >
              {areaTypes?.map((type) => (
                <option key={type.id} value={type.id}>
                  {type.name}
                </option>
              ))}
            </select>
          </div>

          {/* Sort controls */}
          <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex items-center justify-between">
            <span className="text-xs text-gray-500 dark:text-gray-400">Sort by:</span>
            <div className="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600">
              <button
                type="button"
                onClick={() => setSortMode("name")}
                className={`px-2 py-1 text-xs font-medium flex items-center gap-1 ${
                  sortMode === "name"
                    ? "bg-trig-green-600 text-white"
                    : "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600"
                }`}
                title="Sort alphabetically"
              >
                <SortAsc className="w-3 h-3" />
                A-Z
              </button>
              <button
                type="button"
                onClick={() => setSortMode("distance")}
                disabled={!hasLocation}
                className={`px-2 py-1 text-xs font-medium flex items-center gap-1 border-l border-gray-300 dark:border-gray-600 ${
                  sortMode === "distance"
                    ? "bg-trig-green-600 text-white"
                    : hasLocation
                      ? "bg-white dark:bg-gray-700 text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-600"
                      : "bg-gray-100 dark:bg-gray-800 text-gray-400 cursor-not-allowed"
                }`}
                title={hasLocation ? "Sort by distance from search location" : "Set a location first"}
              >
                <Navigation className="w-3 h-3" />
                Nearest
              </button>
            </div>
          </div>

          {/* Clear selection button - only show when areas are selected */}
          {selectedAreaIds.length > 0 && (
            <div className="flex gap-2 px-3 py-2 border-b border-[color:var(--color-border)]">
              <button
                type="button"
                onClick={onClear}
                className="px-2 py-1 text-xs font-medium text-trig-green-600 
                           hover:bg-trig-green-50 dark:hover:bg-trig-green-900/20 rounded transition-colors"
              >
                Clear selection
              </button>
            </div>
          )}

          {/* Area list */}
          {isLoadingAreas ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
            </div>
          ) : (
            <div className="py-1">
              {sortedAreas.map((area) => {
                const isContaining = area.id === containingAreaId;
                return (
                  <div
                    key={area.id}
                    className={isContaining ? "bg-trig-green-50 dark:bg-trig-green-900/20" : ""}
                  >
                    <FilterListItem
                      label={area.name}
                      checked={selectedAreaIds.includes(area.id)}
                      onChange={() => onToggleArea(area.id)}
                      icon={
                        isContaining ? (
                          <span className="text-trig-green-600 dark:text-trig-green-400" title="Your current location is in this area">
                            📍
                          </span>
                        ) : undefined
                      }
                    />
                  </div>
                );
              })}
              {sortedAreas.length === 0 && (
                <div className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 text-center">
                  No areas available for this type
                </div>
              )}
            </div>
          )}
        </>
      )}
    </FilterChip>
  );
}

export default AreaChip;
