/**
 * TypeChip - Filter chip for physical trig types (hierarchical, grouped by category)
 * 
 * Types are grouped by category (Pillar, FBM, etc.) with expand/collapse functionality.
 * Toggling a category toggles all types within it.
 */

import { useState } from "react";
import { Tag, ChevronRight, ChevronDown } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons, FilterCheckbox } from "../FilterChip";

// Type definitions grouped by category
// In production, this would come from the /v1/types/categories API
export interface TrigType {
  code: string;
  name: string;
}

export interface TrigCategory {
  id: number;
  code: string;
  name: string;
  icon: string;
  types: TrigType[];
}

// Mock data matching the actual database structure
export const TYPE_CATEGORIES: TrigCategory[] = [
  {
    id: 10,
    code: "PILLAR",
    name: "Pillar",
    icon: "/icons/t_pillar.png",
    types: [
      { code: "HOTINE", name: "Hotine pillar" },
      { code: "COLE", name: "Cole pillar" },
      { code: "VANESSA", name: "Vanessa pillar" },
      { code: "FBM_PILLAR", name: "FBM pillar" },
      { code: "OTHER_PILLAR", name: "Other pillar" },
    ],
  },
  {
    id: 20,
    code: "FBM",
    name: "FBM",
    icon: "/icons/t_fbm.png",
    types: [
      { code: "FLUSH_BRACKET", name: "Flush bracket" },
      { code: "BOLT", name: "Bolt" },
      { code: "RIVET", name: "Rivet" },
      { code: "CUT", name: "Cut" },
    ],
  },
  {
    id: 30,
    code: "SURVEY_MARK",
    name: "Survey mark",
    icon: "/icons/t_passive.png",
    types: [
      { code: "SURFACE_BLOCK", name: "Surface block" },
      { code: "BURIED_BLOCK", name: "Buried block" },
      { code: "PIPE", name: "Pipe" },
    ],
  },
  {
    id: 40,
    code: "INTERSECTED",
    name: "Intersected",
    icon: "/icons/t_intersected.png",
    types: [
      { code: "CHURCH", name: "Church spire/tower" },
      { code: "CHIMNEY", name: "Chimney" },
      { code: "MAST", name: "Mast/tower" },
      { code: "LIGHTHOUSE", name: "Lighthouse" },
      { code: "OTHER_INTERSECTED", name: "Other intersected" },
    ],
  },
  {
    id: 50,
    code: "ACTIVE",
    name: "Active station",
    icon: "/icons/t_active.png",
    types: [
      { code: "GNSS", name: "GNSS station" },
      { code: "OSNET", name: "OS Net station" },
    ],
  },
  {
    id: 60,
    code: "OTHER",
    name: "Other",
    icon: "/icons/t_other.svg",
    types: [
      { code: "CANNON", name: "Cannon" },
      { code: "PLATFORM", name: "Platform" },
      { code: "OTHER_OTHER", name: "Other" },
    ],
  },
];

// Get all type codes
export const ALL_TYPE_CODES = TYPE_CATEGORIES.flatMap((c) => c.types.map((t) => t.code));

export interface TypeChipProps {
  selectedTypes: string[];
  selectedCategories: number[];
  onToggleType: (typeCode: string) => void;
  onToggleCategory: (categoryId: number) => void;
  onSelectAll: () => void;
  onSelectNone: () => void;
}

