/**
 * HistoricCountyChip - Simplified filter chip for historic counties only
 * 
 * Similar UX to HistoricUseChip - just a toggleable list with All/None
 */

import { Map } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";
import { HISTORIC_COUNTIES } from "./historicCountyData";

export interface HistoricCountyChipProps {
  selectedCountyIds: number[];
  onToggleCounty: (countyId: number) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
  /** ID of the county containing the current location (to highlight) */
  containingCountyId?: number | null;
}

export function HistoricCountyChip({
  selectedCountyIds,
  onToggleCounty,
  onSelectAll,
  onSelectNone,
  containingCountyId,
}: HistoricCountyChipProps) {
  const selectedCount = selectedCountyIds.length;
  const totalCount = HISTORIC_COUNTIES.length;

  // Get selected county names for summary
  const selectedCounties = HISTORIC_COUNTIES.filter((c) =>
    selectedCountyIds.includes(c.id)
  );

  let summary: string;
  if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else if (selectedCount === 1) {
    summary = selectedCounties[0]?.name || "1 selected";
  } else if (selectedCount === 2) {
    summary = selectedCounties.map((c) => c.name).join(", ");
  } else {
    summary = `${selectedCount} counties`;
  }

  // Active when some (but not all) items are selected
  const isActive = selectedCount > 0 && selectedCount < totalCount;
  // Warning when nothing is selected (will result in empty list)
  const isWarning = selectedCount === 0;

  // Sort counties alphabetically, but put containing county first
  const sortedCounties = [...HISTORIC_COUNTIES].sort((a, b) => {
    if (a.id === containingCountyId) return -1;
    if (b.id === containingCountyId) return 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <FilterChip
      label="Historic County"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onSelectAll}
      popoverWidth="lg"
      icon={<Map className="w-3.5 h-3.5" />}
    >
      <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
      
      {/* County list */}
      <div className="py-1">
        {sortedCounties.map((county) => {
          const isContaining = county.id === containingCountyId;
          return (
            <div
              key={county.id}
              className={isContaining ? "bg-trig-green-50 dark:bg-trig-green-900/20" : ""}
            >
              <FilterListItem
                label={county.name}
                checked={selectedCountyIds.includes(county.id)}
                onChange={() => onToggleCounty(county.id)}
                icon={
                  isContaining ? (
                    <span className="text-trig-green-600 dark:text-trig-green-400" title="Your current location">
                      📍
                    </span>
                  ) : undefined
                }
              />
            </div>
          );
        })}
      </div>

      {/* Quick search - would be useful for 50+ items */}
      <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700">
        <p className="text-xs text-gray-500 dark:text-gray-400">
          Tip: Scroll to find your county, or use the full Area filter for search.
        </p>
      </div>
    </FilterChip>
  );
}

export default HistoricCountyChip;

