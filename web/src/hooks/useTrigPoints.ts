import { useQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedFetch } from "../lib/api";
import {
  buildTrigFilterParams,
  selectsNothing,
  type TrigFilterOptions,
} from "../lib/trigFilterParams";
import type { TrigData } from "../components/map/types";

const API_BASE = import.meta.env.VITE_API_BASE as string;

interface TrigPointsResponse {
  fields: string[];
  rows: unknown[][];
  total: number;
  truncated: boolean;
}

export interface TrigPoints {
  trigs: TrigData[];
  truncated: boolean;
}

/** Turn the compact `{fields, rows}` table from /trigs/points into TrigData objects. */
export function parseTrigPoints(body: TrigPointsResponse): TrigPoints {
  const index = Object.fromEntries(body.fields.map((field, i) => [field, i]));
  const trigs = body.rows.map((row) => ({
    id: row[index.id] as number,
    waypoint: row[index.waypoint] as string,
    name: row[index.name] as string,
    wgs_lat: row[index.lat] as number,
    wgs_long: row[index.lon] as number,
    condition: row[index.condition] as string,
    osgb_gridref: row[index.osgb_gridref] as string,
    type_name: (row[index.type_name] as string | null) ?? undefined,
    category_code: (row[index.category_code] as string | null) ?? undefined,
  }));
  return { trigs, truncated: body.truncated };
}

/**
 * Every trig matching the filters (not just the loaded list pages), for
 * plotting on a map. Only fetches while `enabled` - i.e. the map is showing.
 */
export function useTrigPoints(filters: TrigFilterOptions, enabled: boolean) {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  return useQuery<TrigPoints>({
    queryKey: ["trigs", "points", filters],
    enabled,
    queryFn: async () => {
      if (selectsNothing(filters)) {
        return { trigs: [], truncated: false };
      }
      const url = `${API_BASE}/v1/trigs/points?${buildTrigFilterParams(filters).toString()}`;
      const response = isAuthenticated
        ? await authenticatedFetch(url, {}, getAccessTokenSilently)
        : await fetch(url);
      if (!response.ok) {
        throw new Error("Failed to fetch trigpoints for the map");
      }
      return parseTrigPoints(await response.json());
    },
    staleTime: 10 * 60 * 1000, // 10 minutes
  });
}
