/**
 * CurrentUseChip - Filter chip for current/recent use of trigpoints
 * 
 * Values from trig.current_use column (e.g., "Passive station", "Active station")
 * Note: Despite the name "current_use", this is really about the most recent use.
 */

import { Radio } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";

// Known current use values from the database
export const CURRENT_USE_VALUES = [
  { value: "Passive station", label: "Passive station" },
  { value: "Active station", label: "Active station" },
  { value: "None", label: "None" },
  { value: "Unknown", label: "Unknown" },
  { value: "", label: "(Not specified)" },
];

export interface CurrentUseChipProps {
  selectedValues: string[];
  onToggle: (value: string) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

export function CurrentUseChip({
  selectedValues,
  onToggle,
  onSelectAll,
  onSelectNone,
}: CurrentUseChipProps) {
  const selectedCount = selectedValues.length;
  const totalCount = CURRENT_USE_VALUES.length;
  
  let summary: string;
  if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else if (selectedCount === 1) {
    const selected = CURRENT_USE_VALUES.find(v => selectedValues.includes(v.value));
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
      label="Recent use"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onSelectAll}
      popoverWidth="md"
      icon={<Radio className="w-3.5 h-3.5" />}
    >
      <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
      <div className="py-1">
        {CURRENT_USE_VALUES.map((item) => (
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

export default CurrentUseChip;

