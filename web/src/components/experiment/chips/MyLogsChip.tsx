/**
 * MyLogsChip - Filter chip for filtering by user's logged status
 * 
 * Two-tier structure:
 * - "Logged by me" expands to show individual conditions
 * - "Not logged by me" is a simple toggle
 */

import { useState } from "react";
import { CheckCircle, ChevronRight, ChevronDown } from "lucide-react";
import { FilterChip, FilterListItem, FilterCheckbox } from "../FilterChip";

// Condition values for logged trigs - using same values as ConditionChip
export const LOGGED_CONDITION_VALUES = [
  { code: "G", label: "Good", icon: "c_good.png", mapIcon: "mapicon_pillar_green.png" },
  { code: "S", label: "Slightly Damaged", icon: "c_slightlydamaged.png", mapIcon: "mapicon_pillar_yellow.png" },
  { code: "D", label: "Damaged", icon: "c_damaged.png", mapIcon: "mapicon_pillar_orange.png" },
  { code: "T", label: "Toppled", icon: "c_toppled.png", mapIcon: "mapicon_pillar_orange.png" },
  { code: "C", label: "Converted", icon: "c_slightlydamaged.png", mapIcon: "mapicon_pillar_yellow.png" },
  { code: "R", label: "Remains", icon: "c_toppled.png", mapIcon: "mapicon_pillar_orange.png" },
  { code: "X", label: "Destroyed", icon: "c_definitelymissing.png", mapIcon: "mapicon_pillar_red.png" },
  { code: "V", label: "Unreachable but Visible", icon: "c_unreachablebutvisible.png", mapIcon: "mapicon_pillar_yellow.png" },
  { code: "P", label: "Inaccessible", icon: "c_unknown.png", mapIcon: "mapicon_pillar_grey.png" },
  { code: "U", label: "Unknown", icon: "c_unknown.png", mapIcon: "mapicon_pillar_grey.png" },
  { code: "Q", label: "Possibly Missing", icon: "c_possiblymissing.png", mapIcon: "mapicon_pillar_orange.png" },
  { code: "N", label: "Couldn't Find", icon: "c_possiblymissing.png", mapIcon: "mapicon_pillar_grey.png" },
];

export const ALL_LOGGED_CONDITION_CODES = LOGGED_CONDITION_VALUES.map(c => c.code);

export interface MyLogsChipProps {
  selectedLoggedConditions: string[];
  showNotLogged: boolean;
  onToggleLoggedCondition: (code: string) => void;
  onToggleNotLogged: () => void;
  onSelectAllLogged: () => void;
  onSelectNoneLogged: () => void;
  isAuthenticated: boolean;
}

