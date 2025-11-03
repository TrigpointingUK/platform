import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";

interface LocationSearchResult {
  type: string;
  name: string;
  lat: number;
  lon: number;
  description?: string;
}

export function useLocationSearch(query: string, enabled: boolean = true) {
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  // Debounce the query
  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);

    return () => clearTimeout(timer);
  }, [query]);

  return useQuery<LocationSearchResult[]>({
    queryKey: ["locationSearch", debouncedQuery],
    queryFn: async () => {
      if (!debouncedQuery || debouncedQuery.length < 2) {
        return [];
      }
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/locations/search?q=${encodeURIComponent(debouncedQuery)}&limit=10`
      );
      if (!response.ok) {
        throw new Error("Failed to search locations");
      }
      return response.json();
    },
    enabled: enabled && debouncedQuery.length >= 2,
    staleTime: 60 * 60 * 1000, // 1 hour
  });
}

