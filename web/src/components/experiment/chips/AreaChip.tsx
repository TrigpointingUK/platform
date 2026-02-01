/**
 * AreaChip - Full-featured filter chip for geographic areas
 * 
 * Features:
 * - Area type selector at top
 * - Toggleable list of all areas of that type
 * - Sort by alphabetical or distance from search location
 * - Current location's area highlighted at top
 */

import { useState, useMemo } from "react";
import { MapIcon, SortAsc, Navigation } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";

// Area type definitions
export interface AreaType {
  id: number;
  code: string;
  name: string;
}

export interface Area {
  id: number;
  name: string;
  code?: string;
  areaTypeId: number;
  // For sorting by distance - would be calculated from centroid
  centroidLat?: number;
  centroidLon?: number;
}

// Mock area types - would come from API /v1/areas/types
export const AREA_TYPES: AreaType[] = [
  { id: 1, code: "historic_county", name: "Historic County" },
  { id: 2, code: "county_1991", name: "County (1991)" },
  { id: 3, code: "os_landranger", name: "OS Landranger" },
  { id: 4, code: "os_explorer", name: "OS Explorer" },
  { id: 5, code: "wainwright", name: "Wainwright" },
  { id: 6, code: "country", name: "Country" },
];

// Mock areas - in production would come from API
// Note: This is a simplified subset for demonstration
export const MOCK_AREAS: Record<string, Area[]> = {
  historic_county: [
    { id: 101, name: "Derbyshire", code: "DBY", areaTypeId: 1, centroidLat: 53.1, centroidLon: -1.5 },
    { id: 102, name: "Yorkshire", code: "YKS", areaTypeId: 1, centroidLat: 53.9, centroidLon: -1.5 },
    { id: 103, name: "Lancashire", code: "LAN", areaTypeId: 1, centroidLat: 53.8, centroidLon: -2.5 },
    { id: 104, name: "Staffordshire", code: "STA", areaTypeId: 1, centroidLat: 52.8, centroidLon: -2.0 },
    { id: 105, name: "Cheshire", code: "CHE", areaTypeId: 1, centroidLat: 53.2, centroidLon: -2.5 },
    { id: 106, name: "Nottinghamshire", code: "NTT", areaTypeId: 1, centroidLat: 53.1, centroidLon: -1.0 },
    { id: 107, name: "Leicestershire", code: "LEI", areaTypeId: 1, centroidLat: 52.6, centroidLon: -1.1 },
    { id: 108, name: "Lincolnshire", code: "LIN", areaTypeId: 1, centroidLat: 53.2, centroidLon: -0.2 },
    { id: 109, name: "Cornwall", code: "CON", areaTypeId: 1, centroidLat: 50.3, centroidLon: -5.0 },
    { id: 110, name: "Devon", code: "DEV", areaTypeId: 1, centroidLat: 50.7, centroidLon: -3.5 },
  ],
  county_1991: [
    { id: 201, name: "Derbyshire", code: "DBY", areaTypeId: 2, centroidLat: 53.1, centroidLon: -1.5 },
    { id: 202, name: "North Yorkshire", code: "NYK", areaTypeId: 2, centroidLat: 54.2, centroidLon: -1.5 },
    { id: 203, name: "South Yorkshire", code: "SYK", areaTypeId: 2, centroidLat: 53.5, centroidLon: -1.4 },
    { id: 204, name: "West Yorkshire", code: "WYK", areaTypeId: 2, centroidLat: 53.8, centroidLon: -1.7 },
    { id: 205, name: "Greater Manchester", code: "GTM", areaTypeId: 2, centroidLat: 53.5, centroidLon: -2.3 },
  ],
};

type SortMode = "alpha" | "distance";

// Calculate distance between two points (simplified Haversine)
function calculateDistance(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const R = 6371; // Earth's radius in km
  const dLat = ((lat2 - lat1) * Math.PI) / 180;
  const dLon = ((lon2 - lon1) * Math.PI) / 180;
  const a =
    Math.sin(dLat / 2) * Math.sin(dLat / 2) +
    Math.cos((lat1 * Math.PI) / 180) *
      Math.cos((lat2 * Math.PI) / 180) *
      Math.sin(dLon / 2) *
      Math.sin(dLon / 2);
  const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1 - a));
  return R * c;
}

