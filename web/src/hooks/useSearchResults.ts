import { useQuery, useInfiniteQuery } from "@tanstack/react-query";

// Types matching backend schemas
export interface LocationSearchResult {
  type: string;
  name: string;
  lat: number;
  lon: number;
  description?: string;
  id?: string;
}

export interface LogSearchResult {
  id: number;
  trig_id: number;
  trig_name?: string;
  user_id: number;
  user_name?: string;
  date: string;
  time: string;
  condition: string;
  comment: string;
  score: number;
  comment_excerpt?: string;
}

export interface SearchCategoryResults<T> {
  total: number;
  items: T[];
  has_more: boolean;
  query: string;
}

export interface UnifiedSearchResults {
  query: string;
  trigpoints: SearchCategoryResults<LocationSearchResult>;
  places: SearchCategoryResults<LocationSearchResult>;
  users: SearchCategoryResults<LocationSearchResult>;
  postcodes: SearchCategoryResults<LocationSearchResult>;
  coordinates: SearchCategoryResults<LocationSearchResult>;
  log_substring: SearchCategoryResults<LogSearchResult>;
  log_regex: SearchCategoryResults<LogSearchResult>;
}

const API_BASE = import.meta.env.VITE_API_BASE as string;

/**
 * Hook for fetching unified search results across all categories
 */
export function useUnifiedSearch(query: string) {
  return useQuery<UnifiedSearchResults>({
    queryKey: ["search", "unified", query],
    queryFn: async () => {
      if (!query || query.length < 2) {
        throw new Error("Query must be at least 2 characters");
      }
      const response = await fetch(
        `${API_BASE}/v1/locations/search/all?q=${encodeURIComponent(query)}&limit=20`
      );
      if (!response.ok) {
        throw new Error("Failed to search");
      }
      return response.json();
    },
    enabled: query.length >= 2,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

/**
 * Hook for infinite scroll search in a specific category
 */
export function useCategorySearch<T>(
  category: "trigpoints" | "places" | "users" | "postcodes" | "logs/substring" | "logs/regex",
  query: string,
  enabled: boolean = true
) {
  return useInfiniteQuery<SearchCategoryResults<T>>({
    queryKey: ["search", category, query],
    queryFn: async ({ pageParam = 0 }) => {
      const skip = pageParam as number;
      const response = await fetch(
        `${API_BASE}/v1/locations/search/${category}?q=${encodeURIComponent(
          query
        )}&skip=${skip}&limit=20`
      );
      if (!response.ok) {
        throw new Error(`Failed to search ${category}`);
      }
      return response.json();
    },
    getNextPageParam: (lastPage, pages) => {
      const loadedCount = pages.reduce((sum, page) => sum + page.items.length, 0);
      return lastPage.has_more ? loadedCount : undefined;
    },
    enabled: enabled && query.length >= 2,
    staleTime: 5 * 60 * 1000, // 5 minutes
    initialPageParam: 0,
  });
}

