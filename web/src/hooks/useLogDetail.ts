import { useQuery } from "@tanstack/react-query";
import { Log } from "../lib/api";

export function useLogDetail(logId: number) {
  return useQuery<Log>({
    queryKey: ["log", logId],
    queryFn: async () => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/logs/${logId}?include=photos`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch log details");
      }
      return response.json();
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

