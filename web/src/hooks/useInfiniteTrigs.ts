import { useInfiniteQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedFetch } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

// Status ID to category code mapping
const STATUS_ID_TO_CATEGORY_CODE: Record<number, string> = {
  10: "PILLAR",
  20: "FBM",
  30: "SURVEY_MARK",
  40: "INTERSECTED",
  50: "ACTIVE",
  60: "OTHER",
};

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
  };
}

export interface UseInfiniteTrigsOptions {
  lat?: number;
  lon?: number;
  statusIds?: number[]; // Status IDs to filter by (10, 20, 30, etc.)
  types?: string[]; // Type codes to filter by (e.g., ['HOTINE', 'FBM'])
  showLogged?: boolean; // Show trigpoints logged by user (default: true)
  showNotLogged?: boolean; // Show trigpoints not logged by user (default: true)
  maxKm?: number;
  areaId?: number; // Filter to trigpoints within a specific area
  order?: string; // Sort order: distance | name | height | score (prefix with - for desc)
}

export function useInfiniteTrigs(options: UseInfiniteTrigsOptions = {}) {
  const { lat, lon, statusIds, types, showLogged = true, showNotLogged = true, maxKm, areaId, order } = options;
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  return useInfiniteQuery<TrigsResponse>({
    queryKey: ["trigs", "infinite", lat, lon, statusIds, types, showLogged, showNotLogged, maxKm, areaId, order],
    enabled: lat !== undefined && lon !== undefined, // Only fetch when location is set
    queryFn: async ({ pageParam }: { pageParam?: unknown }) => {
      const skip = typeof pageParam === "number" ? pageParam : 0;
      const params = new URLSearchParams();
      
      params.append("limit", "50");
      params.append("skip", skip.toString());
      
      if (lat !== undefined && lon !== undefined) {
        params.append("lat", lat.toString());
        params.append("lon", lon.toString());
      }
      
      // Set sort order - default to distance when coordinates available
      const effectiveOrder = order || (lat !== undefined && lon !== undefined ? "distance" : "name");
      params.append("order", effectiveOrder);
      
      if (maxKm !== undefined) {
        params.append("max_km", maxKm.toString());
      }
      
      if (statusIds && statusIds.length > 0) {
        // Convert status IDs to category codes for the API
        const categoryCodes = statusIds
          .map((id) => STATUS_ID_TO_CATEGORY_CODE[id])
          .filter((code): code is string => code !== undefined);
        if (categoryCodes.length > 0) {
          params.append("categories", categoryCodes.join(","));
        }
      }
      
      // Type filter
      if (types && types.length > 0) {
        params.append("types", types.join(","));
      }
      
      // Log filter: showLogged=false means exclude found, showNotLogged=false means only found
      if (!showLogged) {
        params.append("exclude_found", "true");
      }
      if (!showNotLogged) {
        params.append("only_found", "true");
      }
      
      // Area filter
      if (areaId !== undefined) {
        params.append("area_id", areaId.toString());
      }
      
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

