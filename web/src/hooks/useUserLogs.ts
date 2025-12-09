import { useInfiniteQuery } from "@tanstack/react-query";
import { Photo } from "../lib/api";

export interface UserLog {
  id: number;
  trig_id: number;
  user_id: number;
  trig_name?: string;
  user_name?: string;
  trig_lat?: number | null;
  trig_lon?: number | null;
  trig_condition?: string | null;
  date: string;
  time: string;
  condition: string;
  comment: string;
  score: number;
  photos?: Photo[];
  distance_km?: number | null;
}

interface LogsResponse {
  items: UserLog[];
  total: number;
  pagination: {
    has_more: boolean;
    next_offset: number | null;
  };
}

export interface UseUserLogsOptions {
  lat?: number;
  lon?: number;
  maxKm?: number;
  statusIds?: number[];
  areaId?: number;
  fromDate?: Date;
  toDate?: Date;
}

export function useUserLogs(userId: string, options: UseUserLogsOptions = {}) {
  const LIMIT = 20;
  const { lat, lon, maxKm, statusIds, areaId, fromDate, toDate } = options;

  return useInfiniteQuery<LogsResponse>({
    queryKey: [
      "user",
      userId,
      "logs",
      lat,
      lon,
      maxKm,
      statusIds,
      areaId,
      fromDate?.toISOString(),
      toDate?.toISOString(),
    ],
    queryFn: async ({ pageParam = 0 }) => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const params = new URLSearchParams();
      params.append("include", "photos");
      params.append("skip", String(pageParam));
      params.append("limit", String(LIMIT));

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
      if (fromDate !== undefined) {
        params.append("from_date", fromDate.toISOString().split("T")[0]);
      }
      if (toDate !== undefined) {
        params.append("to_date", toDate.toISOString().split("T")[0]);
      }

      const response = await fetch(
        `${apiBase}/v1/users/${userId}/logs?${params.toString()}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch user logs");
      }
      const data = await response.json();

      return {
        items: data.items || [],
        total: data.pagination?.total || 0,
        pagination: {
          has_more: data.pagination?.has_more || false,
          next_offset: data.pagination?.has_more
            ? (pageParam as number) + LIMIT
            : null,
        },
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.pagination.next_offset,
  });
}

