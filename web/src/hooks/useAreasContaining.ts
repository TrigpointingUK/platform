import { useQuery } from "@tanstack/react-query";

interface AreaType {
  id: number;
  code: string;
  name: string;
}

interface Area {
  id: number;
  name: string;
  code: string | null;
  area_type: AreaType;
}

interface AreaGroup {
  area_type: AreaType;
  areas: Area[];
}

interface AreasContainingResponse {
  lat: number;
  lon: number;
  groups: AreaGroup[];
  total_areas: number;
}

export type { Area, AreaType, AreaGroup, AreasContainingResponse };

export function useAreasContaining(lat?: number, lon?: number) {
  return useQuery<AreasContainingResponse>({
    queryKey: ["areasContaining", lat, lon],
    queryFn: async () => {
      if (lat === undefined || lon === undefined) {
        return { lat: 0, lon: 0, groups: [], total_areas: 0 };
      }
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(
        `${apiBase}/v1/areas/containing?lat=${lat}&lon=${lon}`
      );
      if (!response.ok) {
        throw new Error("Failed to fetch areas");
      }
      return response.json();
    },
    enabled: lat !== undefined && lon !== undefined,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - areas don't change often
  });
}
