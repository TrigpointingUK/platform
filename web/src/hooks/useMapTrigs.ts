import { useQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";

interface Trig {
  id: number;
  waypoint: string;
  name: string;
  physical_type: string;
  condition: string;
  wgs_lat: string;
  wgs_long: string;
  osgb_gridref: string;
  status_name?: string;
  distance_km?: number;
}

interface TrigsResponse {
  items: Trig[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

export interface UseMapTrigsOptions {
  bounds?: MapBounds;
  physicalTypes?: string[];
  excludeFound?: boolean;
  enabled?: boolean;
}

/**
 * Calculate center and radius from bounds
 */
function boundsToCenter(bounds: MapBounds): { lat: number; lon: number; maxKm: number } {
  const lat = (bounds.north + bounds.south) / 2;
  const lon = (bounds.east + bounds.west) / 2;
  
  // Calculate approximate radius in km
  // Haversine formula simplified for small distances
  const latDiff = bounds.north - bounds.south;
  const lonDiff = bounds.east - bounds.west;
  const degToKm = 111.32; // Approximate km per degree
  
  const latKm = latDiff * degToKm;
  const lonKm = lonDiff * degToKm * Math.cos((lat * Math.PI) / 180);
  
  // Use diagonal distance as radius
  const maxKm = Math.sqrt(latKm * latKm + lonKm * lonKm) / 2;
  
  return { lat, lon, maxKm };
}

/**
 * Hook to fetch trigpoints within map viewport bounds
 * 
 * Converts bounds to center+radius and queries the existing /v1/trigs endpoint.
 */
export function useMapTrigs({
  bounds,
  physicalTypes,
  excludeFound = false,
  enabled = true,
}: UseMapTrigsOptions) {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  
  return useQuery<TrigsResponse>({
    queryKey: ["map-trigs", bounds, physicalTypes, excludeFound],
    enabled: enabled && !!bounds,
    staleTime: 2 * 60 * 1000, // 2 minutes
    queryFn: async () => {
      if (!bounds) {
        throw new Error("Bounds are required");
      }
      
      const { lat, lon, maxKm } = boundsToCenter(bounds);
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const params = new URLSearchParams();
      
      // Request large limit to get all visible trigpoints
      params.append("limit", "100");
      params.append("skip", "0");
      
      params.append("lat", lat.toString());
      params.append("lon", lon.toString());
      params.append("max_km", maxKm.toString());
      params.append("order", "distance");
      
      if (physicalTypes && physicalTypes.length > 0) {
        params.append("physical_types", physicalTypes.join(","));
      }
      
      if (excludeFound) {
        params.append("exclude_found", "true");
      }
      
      // Get auth token if authenticated and exclude_found is enabled
      const headers: Record<string, string> = {};
      if (excludeFound && isAuthenticated) {
        try {
          const token = await getAccessTokenSilently({ cacheMode: "on" });
          headers["Authorization"] = `Bearer ${token}`;
        } catch (error) {
          console.error("Failed to get access token for map trigs:", error);
          // Continue without auth - backend will simply not filter
        }
      }
      
      const response = await fetch(`${apiBase}/v1/trigs?${params.toString()}`, {
        headers,
      });
      
      if (!response.ok) {
        throw new Error("Failed to fetch trigpoints for map");
      }
      
      return response.json();
    },
  });
}

/**
 * Hook to check if a user has logged specific trigpoints
 * Returns a map of trig_id -> log status
 */
export function useUserLogStatus(trigIds: number[]) {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  
  return useQuery({
    queryKey: ["user-log-status", trigIds],
    enabled: isAuthenticated && trigIds.length > 0,
    staleTime: 5 * 60 * 1000, // 5 minutes
    queryFn: async () => {
      if (!isAuthenticated || trigIds.length === 0) {
        return {};
      }
      
      const apiBase = import.meta.env.VITE_API_BASE as string;
      
      try {
        const token = await getAccessTokenSilently({ cacheMode: "on" });
        
        // Fetch user's profile which includes log stats
        const response = await fetch(`${apiBase}/v1/users/me?include=stats`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });
        
        if (!response.ok) {
          throw new Error("Failed to fetch user log status");
        }
        
        // For now, return empty object - this would need backend support
        // to efficiently check log status for multiple trigs
        // TODO: Implement batch log status check endpoint
        return {};
      } catch (error) {
        console.error("Failed to fetch user log status:", error);
        return {};
      }
    },
  });
}

