/**
 * ConditionChip - Filter chip for trig physical condition
 * 
 * Values from trig.condition column (G=Good, S=Slightly damaged, etc.)
 */

import { Heart } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";

// Condition values with icons
// Using correct icon filenames from /icons/conditions/
export const CONDITION_VALUES = [
  { code: "G", label: "Good", icon: "c_good.png", color: "text-green-600" },
  { code: "S", label: "Slightly Damaged", icon: "c_slightlydamaged.png", color: "text-yellow-600" },
  { code: "D", label: "Damaged", icon: "c_damaged.png", color: "text-orange-600" },
  { code: "T", label: "Toppled", icon: "c_toppled.png", color: "text-orange-700" },
  { code: "C", label: "Converted", icon: "c_slightlydamaged.png", color: "text-blue-600" },
  { code: "R", label: "Remains", icon: "c_toppled.png", color: "text-gray-600" },
  { code: "X", label: "Destroyed", icon: "c_definitelymissing.png", color: "text-red-600" },
  { code: "V", label: "Unreachable but Visible", icon: "c_unreachablebutvisible.png", color: "text-purple-600" },
  { code: "P", label: "Inaccessible", icon: "c_unknown.png", color: "text-amber-600" },
  { code: "U", label: "Unknown", icon: "c_unknown.png", color: "text-gray-400" },
  { code: "Q", label: "Possibly Missing", icon: "c_possiblymissing.png", color: "text-amber-500" },
  { code: "N", label: "Couldn't Find", icon: "c_possiblymissing.png", color: "text-gray-400" },
];

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
  const selectedCount = selectedConditions.length;
  const totalCount = CONDITION_VALUES.length;
  
  // Get the "definite" conditions (G, S, D, T, C, R, X, V)
  const definiteConditions = ["G", "S", "D", "T", "C", "R", "X", "V"];
  const selectedDefinite = selectedConditions.filter(c => definiteConditions.includes(c));
  
  let summary: string;
  if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else if (selectedCount === 1) {
    const selected = CONDITION_VALUES.find(v => selectedConditions.includes(v.code));
    summary = selected?.label || "1 selected";
  } else if (selectedDefinite.length === 1) {
    const selected = CONDITION_VALUES.find(v => v.code === selectedDefinite[0]);
    summary = `${selected?.label || "1"} +${selectedCount - 1}`;
  } else {
    summary = `${selectedCount} selected`;
  }

  // Active when some (but not all) items are selected
  const isActive = selectedCount > 0 && selectedCount < totalCount;
  // Warning when nothing is selected (will result in empty list)
  const isWarning = selectedCount === 0;

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
      <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
      <div className="py-1">
        {CONDITION_VALUES.map((condition) => (
          <FilterListItem
            key={condition.code}
            label={condition.label}
            checked={selectedConditions.includes(condition.code)}
            onChange={() => onToggle(condition.code)}
            icon={
              <img
                src={`/icons/conditions/${condition.icon}`}
                alt=""
                className="w-5 h-5 object-contain"
              />
            }
          />
        ))}
      </div>
    </FilterChip>
  );
}

export default ConditionChip;