export interface AreaChipProps {
  selectedAreaIds: number[];
  onToggleArea: (areaId: number) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
  /** Current search location for distance sorting */
  centerLat?: number | null;
  centerLon?: number | null;
  /** ID of the area containing the current location (to highlight) */
  containingAreaId?: number | null;
}

export function AreaChip({
  selectedAreaIds,
  onToggleArea,
  onSelectAll,
  onSelectNone,
  centerLat,
  centerLon,
  containingAreaId,
}: AreaChipProps) {
  const [selectedAreaType, setSelectedAreaType] = useState<string>("historic_county");
  const [sortMode, setSortMode] = useState<SortMode>("alpha");

  // Get areas for selected type
  const areas = MOCK_AREAS[selectedAreaType] || [];

  // Sort areas based on mode
  const sortedAreas = useMemo(() => {
    const areasWithDistance = areas.map((area) => ({
      ...area,
      distance:
        centerLat && centerLon && area.centroidLat && area.centroidLon
          ? calculateDistance(centerLat, centerLon, area.centroidLat, area.centroidLon)
          : Infinity,
    }));

    let sorted: typeof areasWithDistance;
    if (sortMode === "distance") {
      sorted = [...areasWithDistance].sort((a, b) => a.distance - b.distance);
    } else {
      sorted = [...areasWithDistance].sort((a, b) => a.name.localeCompare(b.name));
    }

    // Always put the containing area at the top
    if (containingAreaId) {
      const containingIndex = sorted.findIndex((a) => a.id === containingAreaId);
      if (containingIndex > 0) {
        const [containingArea] = sorted.splice(containingIndex, 1);
        sorted.unshift(containingArea);
      }
    }

    return sorted;
  }, [areas, sortMode, centerLat, centerLon, containingAreaId]);

  const selectedCount = selectedAreaIds.length;
  const selectedInType = areas.filter((a) => selectedAreaIds.includes(a.id));
  const allInTypeSelected = areas.length > 0 && selectedInType.length === areas.length;

  let summary: string;
  if (selectedCount === 0) {
    summary = "None";
  } else if (allInTypeSelected) {
    summary = "All areas";
  } else if (selectedInType.length === 1) {
    summary = selectedInType[0].name;
  } else if (selectedInType.length > 1) {
    summary = `${selectedInType.length} areas`;
  } else {
    summary = `${selectedCount} selected`;
  }

  // Active when some (but not all) areas are selected
  const isActive = selectedCount > 0 && !allInTypeSelected;
  // Warning when nothing is selected (will result in empty list)
  const isWarning = selectedCount === 0;
  const hasLocation = centerLat != null && centerLon != null;

  return (
    <FilterChip
      label="Area"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onSelectAll}
      popoverWidth="xl"
      icon={<MapIcon className="w-3.5 h-3.5" />}
    >
      {/* Area type selector */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700">
        <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">
          Area type
        </label>
        <select
          value={selectedAreaType}
          onChange={(e) => setSelectedAreaType(e.target.value)}
          className="w-full px-2 py-1.5 text-sm border border-gray-300 dark:border-gray-600 
                     rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                     focus:ring-1 focus:ring-trig-green-500 focus:border-trig-green-500"
        >
          {AREA_TYPES.map((type) => (
            <option key={type.code} value={type.code}>
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
            onClick={() => setSortMode("alpha")}
            className={`px-2 py-1 text-xs font-medium flex items-center gap-1 ${
              sortMode === "alpha"
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

      <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />

      {/* Area list */}
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
                count={
                  sortMode === "distance" && area.distance !== Infinity
                    ? Math.round(area.distance)
                    : undefined
                }
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
        {areas.length === 0 && (
          <div className="px-3 py-4 text-sm text-gray-500 dark:text-gray-400 text-center">
            No areas available for this type
          </div>
        )}
      </div>

      {/* Note about backend */}
      <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700 bg-amber-50 dark:bg-amber-900/20">
        <p className="text-xs text-amber-700 dark:text-amber-300">
          ⚠️ Demo data only. Full area list requires API support.
        </p>
      </div>
    </FilterChip>
  );
}

export default AreaChip;

