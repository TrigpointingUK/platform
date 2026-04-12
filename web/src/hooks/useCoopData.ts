import { useInfiniteQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedFetch } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

export interface CoopVisit {
  log_id: number;
  condition: string;
  date: string | null;
}

export interface CoopTrigItem {
  id: number;
  waypoint: string;
  name: string;
  condition: string;
  type_code: string | null;
  type_name: string | null;
  category_code: string | null;
  category_name: string | null;
  wgs_lat: number;
  wgs_long: number;
  osgb_gridref: string;
  distance_km: number | null;
  visits: Record<string, CoopVisit | null>;
}

export interface CoopUser {
  id: number;
  name: string;
}

export interface CoopResponse {
  users: CoopUser[];
  items: CoopTrigItem[];
  total: number;
  skip: number;
  limit: number;
  has_more: boolean;
}

export type CoopFilterMode = "all" | "unvisited_by_all" | "visited_by_any" | "unvisited_by_me" | "visited_by_me" | "only_visited_by_me" | "visited_by_all" | "visited_by_all_except_me" | "visited_by_most" | "not_visited_by_most";

export interface UseCoopDataOptions {
  userIds: number[];
  lat?: number;
  lon?: number;
  maxKm?: number;
  categories?: string[];
  types?: string[];
  filterMode?: CoopFilterMode;
}

export function useCoopData(options: UseCoopDataOptions) {
  const {
    userIds,
    lat,
    lon,
    maxKm,
    categories,
    types,
    filterMode = "all",
  } = options;
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  const enabled =
    isAuthenticated &&
    userIds.length > 1 &&
    lat !== undefined &&
    lon !== undefined;

  return useInfiniteQuery<CoopResponse>({
    queryKey: [
      "coop",
      userIds,
      lat,
      lon,
      maxKm,
      categories,
      types,
      filterMode,
    ],
    enabled,
    queryFn: async ({ pageParam }: { pageParam?: unknown }) => {
      const skip = typeof pageParam === "number" ? pageParam : 0;
      const params = new URLSearchParams();

      params.append("user_ids", userIds.join(","));
      params.append("limit", "50");
      params.append("skip", skip.toString());
      params.append("filter_mode", filterMode);

      if (lat !== undefined && lon !== undefined) {
        params.append("lat", lat.toString());
        params.append("lon", lon.toString());
      }

      if (maxKm !== undefined) {
        params.append("max_km", maxKm.toString());
      }

      if (categories && categories.length > 0) {
        params.append("categories", categories.join(","));
      }

      if (types && types.length > 0) {
        params.append("types", types.join(","));
      }

      const url = `${API_BASE}/v1/experiment/coop?${params.toString()}`;
      const response = await authenticatedFetch(
        url,
        {},
        getAccessTokenSilently,
      );

      if (!response.ok) {
        throw new Error("Failed to fetch co-op data");
      }

      return response.json();
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      return lastPage.has_more ? lastPage.skip + lastPage.limit : null;
    },
    staleTime: 5 * 60 * 1000,
  });
}