export function TypeChip({
  selectedTypes,
  selectedCategories,
  onToggleType,
  onToggleCategory,
  onSelectAll,
  onSelectNone,
}: TypeChipProps) {
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  const toggleCategoryExpanded = (code: string) => {
    setExpandedCategories((prev) => {
      const next = new Set(prev);
      if (next.has(code)) {
        next.delete(code);
      } else {
        next.add(code);
      }
      return next;
    });
  };

  const selectedCount = selectedTypes.length;
  const totalCount = ALL_TYPE_CODES.length;
  
  let summary: string;
  if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else {
    // Check if any full categories are selected
    const selectedCategoryNames = TYPE_CATEGORIES
      .filter((cat) => {
        const catTypeCodes = cat.types.map((t) => t.code);
        return catTypeCodes.every((code) => selectedTypes.includes(code));
      })
      .map((cat) => cat.name);
    
    if (selectedCategoryNames.length > 0 && selectedCategoryNames.length <= 2) {
      summary = selectedCategoryNames.join(", ");
    } else {
      summary = `${selectedCount} types`;
    }
  }

  // Active when some (but not all) items are selected
  const isActive = selectedCount > 0 && selectedCount < totalCount;
  // Warning when nothing is selected (will result in empty list)
  const isWarning = selectedCount === 0;

  // Check if a category is fully selected
  const isCategoryFullySelected = (category: TrigCategory): boolean => {
    return category.types.every((t) => selectedTypes.includes(t.code));
  };

  // Check if a category is partially selected
  const isCategoryPartiallySelected = (category: TrigCategory): boolean => {
    const selectedInCat = category.types.filter((t) => selectedTypes.includes(t.code));
    return selectedInCat.length > 0 && selectedInCat.length < category.types.length;
  };

  // Handle toggling an entire category's types
  const handleCategoryToggle = (category: TrigCategory) => {
    const isFullySelected = isCategoryFullySelected(category);
    const isCategorySelectedInMainUI = selectedCategories.includes(category.id);
    
    // Determine desired state: if fully selected, we want to deselect; otherwise select
    const wantSelected = !isFullySelected;
    
    // Only toggle the main category button if its state doesn't match what we want
    if (wantSelected !== isCategorySelectedInMainUI) {
      onToggleCategory(category.id);
    }
    
    // Toggle all types in this category to match the desired state
    category.types.forEach((type) => {
      const isSelected = selectedTypes.includes(type.code);
      if (wantSelected && !isSelected) {
        // We want to select, and it's not selected - toggle it on
        onToggleType(type.code);
      } else if (!wantSelected && isSelected) {
        // We want to deselect, and it's selected - toggle it off
        onToggleType(type.code);
      }
    });
  };

  return (
    <FilterChip
      label="Type"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={onSelectAll}
      popoverWidth="lg"
      icon={<Tag className="w-3.5 h-3.5" />}
    >
      <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
      <div className="py-1">
        {TYPE_CATEGORIES.map((category) => {
          const isExpanded = expandedCategories.has(category.code);
          const isFullySelected = isCategoryFullySelected(category);
          const isPartial = isCategoryPartiallySelected(category);
          
          return (
            <div key={category.code}>
              {/* Category header */}
            <div className="flex items-center px-3 py-2 hover:bg-trig-green-50 dark:hover:bg-gray-800">
                {/* Expand/collapse button */}
                <button
                  type="button"
                  onClick={() => toggleCategoryExpanded(category.code)}
                  className="p-0.5 mr-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {isExpanded ? (
                    <ChevronDown className="w-4 h-4" />
                  ) : (
                    <ChevronRight className="w-4 h-4" />
                  )}
                </button>
                
                {/* Category checkbox */}
              <label className="flex items-center gap-2 cursor-pointer flex-1">
                <FilterCheckbox
                  checked={isFullySelected}
                  indeterminate={isPartial}
                  onChange={() => handleCategoryToggle(category)}
                  ariaLabel={category.name}
                />
                  <img
                    src={category.icon}
                    alt=""
                    className="w-5 h-5 object-contain"
                  />
                <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                    {category.name}
                  </span>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                    ({category.types.filter((t) => selectedTypes.includes(t.code)).length}/{category.types.length})
                  </span>
                </label>
              </div>
              
              {/* Expanded types */}
              {isExpanded && (
                <div className="pl-4">
                  {category.types.map((type) => (
                    <FilterListItem
                      key={type.code}
                      label={type.name}
                      checked={selectedTypes.includes(type.code)}
                      onChange={() => onToggleType(type.code)}
                      indented
                    />
                  ))}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </FilterChip>
  );
}

export default TypeChip;