export function MyLogsChip({
  selectedLoggedConditions,
  showNotLogged,
  onToggleLoggedCondition,
  onToggleNotLogged,
  onSelectAllLogged,
  onSelectNoneLogged,
  isAuthenticated,
}: MyLogsChipProps) {
  const [isLoggedExpanded, setIsLoggedExpanded] = useState(false);
  
  const allLoggedSelected = selectedLoggedConditions.length === LOGGED_CONDITION_VALUES.length;
  const someLoggedSelected = selectedLoggedConditions.length > 0;
  const isPartialLogged = someLoggedSelected && !allLoggedSelected;

  // Generate summary
  let summary: string;
  if (allLoggedSelected && showNotLogged) {
    summary = "All";
  } else if (!someLoggedSelected && !showNotLogged) {
    summary = "None";
  } else if (!someLoggedSelected && showNotLogged) {
    summary = "Not logged only";
  } else if (allLoggedSelected && !showNotLogged) {
    summary = "Logged only";
  } else if (someLoggedSelected && !showNotLogged) {
    summary = `${selectedLoggedConditions.length} logged conditions`;
  } else {
    // Some logged conditions + not logged
    summary = `${selectedLoggedConditions.length} logged conditions +`;
  }

  // Active when filtered (not showing everything)
  const isActive = !(allLoggedSelected && showNotLogged);
  // Warning when nothing is selected
  const isWarning = !someLoggedSelected && !showNotLogged;

  const handleClear = () => {
    // Reset to showing all
    onSelectAllLogged();
    if (!showNotLogged) onToggleNotLogged();
  };

  const handleToggleAllLogged = () => {
    if (allLoggedSelected) {
      onSelectNoneLogged();
    } else {
      onSelectAllLogged();
    }
  };

  if (!isAuthenticated) {
    return null; // Don't show this chip for unauthenticated users
  }

  return (
    <FilterChip
      label="My logs"
      summary={summary}
      isActive={isActive}
      isWarning={isWarning}
      clearable={isActive || isWarning}
      onClear={handleClear}
      popoverWidth="lg"
      icon={<CheckCircle className="w-3.5 h-3.5" />}
    >
      {/* Quick selection shortcuts */}
      <div className="px-3 py-2 border-b border-gray-200 dark:border-gray-700 flex gap-2">
        <button
          type="button"
          onClick={handleClear}
          className="px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 
                     hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
        >
          All
        </button>
        <button
          type="button"
          onClick={() => {
            onSelectAllLogged();
            if (showNotLogged) onToggleNotLogged();
          }}
          className="px-2 py-1 text-xs font-medium text-trig-green-600 dark:text-trig-green-400 
                     hover:bg-trig-green-50 dark:hover:bg-trig-green-900/30 rounded transition-colors"
        >
          Logged only
        </button>
        <button
          type="button"
          onClick={() => {
            onSelectNoneLogged();
            if (!showNotLogged) onToggleNotLogged();
          }}
          className="px-2 py-1 text-xs font-medium text-gray-600 dark:text-gray-400 
                     hover:bg-gray-100 dark:hover:bg-gray-700 rounded transition-colors"
        >
          Not logged only
        </button>
      </div>
      <div className="py-1">
        {/* Not logged by me - simple toggle (at top) */}
        <div className="flex items-center px-3 py-2 hover:bg-trig-green-50 dark:hover:bg-gray-800 transition-colors">
          {/* Spacer to align with expand button below */}
          <div className="w-4 h-4 p-0.5 mr-1" />
          <label className="flex items-center gap-2 cursor-pointer flex-1">
            <FilterCheckbox
              checked={showNotLogged}
              onChange={onToggleNotLogged}
              ariaLabel="Not logged by me"
            />
            <img src="/icons/mapicon_pillar_grey.png" alt="" className="w-5 h-5" />
            <span className="text-sm text-gray-800 dark:text-gray-200">
              Not logged by me
            </span>
          </label>
        </div>

        {/* Logged by me - expandable */}
        <div>
          <div className="flex items-center px-3 py-2 hover:bg-trig-green-50 dark:hover:bg-gray-800">
            {/* Expand/collapse button */}
            <button
              type="button"
              onClick={() => setIsLoggedExpanded(!isLoggedExpanded)}
              className="p-0.5 mr-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
            >
              {isLoggedExpanded ? (
                <ChevronDown className="w-4 h-4" />
              ) : (
                <ChevronRight className="w-4 h-4" />
              )}
            </button>
            
            {/* Logged checkbox */}
            <label className="flex items-center gap-2 cursor-pointer flex-1">
              <FilterCheckbox
                checked={allLoggedSelected}
                indeterminate={isPartialLogged}
                onChange={handleToggleAllLogged}
                ariaLabel="Logged by me"
              />
              <div className="flex -space-x-1">
                <img src="/icons/mapicon_pillar_green.png" alt="" className="w-5 h-5" />
                <img src="/icons/mapicon_pillar_yellow.png" alt="" className="w-5 h-5" />
                <img src="/icons/mapicon_pillar_red.png" alt="" className="w-5 h-5" />
              </div>
              <span className="text-sm font-medium text-gray-800 dark:text-gray-200">
                Logged by me
              </span>
              <span className="text-xs text-gray-500 dark:text-gray-400">
                ({selectedLoggedConditions.length}/{LOGGED_CONDITION_VALUES.length})
              </span>
            </label>
          </div>
          
          {/* Expanded conditions */}
          {isLoggedExpanded && (
            <div className="pl-4">
              {LOGGED_CONDITION_VALUES.map((condition) => (
                <FilterListItem
                  key={condition.code}
                  label={condition.label}
                  checked={selectedLoggedConditions.includes(condition.code)}
                  onChange={() => onToggleLoggedCondition(condition.code)}
                  icon={
                    <img
                      src={`/icons/conditions/${condition.icon}`}
                      alt=""
                      className="w-5 h-5 object-contain"
                    />
                  }
                  indented
                />
              ))}
            </div>
          )}
        </div>
      </div>
    </FilterChip>
  );
}

export default MyLogsChip;
