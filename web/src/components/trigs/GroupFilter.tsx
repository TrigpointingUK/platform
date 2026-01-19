/**
 * GroupFilter component for filtering trigpoints by type group.
 *
 * This is the new type system replacement for StatusFilter.
 * It fetches groups from the API and displays them as toggleable buttons.
 */

import { useTrigTypeGroups } from "../../hooks/useTrigTypes";

// Icons for each group (matching trig_type_group.code from API)
// Note: ACTIVE and OTHER icons use SVG files with ? and ! symbols
const GROUP_ICONS: Record<string, string> = {
  PILLAR: "/icons/t_pillar.png",
  FBM: "/icons/t_fbm.png",
  SURVEY_MARK: "/icons/t_passive.png",
  INTERSECTED: "/icons/t_intersected.png",
  ACTIVE: "/icons/t_active.png",
  OTHER: "/icons/t_other.svg",
};

// Fallback icon
const DEFAULT_ICON = "/icons/t_other.svg";

interface GroupFilterProps {
  selectedGroups: string[];
  onToggleGroup: (groupCode: string) => void;
  visibleGroups?: string[]; // Only show these groups (by code)
}

export function GroupFilter({
  selectedGroups,
  onToggleGroup,
  visibleGroups,
}: GroupFilterProps) {
  const { data: groups, isLoading, error } = useTrigTypeGroups();

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

  if (error || !groups) {
    return (
      <div className="text-sm text-red-600 dark:text-red-400">Failed to load type groups</div>
    );
  }

  const groupsToShow = visibleGroups
    ? groups.filter((g) => visibleGroups.includes(g.code))
    : groups;

  return (
    <div className="flex flex-wrap gap-2">
      {groupsToShow.map((group) => {
        const isSelected = selectedGroups.includes(group.code);
        const icon = GROUP_ICONS[group.code] || DEFAULT_ICON;

        return (
          <button
            key={group.code}
            type="button"
            onClick={() => onToggleGroup(group.code)}
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
            title={group.name}
            aria-label={`${isSelected ? "Deselect" : "Select"} ${group.name}`}
            aria-pressed={isSelected}
          >
            <img
              src={icon}
              alt={group.name}
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
 * Hybrid filter that shows groups but uses legacy status IDs for API calls.
 * This is useful during the transition period.
 */
interface HybridGroupFilterProps {
  selectedStatuses: number[];
  onToggleStatus: (statusId: number) => void;
  visibleStatuses?: number[];
}

// Map status IDs to group codes (trig_type_group.code)
const STATUS_TO_GROUP: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "SURVEY_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

// Map group codes to status IDs
const GROUP_TO_STATUS: Record<string, number> = {
  PILLAR: 10,
  FBM: 20,
  SURVEY_MARK: 30,
  INTERSECTED: 40,
  ACTIVE: 50,
  OTHER: 60,
};

export function HybridGroupFilter({
  selectedStatuses,
  onToggleStatus,
  visibleStatuses,
}: HybridGroupFilterProps) {
  const { data: groups, isLoading, error } = useTrigTypeGroups();

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

  if (error || !groups) {
    // Fall back to showing nothing on error
    return null;
  }

  // Convert visible statuses to group codes
  const visibleGroupCodes = visibleStatuses
    ? visibleStatuses.map((id) => STATUS_TO_GROUP[id]).filter(Boolean)
    : undefined;

  const groupsToShow = visibleGroupCodes
    ? groups.filter((g) => visibleGroupCodes.includes(g.code))
    : groups;

  // Convert selected statuses to group codes for display
  const selectedGroupCodes = selectedStatuses
    .map((id) => STATUS_TO_GROUP[id])
    .filter(Boolean);

  const handleToggle = (groupCode: string) => {
    const statusId = GROUP_TO_STATUS[groupCode];
    if (statusId !== undefined) {
      onToggleStatus(statusId);
    }
  };

  return (
    <div className="flex flex-wrap gap-2">
      {groupsToShow.map((group) => {
        const isSelected = selectedGroupCodes.includes(group.code);
        const icon = GROUP_ICONS[group.code] || DEFAULT_ICON;

        return (
          <button
            key={group.code}
            type="button"
            onClick={() => handleToggle(group.code)}
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
            title={group.name}
            aria-label={`${isSelected ? "Deselect" : "Select"} ${group.name}`}
            aria-pressed={isSelected}
          >
            <img
              src={icon}
              alt={group.name}
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
