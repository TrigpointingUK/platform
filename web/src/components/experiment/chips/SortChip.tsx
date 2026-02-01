/**
 * SortChip - A chip for selecting sort options
 * 
 * Unlike filter chips, only one sort chip can be active at a time.
 * Clicking an active chip toggles the sort direction.
 */

import { ReactNode } from "react";
import { ArrowUp, ArrowDown } from "lucide-react";

export type SortDirection = "asc" | "desc";

export interface SortChipProps {
  /** Label shown on the chip */
  label: string;
  /** Unique identifier for this sort option */
  sortKey: string;
  /** Currently active sort key */
  activeSortKey: string;
  /** Current sort direction */
  sortDirection: SortDirection;
  /** Called when this chip is clicked */
  onSort: (sortKey: string, direction: SortDirection) => void;
  /** Icon to display */
  icon?: ReactNode;
  /** Whether this sort requires a location */
  requiresLocation?: boolean;
  /** Whether location is available */
  hasLocation?: boolean;
}

export function SortChip({
  label,
  sortKey,
  activeSortKey,
  sortDirection,
  onSort,
  icon,
  requiresLocation = false,
  hasLocation = true,
}: SortChipProps) {
  const isActive = activeSortKey === sortKey;
  const isDisabled = requiresLocation && !hasLocation;

  const handleClick = () => {
    if (isDisabled) return;
    
    if (isActive) {
      // Toggle direction
      onSort(sortKey, sortDirection === "asc" ? "desc" : "asc");
    } else {
      // Activate with default direction (desc for distance, asc for others)
      const defaultDirection: SortDirection = sortKey === "distance" ? "asc" : "asc";
      onSort(sortKey, defaultDirection);
    }
  };

  return (
    <button
      type="button"
      onClick={handleClick}
      disabled={isDisabled}
      className={`
        inline-flex items-center gap-1.5 px-3 py-1.5
        w-44 text-sm font-medium rounded-full
        border transition-all duration-150
        ${isDisabled
          ? "bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed"
          : isActive
            ? "bg-trig-green-50 dark:bg-trig-green-900/30 border-trig-green-300 dark:border-trig-green-700 text-trig-green-700 dark:text-trig-green-300"
            : "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400 dark:hover:border-gray-500 cursor-pointer"
        }
      `}
      title={isDisabled ? "Requires a location to be set" : undefined}
    >
      {icon && <span className="flex-shrink-0">{icon}</span>}
      <span className="flex-1 text-left truncate">{label}</span>
      {isActive && (
        <span className="flex-shrink-0">
          {sortDirection === "asc" ? (
            <ArrowUp className="w-3.5 h-3.5" />
          ) : (
            <ArrowDown className="w-3.5 h-3.5" />
          )}
        </span>
      )}
    </button>
  );
}

export default SortChip;

