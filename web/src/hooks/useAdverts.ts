import { useQuery } from "@tanstack/react-query";
import * as yaml from "js-yaml";

export interface AdvertItem {
  id: number;
  title?: string | null;
  text?: string | null;
  photo?: string | null;
  link?: string | null;
  startDate?: string | null;
  endDate?: string | null;
}

/**
 * Filters adverts based on current date and their startDate/endDate
 * - No dates = always show
 * - Only startDate = show from that date onwards
 * - Only endDate = show until that date
 * - Both dates = show only within the range (inclusive)
 */
function filterActiveAdverts(adverts: AdvertItem[]): AdvertItem[] {
  const now = new Date();
  now.setHours(0, 0, 0, 0); // Normalize to start of day for comparison

  return adverts.filter((advert) => {
    const { startDate, endDate } = advert;

    // No dates = always show
    if (!startDate && !endDate) {
      return true;
    }

    const start = startDate ? new Date(startDate) : null;
    const end = endDate ? new Date(endDate) : null;

    // Normalize dates to start of day
    if (start) start.setHours(0, 0, 0, 0);
    if (end) end.setHours(0, 0, 0, 0);

    // Only startDate = show from that date onwards
    if (start && !end) {
      return now >= start;
    }

    // Only endDate = show until that date
    if (!start && end) {
      return now <= end;
    }

    // Both dates = show only within the range (inclusive)
    if (start && end) {
      return now >= start && now <= end;
    }

    return false;
  });
}

export function useAdverts() {
  return useQuery<AdvertItem[]>({
    queryKey: ["adverts"],
    queryFn: async () => {
      const response = await fetch("/adverts.yaml");
      if (!response.ok) {
        throw new Error("Failed to fetch adverts");
      }
      const text = await response.text();
      const data = yaml.load(text) as AdvertItem[];
      return filterActiveAdverts(data);
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}

