import { useState, useEffect } from "react";

export interface GeoJSONTrig {
  type: "Feature";
  geometry: {
    type: "Point";
    coordinates: [number, number]; // [lon, lat]
  };
  properties: {
    id: number;
    name: string;
    condition: string;
    osgb_gridref: string;
  };
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  features: GeoJSONTrig[];
}

export interface GeoJSONResponse {
  fbm: GeoJSONFeatureCollection;
  pillar: GeoJSONFeatureCollection;
  generated_at: string;
  cache_info: string;
}

export interface UseMapTrigsGeoJSONOptions {
  enabled?: boolean;
  limit?: number | null; // null means no limit (maximum)
}

export function useMapTrigsGeoJSON({
  enabled = true,
  limit = null,
}: UseMapTrigsGeoJSONOptions) {
  const [data, setData] = useState<GeoJSONResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const fetchData = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const apiBase = import.meta.env.VITE_API_BASE as string;
        const params = new URLSearchParams();

        if (limit !== null) {
          params.append("limit", limit.toString());
        }

        const url = `${apiBase}/v1/trigs/geojson${params.toString() ? "?" + params.toString() : ""}`;
        const res = await fetch(url);

        if (!res.ok) {
          throw new Error(`HTTP ${res.status}: ${res.statusText}`);
        }

        const jsonData = await res.json();
        setData(jsonData);
      } catch (err) {
        setError(err as Error);
      } finally {
        setIsLoading(false);
      }
    };

    fetchData();
  }, [enabled, limit]);

  return {
    data,
    isLoading,
    error,
  };
}

