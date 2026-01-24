/**
 * Hook for fetching user log timeline data for animated map visualisation.
 *
 * Returns lightweight {lat, lon, date, colour} tuples sorted chronologically.
 */

import { useQuery } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_BASE as string;

/**
 * Single log entry in the timeline.
 */
export interface TimelineEntry {
  lat: number;
  lon: number;
  date: string | null;
  colour: "green" | "yellow" | "red" | "grey";
}

/**
 * Fetch user log timeline data.
 *
 * @param userId - User ID to fetch timeline for
 * @returns React Query result with timeline entries
 */
export function useUserLogTimeline(userId: number | string) {
  return useQuery<TimelineEntry[]>({
    queryKey: ["user", "log-timeline", userId],
    queryFn: async () => {
      const response = await fetch(
        `${API_BASE}/v1/users/${userId}/log-timeline`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch log timeline");
      }
      return response.json();
    },
    // Cache for 5 minutes client-side (server caches for 2 hours)
    staleTime: 5 * 60 * 1000,
    // Don't refetch on window focus for this data
    refetchOnWindowFocus: false,
  });
}

