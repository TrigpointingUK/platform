/**
 * TypeChip - Filter chip for physical trig types (hierarchical, grouped by category)
 * 
 * Types are grouped by category (Pillar, FBM, etc.) with expand/collapse functionality.
 * Toggling a category toggles all types within it.
 */

import { useState, useMemo } from "react";
import { Tag, ChevronRight, ChevronDown, Loader2 } from "lucide-react";
import { FilterChip, FilterListItem, FilterSelectionButtons, FilterCheckbox } from "../FilterChip";
import { useTrigCategories, type TrigCategory } from "../../../hooks/useReferenceData";

// Status ID to category code mapping (for the main UI toggle buttons)
const STATUS_ID_TO_CATEGORY_CODE: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "PASSIVE",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

export interface TypeChipProps {
  selectedTypes: string[];
  selectedCategories: number[]; // Status IDs for the main category buttons
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
  const { data: categories, isLoading, isError } = useTrigCategories();
  const [expandedCategories, setExpandedCategories] = useState<Set<string>>(new Set());

  // Get all type codes from the loaded categories
  const allTypeCodes = useMemo(() => {
    if (!categories) return [];
    return categories.flatMap((c) => c.types.map((t) => t.code));
  }, [categories]);

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
  const totalCount = allTypeCodes.length;
  
  // Build summary text
  let summary: string;
  if (isLoading) {
    summary = "Loading...";
  } else if (isError || !categories) {
    summary = "Error";
  } else if (selectedCount === 0) {
    summary = "None";
  } else if (selectedCount === totalCount) {
    summary = "All";
  } else {
    // Check if any full categories are selected
    const selectedCategoryNames = categories
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
  const isWarning = selectedCount === 0 && !isLoading;

  // Check if a category is fully selected
  const isCategoryFullySelected = (category: TrigCategory): boolean => {
    return category.types.every((t) => selectedTypes.includes(t.code));
  };

  // Check if a category is partially selected
  const isCategoryPartiallySelected = (category: TrigCategory): boolean => {
    const selectedInCat = category.types.filter((t) => selectedTypes.includes(t.code));
    return selectedInCat.length > 0 && selectedInCat.length < category.types.length;
  };

  // Find the status ID for a category code
  const getStatusIdForCategory = (categoryCode: string): number | null => {
    for (const [statusId, code] of Object.entries(STATUS_ID_TO_CATEGORY_CODE)) {
      if (code === categoryCode) {
        return parseInt(statusId, 10);
      }
    }
    return null;
  };

  // Handle toggling an entire category's types
  const handleCategoryToggle = (category: TrigCategory) => {
    const isFullySelected = isCategoryFullySelected(category);
    const statusId = getStatusIdForCategory(category.code);
    const isCategorySelectedInMainUI = statusId !== null && selectedCategories.includes(statusId);
    
    // Determine desired state: if fully selected, we want to deselect; otherwise select
    const wantSelected = !isFullySelected;
    
    // Only toggle the main category button if its state doesn't match what we want
    if (statusId !== null && wantSelected !== isCategorySelectedInMainUI) {
      onToggleCategory(statusId);
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

  // Get icon path for a category
  const getCategoryIcon = (category: TrigCategory): string => {
    if (category.icon_file) {
      return `/icons/${category.icon_file}`;
    }
    // Fallback icons based on category code
    const iconMap: Record<string, string> = {
      PILLAR: "/icons/t_pillar.png",
      FBM: "/icons/t_fbm.png",
      PASSIVE: "/icons/t_passive.png",
      SURVEY_MARK: "/icons/t_passive.png",
      INTERSECTED: "/icons/t_intersected.png",
      ACTIVE: "/icons/t_active.png",
      OTHER: "/icons/t_other.svg",
    };
    return iconMap[category.code] || "/icons/t_other.svg";
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
      {isLoading ? (
        <div className="flex items-center justify-center py-8">
          <Loader2 className="w-6 h-6 animate-spin text-gray-400" />
        </div>
      ) : isError || !categories ? (
        <div className="px-3 py-4 text-sm text-red-600 dark:text-red-400">
          Failed to load types. Please try again.
        </div>
      ) : (
        <>
          <FilterSelectionButtons onSelectAll={onSelectAll} onSelectNone={onSelectNone} />
          <div className="py-1">
            {categories.map((category) => {
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
                        src={getCategoryIcon(category)}
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
        </>
      )}
    </FilterChip>
  );
}

export default TypeChip;
