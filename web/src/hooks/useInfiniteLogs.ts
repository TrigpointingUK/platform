import { useInfiniteQuery } from "@tanstack/react-query";
import { Photo } from "../lib/api";

export interface Log {
  id: number;
  trig_id: number;
  user_id: number;
  trig_name?: string;
  user_name?: string;
  trig_lat?: number | null;
  trig_lon?: number | null;
  date: string;
  time: string;
  condition: string;
  comment: string;
  score: number;
  photos?: Photo[];
  distance_km?: number | null;
}

interface LogsResponse {
  items: Log[];
  total: number;
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
}

export interface UseInfiniteLogsOptions {
  lat?: number;
  lon?: number;
  maxKm?: number;
  statusIds?: number[];
  areaId?: number;
  showLogged?: boolean; // Show logs for trigpoints logged by user (default: true)
  showNotLogged?: boolean; // Show logs for trigpoints not logged by user (default: true)
}

export function useInfiniteLogs(options: UseInfiniteLogsOptions = {}) {
  const {
    lat,
    lon,
    maxKm,
    statusIds,
    areaId,
    showLogged = true,
    showNotLogged = true,
  } = options;

  // Check if any filters are active (for query key and enabled logic)
  const hasFilters =
    lat !== undefined ||
    lon !== undefined ||
    maxKm !== undefined ||
    (statusIds !== undefined && statusIds.length > 0) ||
    areaId !== undefined ||
    !showLogged ||
    !showNotLogged;

  return useInfiniteQuery<LogsResponse>({
    queryKey: [
      "logs",
      "infinite",
      lat,
      lon,
      maxKm,
      statusIds,
      areaId,
      showLogged,
      showNotLogged,
    ],
    queryFn: async ({ pageParam = 0 }) => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const params = new URLSearchParams();

      params.append("limit", "20");
      params.append("skip", String(pageParam));
      params.append("include", "photos");

      if (lat !== undefined) {
        params.append("lat", lat.toString());
      }
      if (lon !== undefined) {
        params.append("lon", lon.toString());
      }
      if (maxKm !== undefined) {
        params.append("max_km", maxKm.toString());
      }
      if (statusIds && statusIds.length > 0) {
        params.append("status_ids", statusIds.join(","));
      }
      if (areaId !== undefined) {
        params.append("area_id", areaId.toString());
      }
      // Log filter: showLogged=false means exclude found, showNotLogged=false means only found
      if (!showLogged) {
        params.append("exclude_found", "true");
      }
      if (!showNotLogged) {
        params.append("only_found", "true");
      }

      const response = await fetch(`${apiBase}/v1/logs?${params.toString()}`);
      if (!response.ok) {
        throw new Error("Failed to fetch logs");
      }
      return response.json();
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      return lastPage.pagination.has_more
        ? lastPage.pagination.offset + lastPage.pagination.limit
        : null;
    },
    staleTime: hasFilters ? 10 * 60 * 1000 : 5 * 60 * 1000, // 10 min with filters, 5 min without
  });
}
