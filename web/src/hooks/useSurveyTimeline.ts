/**
 * Hook for fetching survey timeline data for animated map visualisation.
 *
 * Returns {lat, lon, date, colour} tuples for triangulation and levelling dates,
 * sorted chronologically.
 */

import { useQuery } from "@tanstack/react-query";

const API_BASE = import.meta.env.VITE_API_BASE as string;

/**
 * Single entry in the survey timeline.
 */
export interface SurveyTimelineEntry {
  lat: number;
  lon: number;
  date: string | null;
  colour: "green" | "blue"; // green = triangulation, blue = levelling
}

/**
 * Fetch survey timeline data showing when trigpoints were triangulated and levelled.
 *
 * @returns React Query result with timeline entries
 */
export function useSurveyTimeline() {
  return useQuery<SurveyTimelineEntry[]>({
    queryKey: ["experiment", "survey-timeline"],
    queryFn: async () => {
      const response = await fetch(`${API_BASE}/v1/experiment/survey-timeline`);
      if (!response.ok) {
        throw new Error("Failed to fetch survey timeline");
      }
      return response.json();
    },
    // Cache for 1 hour client-side (data doesn't change)
    staleTime: 60 * 60 * 1000,
    // Don't refetch on window focus for this static data
    refetchOnWindowFocus: false,
  });
}

