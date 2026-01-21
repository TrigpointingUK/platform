import { useQuery } from "@tanstack/react-query";

export interface AreaType {
  id: number;
  code: string;
  name: string;
  description: string | null;
}

export interface AreaCountItem {
  area_name: string;
  count: number;
}

export interface UserAreaBreakdownResponse {
  area_type: AreaType;
  items: AreaCountItem[];
}

export function useUserAreaBreakdown(
  userId: number | string | undefined,
  areaTypeCode: string = "county_1991"
) {
  return useQuery<UserAreaBreakdownResponse>({
    queryKey: ["userAreaBreakdown", userId, areaTypeCode],
    queryFn: async () => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/users/${userId}/area-breakdown?area_type_code=${encodeURIComponent(areaTypeCode)}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch user area breakdown");
      }
      return response.json();
    },
    enabled: userId !== undefined && userId !== null,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - area data doesn't change often
  });
}

