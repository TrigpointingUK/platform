import { useQuery } from "@tanstack/react-query";

export interface AreaType {
  id: number;
  code: string;
  name: string;
  description: string | null;
}

export function useAreaTypes() {
  return useQuery<AreaType[]>({
    queryKey: ["areaTypes"],
    queryFn: async () => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(`${apiBase}/v1/areas/types`);
      if (!response.ok) {
        throw new Error("Failed to fetch area types");
      }
      return response.json();
    },
    staleTime: 24 * 60 * 60 * 1000, // 24 hours - area types don't change often
  });
}

