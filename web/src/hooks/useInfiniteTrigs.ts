import { useInfiniteQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";

interface Trig {
  id: number;
  waypoint: string;
  name: string;
  physical_type: string;
  condition: string;
  wgs_lat: string;
  wgs_long: string;
  osgb_gridref: string;
  status_name?: string;
  distance_km?: number;
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
  physicalTypes?: string[];
  excludeFound?: boolean;
  maxKm?: number;
}

export function useInfiniteTrigs(options: UseInfiniteTrigsOptions = {}) {
  const { lat, lon, physicalTypes, excludeFound, maxKm } = options;
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  return useInfiniteQuery<TrigsResponse>({
    queryKey: ["trigs", "infinite", lat, lon, physicalTypes, excludeFound, maxKm],
    enabled: lat !== undefined && lon !== undefined, // Only fetch when location is set
    queryFn: async ({ pageParam }: { pageParam?: unknown }) => {
      const skip = typeof pageParam === "number" ? pageParam : 0;
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const params = new URLSearchParams();
      
      params.append("limit", "50");
      params.append("skip", skip.toString());
      
      if (lat !== undefined && lon !== undefined) {
        params.append("lat", lat.toString());
        params.append("lon", lon.toString());
        params.append("order", "distance");
      }
      
      if (maxKm !== undefined) {
        params.append("max_km", maxKm.toString());
      }
      
      if (physicalTypes && physicalTypes.length > 0) {
        params.append("physical_types", physicalTypes.join(","));
      }
      
      if (excludeFound) {
        params.append("exclude_found", "true");
      }
      
      // Get auth token if authenticated and exclude_found is enabled
      const headers: Record<string, string> = {};
      if (excludeFound && isAuthenticated) {
        try {
          const token = await getAccessTokenSilently({ cacheMode: "on" });
          headers["Authorization"] = `Bearer ${token}`;
        } catch (error) {
          console.error("Failed to get access token for trigs query:", error);
          // Continue without auth - backend will simply not filter
        }
      }
      
      const response = await fetch(`${apiBase}/v1/trigs?${params.toString()}`, {
        headers,
      });
      
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

