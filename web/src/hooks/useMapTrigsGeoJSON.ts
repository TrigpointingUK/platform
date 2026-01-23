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
    type_code?: string; // From trig_type.code
    type_name?: string; // From trig_type.name
    category_code?: string; // From trig_category.code
    category_name?: string; // From trig_category.name
  };
}

export interface GeoJSONFeatureCollection {
  type: "FeatureCollection";
  name?: string; // trig_category.name for display
  description?: string; // trig_category.description
  features: GeoJSONTrig[];
}

// Warning object for unmapped trigpoints
export interface GeoJSONWarning {
  message: string;
  reason: string;
  unmapped_count: number;
  unmapped_categories: Record<string, number>;
  sample_trigs: Array<{
    id: number;
    name: string;
    category_code: string;
    category_name: string;
  }>;
}

// Category-based structure (keyed by trig_category.code)
export interface GeoJSONResponse {
  PILLAR?: GeoJSONFeatureCollection;
  FBM?: GeoJSONFeatureCollection;
  SURVEY_MARK?: GeoJSONFeatureCollection;
  INTERSECTED?: GeoJSONFeatureCollection;
  ACTIVE?: GeoJSONFeatureCollection;
  OTHER?: GeoJSONFeatureCollection;
  _warning?: GeoJSONWarning;
  generated_at: string;
  [key: string]: GeoJSONFeatureCollection | GeoJSONWarning | string | undefined;
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

