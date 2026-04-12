import { useQuery } from "@tanstack/react-query";
import { useState, useEffect } from "react";

export interface UserSearchResult {
  id: number;
  name: string;
  stats: {
    total_logs: number;
    total_trigs_logged: number;
    total_photos: number;
  };
}

interface UserSearchResponse {
  items: UserSearchResult[];
  total: number;
}

export function useUserSearch(query: string, enabled: boolean = true) {
  const [debouncedQuery, setDebouncedQuery] = useState(query);

  useEffect(() => {
    const timer = setTimeout(() => {
      setDebouncedQuery(query);
    }, 300);
    return () => clearTimeout(timer);
  }, [query]);

  return useQuery<UserSearchResult[]>({
    queryKey: ["userSearch", debouncedQuery],
    queryFn: async () => {
      if (!debouncedQuery || debouncedQuery.length < 2) {
        return [];
      }
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/users/browse?q=${encodeURIComponent(debouncedQuery)}&limit=10&sort=trigs&direction=desc`,
      );
      if (!response.ok) {
        throw new Error("Failed to search users");
      }
      const data: UserSearchResponse = await response.json();
      return data.items;
    },
    enabled: enabled && debouncedQuery.length >= 2,
    staleTime: 60 * 60 * 1000,
  });
}
