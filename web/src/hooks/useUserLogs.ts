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
    has_more: boolean;
    next_offset: number | null;
  };
}

export interface UseUserLogsOptions {
  fromDate?: Date;
  toDate?: Date;
}

export function useUserLogs(userId: string, options: UseUserLogsOptions = {}) {
  const LIMIT = 20;
  const { fromDate, toDate } = options;

  return useInfiniteQuery<LogsResponse>({
    queryKey: ["user", userId, "logs", fromDate?.toISOString(), toDate?.toISOString()],
    queryFn: async ({ pageParam = 0 }) => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const params = new URLSearchParams();
      params.append("include", "photos");
      params.append("skip", String(pageParam));
      params.append("limit", String(LIMIT));

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

