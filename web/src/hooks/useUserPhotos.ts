import { useInfiniteQuery } from "@tanstack/react-query";
import { Photo } from "../lib/api";

interface PhotosResponse {
  items: Photo[];
  total: number;
  pagination: {
    has_more: boolean;
    next_offset: number | null;
  };
}

export function useUserPhotos(userId: string) {
  const LIMIT = 24;

  return useInfiniteQuery<PhotosResponse>({
    queryKey: ["user", userId, "photos"],
    queryFn: async ({ pageParam = 0 }) => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/users/${userId}/photos?skip=${pageParam}&limit=${LIMIT}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch user photos");
      }
      const data = await response.json();

      return {
        items: data.items || [],
        total: data.pagination?.total || 0,
        pagination: {
          has_more: data.pagination?.has_more || false,
          next_offset: data.pagination?.has_more
            ? (pageParam as number) + LIMIT
            : null,
        },
      };
    },
    initialPageParam: 0,
    getNextPageParam: (lastPage) => lastPage.pagination.next_offset,
  });
}

