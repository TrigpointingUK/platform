/**
 * Hook for fetching trig type categories and types from the API.
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
  category_id: number;
}

export interface TrigCategory {
  id: number;
  code: string;
  name: string;
  description: string | null;
  wiki_url: string | null;
  sort_order: number;
  types: TrigType[];
}

/**
 * Fetch all trig type categories with their nested types.
 */
export function useTrigCategories() {
  return useQuery<TrigCategory[]>({
    queryKey: ["trigCategories"],
    queryFn: async () => {
      return apiGet<TrigCategory[]>("/v1/types/categories");
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - types rarely change
    gcTime: 24 * 60 * 60 * 1000,
  });
}

/**
 * Get category codes that should be selected based on a max sort_order threshold.
 */
export function getCategoryCodesUpToSortOrder(
  categories: TrigCategory[],
  maxSortOrder: number,
): string[] {
  return categories.filter((c) => c.sort_order <= maxSortOrder).map((c) => c.code);
}

/**
 * Map legacy status IDs to new category codes (trig_category.code).
 * Used during the transition period.
 * 
 * Note: These map to trig_category.code values, NOT status.name.
 * The status table uses different names (e.g., "Major mark" vs "FBM").
 */
export const LEGACY_STATUS_TO_CATEGORY: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "SURVEY_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

/**
 * Map new category codes to legacy status IDs.
 * Used during the transition period.
 */
export const CATEGORY_TO_LEGACY_STATUS: Record<string, number> = {
  PILLAR: 10,
  FBM: 20,
  SURVEY_MARK: 30,
  INTERSECTED: 40,
  ACTIVE: 50,
  OTHER: 60,
};

/**
 * Convert legacy status IDs to category codes.
 */
export function statusIdsToCategoryCodes(statusIds: number[]): string[] {
  return statusIds
    .map((id) => LEGACY_STATUS_TO_CATEGORY[id])
    .filter((code): code is string => code !== undefined);
}

/**
 * Convert category codes to legacy status IDs.
 */
export function categoryCodesToStatusIds(categoryCodes: string[]): number[] {
  return categoryCodes
    .map((code) => CATEGORY_TO_LEGACY_STATUS[code.toUpperCase()])
    .filter((id): id is number => id !== undefined);
}
