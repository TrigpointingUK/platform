/**
 * ConditionChip - Filter chip for trig physical condition
 * 
 * Values from trig.condition column (G=Good, S=Slightly damaged, etc.)
 */

import { Heart, Loader2 } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";
import { useConditions, type Condition } from "../../../hooks/useReferenceData";

export interface ConditionChipProps {
  selectedConditions: string[];
  onToggle: (code: string) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

export function ConditionChip({
  selectedConditions,
  onToggle,
  onSelectAll,
  onSelectNone,
}: ConditionChipProps) {
  const { data: conditions, isLoading, isError } = useConditions();

  const selectedCount = selectedConditions.length;
  const totalCount = conditions?.length || 0;
  
  // Get the "definite" conditions (the first 8 or so by sort order)
  const definiteConditions = conditions?.slice(0, 8).map((c) => c.code) || [];
  const selectedDefinite = selectedConditions.filter((c) => definiteConditions.includes(c));
  
  let summary: string;
  if (isLoading) {
    summary = "Loading...";
  } else if (isError || !conditions) {
    summary = "Error";
  } else if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else if (selectedCount === 1) {
    const selected = conditions.find((v) => selectedConditions.includes(v.code));
    summary = selected?.name || "1 selected";
  } else if (selectedDefinite.length === 1) {
    const selected = conditions.find((v) => v.code === selectedDefinite[0]);
    summary = `${selected?.name || "1"} +${selectedCount - 1}`;
  } else {
    summary = `${selectedCount} selected`;
  }

  // Active when some (but not all) items are selected
  const isActive = selectedCount > 0 && selectedCount < totalCount;
  // Warning when nothing is selected (will result in empty list)
  const isWarning = selectedCount === 0 && !isLoading;

  // Get icon path for a condition
  const getConditionIcon = (condition: Condition): string => {
    if (condition.icon_file) {
      return `/icons/conditions/${condition.icon_file}`;
    }
    return "/icons/conditions/c_unknown.png";
  };

  return (
    <FilterChip
      label="Condition"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onSelectAll}
      popoverWidth="lg"
      icon={<Heart className="w-3.5 h-3.5" />}
    >
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : isError || !conditions ? (
        <div className="px-3 py-4 text-sm text-red-600 dark:text-red-400">
          Failed to load conditions. Please try again.
        </div>
      ) : (
        <>
          <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
          <div className="py-1">
            {conditions.map((condition) => (
              <FilterListItem
                key={condition.code}
                label={condition.name}
                checked={selectedConditions.includes(condition.code)}
                onChange={() => onToggle(condition.code)}
                icon={
                  <img
                    src={getConditionIcon(condition)}
                    alt=""
                    className="w-5 h-5 object-contain"
                  />
                }
              />
            ))}
          </div>
        </>
      )}
    </FilterChip>
  );
}

export default ConditionChip;
