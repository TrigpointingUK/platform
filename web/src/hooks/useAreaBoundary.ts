import { useQuery } from "@tanstack/react-query";

interface AreaType {
  id: number;
  code: string;
  name: string;
}

interface GeoJSONGeometry {
  type: "Polygon" | "MultiPolygon";
  coordinates: number[][][] | number[][][][];
}

interface AreaBoundaryResponse {
  id: number;
  name: string;
  code: string | null;
  area_type: AreaType;
  boundary: GeoJSONGeometry;
}

export type { AreaType, GeoJSONGeometry, AreaBoundaryResponse };

export function useAreaBoundary(areaId?: number) {
  return useQuery<AreaBoundaryResponse>({
    queryKey: ["areaBoundary", areaId],
    queryFn: async () => {
      if (areaId === undefined) {
        throw new Error("Area ID is required");
      }
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(`${apiBase}/v1/areas/${areaId}/boundary`);
      if (!response.ok) {
        throw new Error("Failed to fetch area boundary");
      }
      return response.json();
    },
    enabled: areaId !== undefined,
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - area boundaries don't change
  });
}
