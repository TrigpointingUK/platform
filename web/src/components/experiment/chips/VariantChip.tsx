/**
 * VariantChip - Filter chip for trig variants (e.g. the detector material of
 * Buried Blocks and Bolts).
 *
 * Like the other multi-select chips, everything ticked means no filter. Most
 * trigs have no variant, so a "Not recorded" option covers them. The page only
 * shows the chip when relevant, passing just the relevant groups - see
 * relevantVariantGroups in lib/trigVariants.
 */

import { Shapes } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";
import type { VariantGroup } from "../../../hooks/useReferenceData";
import { VARIANT_NOT_RECORDED } from "../../../lib/trigVariants";

const NOT_RECORDED_LABEL = "Not recorded";

export interface VariantChipProps {
  groups: VariantGroup[];
  selectedValues: string[];
  onToggle: (value: string) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

export function VariantChip({
  groups,
  selectedValues,
  onToggle,
  onSelectAll,
  onSelectNone,
}: VariantChipProps) {
  const options = [
    ...groups.flatMap((g) => g.values),
    { value: VARIANT_NOT_RECORDED, label: NOT_RECORDED_LABEL },
  ];
  const selectedOptions = options.filter((o) => selectedValues.includes(o.value));
  const selectedCount = selectedOptions.length;
  const totalCount = options.length;

  let summary: string;
  if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else if (selectedCount === 1) {
    summary = selectedOptions[0].label;
  } else {
    summary = `${selectedCount} selected`;
  }

  // Active when some (but not all) items are selected
  const isActive = selectedCount > 0 && selectedCount < totalCount;
  // Warning when nothing is selected (will result in empty list)
  const isWarning = selectedCount === 0;
  // Name the chip after its group when there's only one (e.g. "Detector material")
  const label = groups.length === 1 ? groups[0].name : "Variant";

  return (
    <FilterChip
      label={label}
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onSelectAll}
      popoverWidth="md"
      icon={<Shapes className="w-3.5 h-3.5" />}
    >
      <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
      {groups.map((group) => (
        <div key={group.code} className="py-1">
          {groups.length > 1 && (
            <div className="px-3 pt-1 text-xs font-semibold text-gray-600 dark:text-gray-300">
              {group.name}
            </div>
          )}
          {group.values.map((item) => (
            <FilterListItem
              key={item.value}
              label={item.label}
              checked={selectedValues.includes(item.value)}
              onChange={() => onToggle(item.value)}
            />
          ))}
        </div>
      ))}
      <div className="py-1 border-t border-[color:var(--color-border)]">
        <FilterListItem
          label={NOT_RECORDED_LABEL}
          checked={selectedValues.includes(VARIANT_NOT_RECORDED)}
          onChange={() => onToggle(VARIANT_NOT_RECORDED)}
        />
      </div>
    </FilterChip>
  );
}

export default VariantChip;
