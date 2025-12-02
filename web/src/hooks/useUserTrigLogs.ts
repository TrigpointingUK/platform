import { useQuery } from "@tanstack/react-query";
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
  };
}

/**
 * Fetches all logs for a specific trig by a specific user.
 * Used to show "Your Visits" section on trig detail page.
 */
export function useUserTrigLogs(trigId: number, userId: number | undefined) {
  return useQuery<Log[]>({
    queryKey: ["logs", "trig", trigId, "user", userId],
    queryFn: async () => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      // Fetch with a high limit - users rarely have more than a handful of logs per trig
      const response = await fetch(
        `${apiBase}/v1/logs?trig_id=${trigId}&user_id=${userId}&include=photos&limit=100`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch user's logs for this trig");
      }
      const data: LogsResponse = await response.json();
      return data.items || [];
    },
    enabled: !!userId && !!trigId,
    staleTime: 2 * 60 * 1000, // 2 minutes
  });
}
