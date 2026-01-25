import { useQuery } from "@tanstack/react-query";

interface SiteStats {
  total_trigs: number;
  total_members: number;
  total_logs: number;
  total_photos: number;
  recent_logs_7d: number;
  recent_users_30d: number;
}

export function useSiteStats() {
  return useQuery<SiteStats>({
    queryKey: ["siteStats"],
    queryFn: async () => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(`${apiBase}/v1/stats/site`);
      if (!response.ok) {
        throw new Error("Failed to fetch site stats");
      }
      return response.json();
    },
    staleTime: 60 * 60 * 1000, // 1 hour - matches backend cache
    gcTime: 90 * 60 * 1000, // 90 minutes
  });
}

