import { useQuery } from "@tanstack/react-query";
import { Trig } from "../lib/api";

export function useTrigDetail(trigId: number | undefined) {
  return useQuery<Trig>({
    queryKey: ["trig", trigId, "details"],
    queryFn: async () => {
      if (!trigId) {
        throw new Error("Trig ID is required");
      }
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/trigs/${trigId}?include=details,stats,attrs`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch trig details");
      }
      return response.json();
    },
    enabled: !!trigId, // Only run query if trigId is defined
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

