/**
 * CategoryFilter component for filtering trigpoints by type category.
 *
 * This is the new type system replacement for StatusFilter.
 * It fetches categories from the API and displays them as toggleable buttons.
 */

import { useTrigCategories } from "../../hooks/useTrigTypes";

// Icons for each category (matching trig_category.code from API)
// Note: ACTIVE and OTHER icons use SVG files with ? and ! symbols
const CATEGORY_ICONS: Record<string, string> = {
  PILLAR: "/icons/t_pillar.png",
  FBM: "/icons/t_fbm.png",
  SURVEY_MARK: "/icons/t_passive.png",
  INTERSECTED: "/icons/t_intersected.png",
  ACTIVE: "/icons/t_active.png",
  OTHER: "/icons/t_other.svg",
};

// Fallback icon
const DEFAULT_ICON = "/icons/t_other.svg";

interface CategoryFilterProps {
  selectedCategories: string[];
  onToggleCategory: (categoryCode: string) => void;
  visibleCategories?: string[]; // Only show these categories (by code)
}

export function CategoryFilter({
  selectedCategories,
  onToggleCategory,
  visibleCategories,
}: CategoryFilterProps) {
  const { data: categories, isLoading, error } = useTrigCategories();

  if (isLoading) {
    return (
      <div className="flex flex-wrap gap-2">
        {/* Skeleton loading state */}
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700 animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error || !categories) {
    return (
      <div className="text-sm text-red-600 dark:text-red-400">Failed to load type categories</div>
    );
  }

  const categoriesToShow = visibleCategories
    ? categories.filter((c) => visibleCategories.includes(c.code))
    : categories;

  return (
    <div className="flex flex-wrap gap-2">
      {categoriesToShow.map((category) => {
        const isSelected = selectedCategories.includes(category.code);
        const icon = CATEGORY_ICONS[category.code] || DEFAULT_ICON;

        return (
          <button
            key={category.code}
            type="button"
            onClick={() => onToggleCategory(category.code)}
            className={`
              inline-flex items-center justify-center
              w-10 h-10 p-1 rounded-lg
              transition-all duration-200
              ${
                isSelected
                  ? "bg-trig-green-600 shadow-md scale-105 ring-2 ring-white"
                  : "bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
              }
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            `}
            title={category.name}
            aria-label={`${isSelected ? "Deselect" : "Select"} ${category.name}`}
            aria-pressed={isSelected}
          >
            <img
              src={icon}
              alt={category.name}
              className={`w-full h-full object-contain ${
                isSelected ? "" : "opacity-60"
              }`}
            />
          </button>
        );
      })}
    </div>
  );
}

/**
 * Hybrid filter that shows categories but uses legacy status IDs for API calls.
 * This is useful during the transition period.
 */
interface HybridCategoryFilterProps {
  selectedStatuses: number[];
  onToggleStatus: (statusId: number) => void;
  visibleStatuses?: number[];
}

// Map status IDs to category codes (trig_category.code)
const STATUS_TO_CATEGORY: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "SURVEY_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

// Map category codes to status IDs
const CATEGORY_TO_STATUS: Record<string, number> = {
  PILLAR: 10,
  FBM: 20,
  SURVEY_MARK: 30,
  INTERSECTED: 40,
  ACTIVE: 50,
  OTHER: 60,
};

export function HybridCategoryFilter({
  selectedStatuses,
  onToggleStatus,
  visibleStatuses,
}: HybridCategoryFilterProps) {
  const { data: categories, isLoading, error } = useTrigCategories();

  if (isLoading) {
    return (
      <div className="flex flex-wrap gap-2">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div
            key={i}
            className="w-10 h-10 rounded-lg bg-gray-200 dark:bg-gray-700 animate-pulse"
          />
        ))}
      </div>
    );
  }

  if (error || !categories) {
    // Fall back to showing nothing on error
    return null;
  }

  // Convert visible statuses to category codes
  const visibleCategoryCodes = visibleStatuses
    ? visibleStatuses.map((id) => STATUS_TO_CATEGORY[id]).filter(Boolean)
    : undefined;

  const categoriesToShow = visibleCategoryCodes
    ? categories.filter((c) => visibleCategoryCodes.includes(c.code))
    : categories;

  // Convert selected statuses to category codes for display
  const selectedCategoryCodes = selectedStatuses
    .map((id) => STATUS_TO_CATEGORY[id])
    .filter(Boolean);

  const handleToggle = (categoryCode: string) => {
    const statusId = CATEGORY_TO_STATUS[categoryCode];
    if (statusId !== undefined) {
      onToggleStatus(statusId);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {categoriesToShow.map((category) => {
        const isSelected = selectedCategoryCodes.includes(category.code);
        const icon = CATEGORY_ICONS[category.code] || DEFAULT_ICON;

        return (
          <button
            key={category.code}
            type="button"
            onClick={() => handleToggle(category.code)}
            className={`
              inline-flex items-center justify-center
              w-10 h-10 p-1 rounded-lg
              transition-all duration-200
              ${
                isSelected
                  ? "bg-trig-green-600 shadow-md scale-105 ring-2 ring-white"
                  : "bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
              }
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            `}
            title={category.name}
            aria-label={`${isSelected ? "Deselect" : "Select"} ${category.name}`}
            aria-pressed={isSelected}
          >
            <img
              src={icon}
              alt={category.name}
              className={`w-full h-full object-contain ${
                isSelected ? "" : "opacity-60"
              }`}
            />
          </button>
        );
      })}
    </div>
  );
}

