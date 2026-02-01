/**
 * Hooks for fetching reference/lookup data from the API.
 *
 * These hooks cache the data for 24 hours since reference data rarely changes.
 */

import { useQuery } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_BASE as string;

// =============================================================================
// Types
// =============================================================================

export interface TrigType {
  id: number;
  code: string;
  name: string;
  description?: string;
  sort_order: number;
}

export interface TrigCategory {
  id: number;
  code: string;
  name: string;
  description?: string;
  icon_file?: string;
  sort_order: number;
  types: TrigType[];
}

export interface Condition {
  code: string;
  name: string;
  description?: string;
  icon_file?: string;
  trig_colour?: string;
  log_colour?: string;
  sort_order: number;
}

export interface AreaType {
  id: number;
  code: string;
  name: string;
  description?: string;
}

export interface Area {
  id: number;
  name: string;
  code?: string;
  area_type_id: number;
  area_type?: AreaType;
  center_lat?: number;
  center_lon?: number;
}

export interface ReferenceValue {
  value: string;
  label: string;
}

// =============================================================================
// Categories with Types Hook
// =============================================================================

export function useTrigCategories() {
  return useQuery<TrigCategory[]>({
    queryKey: ["reference", "trigCategories"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/v1/types/categories`);
      if (!response.ok) {
        throw new Error("Failed to fetch trig categories");
      }
      return response.json();
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// =============================================================================
// Conditions Hook
// =============================================================================

export function useConditions() {
  return useQuery<Condition[]>({
    queryKey: ["reference", "conditions"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/v1/conditions`);
      if (!response.ok) {
        throw new Error("Failed to fetch conditions");
      }
      return response.json();
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// =============================================================================
// Historic Use Values Hook
// =============================================================================

export function useHistoricUseValues() {
  return useQuery<ReferenceValue[]>({
    queryKey: ["reference", "historicUse"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/v1/reference/historic-use`);
      if (!response.ok) {
        throw new Error("Failed to fetch historic use values");
      }
      const data = await response.json();
      return data.values;
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// =============================================================================
// Current Use Values Hook
// =============================================================================

export function useCurrentUseValues() {
  return useQuery<ReferenceValue[]>({
    queryKey: ["reference", "currentUse"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/v1/reference/current-use`);
      if (!response.ok) {
        throw new Error("Failed to fetch current use values");
      }
      const data = await response.json();
      return data.values;
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// =============================================================================
// Area Types Hook
// =============================================================================

export function useAreaTypes() {
  return useQuery<AreaType[]>({
    queryKey: ["reference", "areaTypes"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/v1/areas/types`);
      if (!response.ok) {
        throw new Error("Failed to fetch area types");
      }
      return response.json();
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// =============================================================================
// Areas by Type Hook
// =============================================================================

interface UseAreasByTypeOptions {
  typeId: number | null;
  lat?: number;
  lon?: number;
  order?: "name" | "distance";
}

export function useAreasByType(options: UseAreasByTypeOptions) {
  const { typeId, lat, lon, order = "name" } = options;

  return useQuery<Area[]>({
    queryKey: ["reference", "areasByType", typeId, lat, lon, order],
    enabled: typeId !== null,
    queryFn: async () => {
      const params = new URLSearchParams();
      if (lat !== undefined && lon !== undefined) {
        params.append("lat", lat.toString());
        params.append("lon", lon.toString());
      }
      params.append("order", order);

      const response = await fetch(
        `${API_BASE}/v1/areas/by-type/${typeId}?${params.toString()}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch areas");
      }
      return response.json();
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours
  });
}

// =============================================================================
// Combined Reference Data Hook
// =============================================================================

/**
 * Fetches all reference data at once.
 * Useful for preloading data on page load.
 */
export function useAllReferenceData() {
  const categories = useTrigCategories();
  const conditions = useConditions();
  const historicUse = useHistoricUseValues();
  const currentUse = useCurrentUseValues();
  const areaTypes = useAreaTypes();

  return {
    categories,
    conditions,
    historicUse,
    currentUse,
    areaTypes,
    isLoading:
      categories.isLoading ||
      conditions.isLoading ||
      historicUse.isLoading ||
      currentUse.isLoading ||
      areaTypes.isLoading,
    isError:
      categories.isError ||
      conditions.isError ||
      historicUse.isError ||
      currentUse.isError ||
      areaTypes.isError,
  };
}

