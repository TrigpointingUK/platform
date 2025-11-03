import { useInfiniteQuery } from "@tanstack/react-query";
import { Photo } from "../lib/api";

interface Log {
  id: number;
  trig_id: number;
  user_id: number;
  trig_name?: string;
  user_name?: string;
  date: string;
  time: string;
  condition: string;
  comment: string;
  score: number;
  photos?: Photo[];
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

export function useInfiniteLogs() {
  return useInfiniteQuery<LogsResponse>({
    queryKey: ["logs", "infinite"],
    queryFn: async ({ pageParam = 0 }) => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        // `${apiBase}/v1/logs?limit=20&skip=${pageParam}&order=-upd_timestamp&include=photos`
        `${apiBase}/v1/logs?limit=20&skip=${pageParam}&include=photos`
      );
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
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

