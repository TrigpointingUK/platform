/**
 * Hook for fetching trig type groups and types from the API.
 */

import { useQuery } from "@tanstack/react-query";
import { apiGet } from "../lib/api";

// Type definitions matching the API response
export interface TrigType {
  id: number;
  code: string;
  name: string;
  description: string | null;
  wiki_url: string | null;
  sort_order: number;
  group_id: number;
}

export interface TrigTypeGroup {
  id: number;
  code: string;
  name: string;
  description: string | null;
  wiki_url: string | null;
  sort_order: number;
  types: TrigType[];
}

/**
 * Fetch all trig type groups with their nested types.
 */
export function useTrigTypeGroups() {
  return useQuery<TrigTypeGroup[]>({
    queryKey: ["trigTypeGroups"],
    queryFn: async () => {
      return apiGet<TrigTypeGroup[]>("/v1/types/groups");
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - types rarely change
    gcTime: 24 * 60 * 60 * 1000,
  });
}

/**
 * Get group codes that should be selected based on a max sort_order threshold.
 * This mirrors the legacy status_max behaviour.
 */
export function getGroupCodesUpToSortOrder(
  groups: TrigTypeGroup[],
  maxSortOrder: number,
): string[] {
  return groups.filter((g) => g.sort_order <= maxSortOrder).map((g) => g.code);
}

/**
 * Map legacy status IDs to new group codes.
 * Used during the transition period.
 */
export const LEGACY_STATUS_TO_GROUP: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "MINOR_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

/**
 * Map new group codes to legacy status IDs.
 * Used during the transition period.
 */
export const GROUP_TO_LEGACY_STATUS: Record<string, number> = {
  PILLAR: 10,
  FBM: 20,
  MINOR_MARK: 30,
  INTERSECTED: 40,
  ACTIVE: 50,
  OTHER: 60,
};

/**
 * Convert legacy status IDs to group codes.
 */
export function statusIdsToGroupCodes(statusIds: number[]): string[] {
  return statusIds
    .map((id) => LEGACY_STATUS_TO_GROUP[id])
    .filter((code): code is string => code !== undefined);
}

/**
 * Convert group codes to legacy status IDs.
 */
export function groupCodesToStatusIds(groupCodes: string[]): number[] {
  return groupCodes
    .map((code) => GROUP_TO_LEGACY_STATUS[code.toUpperCase()])
    .filter((id): id is number => id !== undefined);
}
