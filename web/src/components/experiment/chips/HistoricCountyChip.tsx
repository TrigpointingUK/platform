/**
 * HistoricCountyChip - Simplified filter chip for historic counties only
 * 
 * Similar UX to HistoricUseChip - just a toggleable list with All/None
 */

import { Map } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";

// Mock historic counties - would come from API
// This is a representative sample of all UK historic counties
export const HISTORIC_COUNTIES = [
  { id: 101, name: "Bedfordshire" },
  { id: 102, name: "Berkshire" },
  { id: 103, name: "Buckinghamshire" },
  { id: 104, name: "Cambridgeshire" },
  { id: 105, name: "Cheshire" },
  { id: 106, name: "Cornwall" },
  { id: 107, name: "Cumberland" },
  { id: 108, name: "Derbyshire" },
  { id: 109, name: "Devon" },
  { id: 110, name: "Dorset" },
  { id: 111, name: "Durham" },
  { id: 112, name: "Essex" },
  { id: 113, name: "Gloucestershire" },
  { id: 114, name: "Hampshire" },
  { id: 115, name: "Herefordshire" },
  { id: 116, name: "Hertfordshire" },
  { id: 117, name: "Huntingdonshire" },
  { id: 118, name: "Kent" },
  { id: 119, name: "Lancashire" },
  { id: 120, name: "Leicestershire" },
  { id: 121, name: "Lincolnshire" },
  { id: 122, name: "Middlesex" },
  { id: 123, name: "Norfolk" },
  { id: 124, name: "Northamptonshire" },
  { id: 125, name: "Northumberland" },
  { id: 126, name: "Nottinghamshire" },
  { id: 127, name: "Oxfordshire" },
  { id: 128, name: "Rutland" },
  { id: 129, name: "Shropshire" },
  { id: 130, name: "Somerset" },
  { id: 131, name: "Staffordshire" },
  { id: 132, name: "Suffolk" },
  { id: 133, name: "Surrey" },
  { id: 134, name: "Sussex" },
  { id: 135, name: "Warwickshire" },
  { id: 136, name: "Westmorland" },
  { id: 137, name: "Wiltshire" },
  { id: 138, name: "Worcestershire" },
  { id: 139, name: "Yorkshire" },
  // Welsh counties
  { id: 201, name: "Anglesey" },
  { id: 202, name: "Breconshire" },
  { id: 203, name: "Caernarfonshire" },
  { id: 204, name: "Cardiganshire" },
  { id: 205, name: "Carmarthenshire" },
  { id: 206, name: "Denbighshire" },
  { id: 207, name: "Flintshire" },
  { id: 208, name: "Glamorgan" },
  { id: 209, name: "Merionethshire" },
  { id: 210, name: "Monmouthshire" },
  { id: 211, name: "Montgomeryshire" },
  { id: 212, name: "Pembrokeshire" },
  { id: 213, name: "Radnorshire" },
  // Scottish counties (sample)
  { id: 301, name: "Aberdeenshire" },
  { id: 302, name: "Argyllshire" },
  { id: 303, name: "Ayrshire" },
  { id: 304, name: "Dumfriesshire" },
  { id: 305, name: "Edinburghshire (Midlothian)" },
  { id: 306, name: "Fife" },
  { id: 307, name: "Inverness-shire" },
  { id: 308, name: "Lanarkshire" },
  { id: 309, name: "Perthshire" },
  { id: 310, name: "Ross-shire" },
];

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

