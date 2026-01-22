/**
 * Hook to fetch and cache condition data from the API.
 *
 * Conditions are fetched once at app startup and cached indefinitely
 * since they rarely change. This replaces hardcoded condition mappings
 * throughout the application.
 */
import { useQuery } from "@tanstack/react-query";
import { fetchPublicConditions, type Condition } from "../lib/api";

/**
 * Query key for conditions - used for cache invalidation
 */
export const CONDITIONS_QUERY_KEY = ["conditions"] as const;

/**
 * Hook to fetch all conditions.
 *
 * Returns conditions sorted by sort_order.
 * Data is cached with staleTime: Infinity since conditions rarely change.
 */
export function useConditions() {
  return useQuery<Condition[]>({
    queryKey: CONDITIONS_QUERY_KEY,
    queryFn: fetchPublicConditions,
    staleTime: Infinity, // Conditions rarely change
    gcTime: Infinity, // Keep in cache forever
    retry: 2,
  });
}

/**
 * Build a lookup map from conditions array.
 * Use this for O(1) lookups by code.
 */
export function buildConditionMap(
  conditions: Condition[]
): Map<string, Condition> {
  return new Map(conditions.map((c) => [c.code, c]));
}

/**
 * Get condition by code from a pre-built map.
 * Returns undefined if code not found.
 */
export function getConditionFromMap(
  map: Map<string, Condition>,
  code: string | null | undefined
): Condition | undefined {
  if (!code) return undefined;
  return map.get(code.toUpperCase());
}

