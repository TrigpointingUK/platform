import { useInfiniteQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedFetch } from "../lib/api";
import {
  buildTrigFilterParams,
  selectsNothing,
  type TrigFilterOptions,
} from "../lib/trigFilterParams";

const API_BASE = import.meta.env.VITE_API_BASE as string;

interface Trig {
  id: number;
  waypoint: string;
  name: string;
  condition: string;
  wgs_lat: string;
  wgs_long: string;
  osgb_gridref: string;
  status_name?: string;
  type_code?: string;
  type_name?: string;
  category_code?: string;
  category_name?: string;
  distance_km?: number;
  wgs_height?: number;
  score?: number;
  first_logged_date?: string | null; // Present when a log user is being looked at
  first_logged_time?: string | null;
}

interface TrigsResponse {
  items: Trig[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
  links: {
    self: string;
    next: string | null;
    prev: string | null;
  };
  context?: {
    centre?: {
      lat: number;
      lon: number;
      srid: number;
    };
    max_km?: number;
    order?: string;
    logged_by?: number;
  };
}

export interface UseInfiniteTrigsOptions extends TrigFilterOptions {
  order?: string; // Sort order: distance | name | height | score | logged (prefix with - for desc)
}

export function useInfiniteTrigs(options: UseInfiniteTrigsOptions = {}) {
  const { order, ...filters } = options;
  const { lat, lon } = filters;
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  return useInfiniteQuery<TrigsResponse>({
    queryKey: ["trigs", "infinite", filters, order],
    enabled: lat !== undefined && lon !== undefined, // Only fetch when location is set
    queryFn: async ({ pageParam }: { pageParam?: unknown }) => {
      // If any filter is an empty selection, return empty results (user selected nothing)
      if (selectsNothing(filters)) {
        return {
          items: [],
          pagination: { total: 0, limit: 50, offset: 0, has_more: false },
          links: { self: "", next: null, prev: null },
        };
      }

      const skip = typeof pageParam === "number" ? pageParam : 0;
      const params = buildTrigFilterParams(filters);
      params.append("limit", "50");
      params.append("skip", skip.toString());

      // Set sort order - default to distance when coordinates available
      const effectiveOrder = order || (lat !== undefined && lon !== undefined ? "distance" : "name");
      params.append("order", effectiveOrder);

      // Use authenticated fetch if logged in for log filters
      const url = `${API_BASE}/v1/trigs?${params.toString()}`;
      const response = isAuthenticated
        ? await authenticatedFetch(url, {}, getAccessTokenSilently)
        : await fetch(url);

      if (!response.ok) {
        throw new Error("Failed to fetch trigpoints");
      }

      return response.json();
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      return lastPage.pagination.has_more
        ? lastPage.pagination.offset + lastPage.pagination.limit
        : null;
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
