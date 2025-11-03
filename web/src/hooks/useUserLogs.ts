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

export function useUserLogs(userId: string) {
  const LIMIT = 20;

  return useInfiniteQuery<LogsResponse>({
    queryKey: ["user", userId, "logs"],
    queryFn: async ({ pageParam = 0 }) => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/users/${userId}/logs?include=photos&skip=${pageParam}&limit=${LIMIT}`
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

