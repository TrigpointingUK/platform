/**
 * CurrentUseChip - Filter chip for current/recent use of trigpoints
 * 
 * Values from trig.current_use column (e.g., "Passive station", "Active station")
 */

import { Clock, Loader2 } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";
import { useCurrentUseValues } from "../../../hooks/useReferenceData";

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
  const { data: values, isLoading, isError } = useCurrentUseValues();

  const selectedCount = selectedValues.length;
  const totalCount = values?.length || 0;
  
  let summary: string;
  if (isLoading) {
    summary = "Loading...";
  } else if (isError || !values) {
    summary = "Error";
  } else if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else if (selectedCount === 1) {
    const selected = values.find((v) => selectedValues.includes(v.value));
    summary = selected?.label || "1 selected";
  } else {
    summary = `${selectedCount} selected`;
  }

  // Active when some (but not all) items are selected
  const isActive = selectedCount > 0 && selectedCount < totalCount;
  // Warning when nothing is selected (will result in empty list)
  const isWarning = selectedCount === 0 && !isLoading;

  return (
    <FilterChip
      label="Recent use"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onSelectAll}
      popoverWidth="md"
      icon={<Clock className="w-3.5 h-3.5" />}
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : isError || !values ? (
        <div className="px-3 py-4 text-sm text-red-600 dark:text-red-400">
          Failed to load current use values. Please try again.
        </div>
      ) : (
        <>
          <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
          <div className="py-1">
            {values.map((item) => (
              <FilterListItem
                key={item.value}
                label={item.label}
                checked={selectedValues.includes(item.value)}
                onChange={() => onToggle(item.value)}
              />
            ))}
          </div>
        </>
      )}
    </FilterChip>
  );
}

export default CurrentUseChip;
