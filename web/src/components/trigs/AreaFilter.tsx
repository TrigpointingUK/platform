import { useState, useRef, useEffect } from "react";
import type { AreaGroup, Area } from "../../hooks/useAreasContaining";

interface AreaFilterProps {
  areaGroups: AreaGroup[];
  selectedAreaId: number | null;
  onSelectArea: (areaId: number | null, areaName: string | null) => void;
  isLoading?: boolean;
  disabled?: boolean;
}

// Helper to format area display text: "<area type> : <area name>"
function formatAreaDisplay(area: Area): string {
  return `${area.area_type.name} : ${area.name}`;
}

export function AreaFilter({
  areaGroups,
  selectedAreaId,
  onSelectArea,
  isLoading = false,
  disabled = false,
}: AreaFilterProps) {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Flatten all areas into a single list, sorted by area type name
  const allAreas = areaGroups
    .flatMap((g) => g.areas)
    .sort((a, b) => a.area_type.name.localeCompare(b.area_type.name));

  // Find the selected area
  const selectedArea = allAreas.find((a) => a.id === selectedAreaId);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectArea = (area: Area) => {
    onSelectArea(area.id, formatAreaDisplay(area));
    setIsOpen(false);
  };

  const handleClear = () => {
    onSelectArea(null, null);
    setIsOpen(false);
  };

  const hasAreas = allAreas.length > 0;

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Trigger button */}
      <button
        type="button"
        onClick={() => !disabled && setIsOpen(!isOpen)}
        disabled={disabled || !hasAreas}
        className={`
          inline-flex items-center justify-between gap-2
          px-4 py-2 min-w-[200px] max-w-[400px]
          text-left text-sm
          border border-gray-300 dark:border-gray-600 rounded-lg
          transition-colors
          ${disabled || !hasAreas
            ? "bg-gray-100 dark:bg-gray-700 text-gray-400 cursor-not-allowed"
            : "bg-white dark:bg-gray-800 dark:text-gray-200 hover:bg-gray-50 dark:hover:bg-gray-700 cursor-pointer"
          }
          ${isOpen ? "ring-2 ring-blue-500 border-transparent" : ""}
        `}
        aria-expanded={isOpen}
        aria-haspopup="listbox"
      >
        <span className="truncate">
          {isLoading ? (
            "Loading areas..."
          ) : !hasAreas ? (
            "First enter a location"
          ) : selectedArea ? (
            formatAreaDisplay(selectedArea)
          ) : (
            "Filter by area..."
          )}
        </span>
        <svg
          className={`w-4 h-4 text-gray-400 dark:text-gray-500 transition-transform flex-shrink-0 ${isOpen ? "rotate-180" : ""}`}
          fill="none"
          stroke="currentColor"
          viewBox="0 0 24 24"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {/* Clear button (shown when area is selected) */}
      {selectedArea && (
        <button
          type="button"
          onClick={handleClear}
          className="ml-2 px-2 py-2 text-gray-500 dark:text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 transition-colors"
          title="Clear area filter"
          aria-label="Clear area filter"
        >
          ✕
        </button>
      )}

      {/* Dropdown */}
      {isOpen && hasAreas && (
        <div
          className="absolute z-50 w-96 mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg dark:shadow-gray-900/50 max-h-96 overflow-y-auto"
          role="listbox"
        >
          {/* Clear option */}
          {selectedAreaId && (
            <button
              type="button"
              onClick={handleClear}
              className="w-full px-4 py-2 text-left text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-700 border-b border-gray-200 dark:border-gray-700"
            >
              Clear selection
            </button>
          )}

          {/* Flat list of all areas */}
          {allAreas.map((area) => (
            <button
              key={area.id}
              type="button"
              onClick={() => handleSelectArea(area)}
              className={`
                w-full px-4 py-2 text-left text-sm
                hover:bg-blue-50 dark:hover:bg-blue-900/30 transition-colors
                border-b border-gray-100 dark:border-gray-700 last:border-b-0
                ${selectedAreaId === area.id ? "bg-blue-100 dark:bg-blue-900/50 text-blue-700 dark:text-blue-300" : "text-gray-700 dark:text-gray-200"}
              `}
              role="option"
              aria-selected={selectedAreaId === area.id}
            >
              {formatAreaDisplay(area)}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
