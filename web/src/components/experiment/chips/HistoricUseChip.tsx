/**
 * HistoricUseChip - Filter chip for historic use of trigpoints
 * 
 * Values from trig.historic_use column (e.g., "Primary", "Secondary", "3rd order", "Other")
 */

import { History } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";

// Known historic use values from the database
// These would ideally come from an API, but for now we'll hardcode the known values
export const HISTORIC_USE_VALUES = [
  { value: "Primary", label: "Primary" },
  { value: "Secondary", label: "Secondary" },
  { value: "3rd order", label: "3rd order" },
  { value: "4th order", label: "4th order" },
  { value: "Other", label: "Other" },
  { value: "Unknown", label: "Unknown" },
  { value: "", label: "(Not specified)" },
];

export interface HistoricUseChipProps {
  selectedValues: string[];
  onToggle: (value: string) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

export function HistoricUseChip({
  selectedValues,
  onToggle,
  onSelectAll,
  onSelectNone,
}: HistoricUseChipProps) {
  const selectedCount = selectedValues.length;
  const totalCount = HISTORIC_USE_VALUES.length;
  
  let summary: string;
  if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else if (selectedCount === 1) {
    const selected = HISTORIC_USE_VALUES.find(v => selectedValues.includes(v.value));
    summary = selected?.label || "1 selected";
  } else {
    summary = `${selectedCount} selected`;
  }

  // Active when some (but not all) items are selected
  const isActive = selectedCount > 0 && selectedCount < totalCount;
  // Warning when nothing is selected (will result in empty list)
  const isWarning = selectedCount === 0;

  return (
    <FilterChip
      label="Historic use"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onSelectAll}
      popoverWidth="md"
      icon={<History className="w-3.5 h-3.5" />}
    >
      <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
      <div className="py-1">
        {HISTORIC_USE_VALUES.map((item) => (
          <FilterListItem
            key={item.value}
            label={item.label}
            checked={selectedValues.includes(item.value)}
            onChange={() => onToggle(item.value)}
          />
        ))}
      </div>
    </FilterChip>
  );
}

export default HistoricUseChip;

