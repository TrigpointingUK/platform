import { useInfiniteQuery } from "@tanstack/react-query";
import { Photo } from "../lib/api";

interface PhotosResponse {
  items: Photo[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

export function useTrigPhotos(trigId: number) {
  const LIMIT = 24;

  return useInfiniteQuery<PhotosResponse>({
    queryKey: ["trig", trigId, "photos"],
    queryFn: async ({ pageParam = 0 }) => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/trigs/${trigId}/photos?skip=${pageParam}&limit=${LIMIT}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch trig photos");
      }
      const data = await response.json();

      return {
        items: data.items || [],
        pagination: {
          total: data.pagination?.total || 0,
          limit: data.pagination?.limit || LIMIT,
          offset: data.pagination?.offset || 0,
          has_more: data.pagination?.has_more || false,
        },
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => {
      if (lastPage.pagination.has_more) {
        return lastPage.pagination.offset + lastPage.pagination.limit;
      }
      return undefined;
    },
    enabled: !!trigId,
  });
}

