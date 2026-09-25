import { useQueries, useQuery } from "@tanstack/react-query";

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

const BOUNDARY_STALE_TIME = 24 * 60 * 60 * 1000; // 24 hours - area boundaries don't change

async function fetchAreaBoundary(areaId: number): Promise<AreaBoundaryResponse> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  const response = await fetch(`${apiBase}/v1/areas/${areaId}/boundary`);
  if (!response.ok) {
    throw new Error("Failed to fetch area boundary");
  }
  return response.json();
}

export function useAreaBoundary(areaId?: number) {
  return useQuery<AreaBoundaryResponse>({
    queryKey: ["areaBoundary", areaId],
    queryFn: () => {
      if (areaId === undefined) {
        throw new Error("Area ID is required");
      }
      return fetchAreaBoundary(areaId);
    },
    enabled: areaId !== undefined,
    staleTime: BOUNDARY_STALE_TIME,
  });
}

/**
 * Boundaries for several areas, one request (and cache entry) per area, so
 * adding or removing an area doesn't refetch the others. Returns those that
 * have loaded so far; any that fail are left out.
 */
export function useAreaBoundaries(areaIds: number[]): AreaBoundaryResponse[] {
  return useQueries({
    queries: areaIds.map((id) => ({
      queryKey: ["areaBoundary", id],
      queryFn: () => fetchAreaBoundary(id),
      staleTime: BOUNDARY_STALE_TIME,
    })),
    combine: (results) =>
      results
        .map((r) => r.data)
        .filter((area): area is AreaBoundaryResponse => !!area),
  });
}
