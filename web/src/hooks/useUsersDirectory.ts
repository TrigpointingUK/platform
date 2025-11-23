import { useInfiniteQuery } from "@tanstack/react-query";

export type UserSortOption = "trigs" | "photos" | "logs" | "joined" | "name";
export type UserSortDirection = "asc" | "desc";

export interface UserDirectoryItem {
  id: number;
  name: string;
  member_since?: string | null;
  stats: {
    total_logs: number;
    total_trigs_logged: number;
    total_photos: number;
  };
  profile_path: string;
}

export interface UserDirectoryResponse {
  items: UserDirectoryItem[];
  next_cursor: string | null;
  total: number;
  applied_filters: {
    query?: string | null;
    sort: UserSortOption;
    direction: UserSortDirection;
    limit: number;
  };
}

export interface UseUsersDirectoryOptions {
  query?: string;
  sort?: UserSortOption;
  direction?: UserSortDirection;
}

export const USERS_SORT_OPTIONS: { label: string; value: UserSortOption }[] = [
  { label: "Trigpoints logged", value: "trigs" },
  { label: "Photos uploaded", value: "photos" },
  { label: "Logs recorded", value: "logs" },
  { label: "Joined date", value: "joined" },
  { label: "Alphabetical", value: "name" },
];

const PAGE_SIZE = 40;

export function useUsersDirectory(
  options: UseUsersDirectoryOptions = {}
): ReturnType<typeof useInfiniteQuery<UserDirectoryResponse>> {
  const sort = options.sort ?? "trigs";
  const direction = options.direction ?? "desc";
  const queryKey = ["users", "browse", options.query, sort, direction];

  return useInfiniteQuery<UserDirectoryResponse>({
    queryKey,
    initialPageParam: null,
    queryFn: async ({ pageParam }) => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const params = new URLSearchParams();
      params.set("limit", PAGE_SIZE.toString());
      params.set("sort", sort);
      params.set("direction", direction);

      const trimmedQuery = options.query?.trim();
      if (trimmedQuery) {
        params.set("q", trimmedQuery);
      }

      if (typeof pageParam === "string" && pageParam.length > 0) {
        params.set("cursor", pageParam);
      }

      const response = await fetch(
        `${apiBase}/v1/users/browse?${params.toString()}`,
        {
          method: "GET",
        }
      );

      if (!response.ok) {
        throw new Error("Failed to load users directory");
      }

      return (await response.json()) as UserDirectoryResponse;
    },
    getNextPageParam: (lastPage) => lastPage.next_cursor,
  });
}


