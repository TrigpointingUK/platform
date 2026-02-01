/**
 * CategoryChip - Filter chip for trig categories (Pillar, FBM, etc.)
 */

import { Layers } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons } from "../FilterChip";

// Category definitions matching StatusFilter
const CATEGORIES = [
  { id: 10, code: "PILLAR", name: "Pillar", icon: "/icons/t_pillar.png" },
  { id: 20, code: "FBM", name: "FBM", icon: "/icons/t_fbm.png" },
  { id: 30, code: "SURVEY_MARK", name: "Survey mark", icon: "/icons/t_passive.png" },
  { id: 40, code: "INTERSECTED", name: "Intersected", icon: "/icons/t_intersected.png" },
  { id: 50, code: "ACTIVE", name: "Active station", icon: "/icons/t_active.png" },
  { id: 60, code: "OTHER", name: "Other", icon: "/icons/t_other.svg" },
];

const ALL_CATEGORY_IDS = CATEGORIES.map((c) => c.id);

export interface CategoryChipProps {
  selectedCategories: number[];
  onToggleCategory: (categoryId: number) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

export function CategoryChip({
  selectedCategories,
  onToggleCategory,
  onSelectAll,
  onSelectNone,
}: CategoryChipProps) {
  const selectedCount = selectedCategories.length;
  const totalCount = CATEGORIES.length;
  
  let summary: string;
  if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else if (selectedCount <= 2) {
    summary = CATEGORIES
      .filter((c) => selectedCategories.includes(c.id))
      .map((c) => c.name)
      .join(", ");
  } else {
    summary = `${selectedCount} selected`;
  }

  const isActive = selectedCount > 0 && selectedCount < totalCount;

  return (
    <FilterChip
      label="Category"
      summary={summary}
      isActive={isActive}
      clearable={isActive}
      onClear={onSelectAll}
      popoverWidth="md"
      icon={<Layers className="w-3.5 h-3.5" />}
    >
      <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
      <div className="py-1">
        {CATEGORIES.map((category) => (
          <FilterListItem
            key={category.id}
            label={category.name}
            checked={selectedCategories.includes(category.id)}
            onChange={() => onToggleCategory(category.id)}
            icon={
              <img
                src={category.icon}
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

export { CATEGORIES, ALL_CATEGORY_IDS };
export default CategoryChip;

