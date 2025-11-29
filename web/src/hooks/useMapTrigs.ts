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
  statusIds?: number[]; // Status IDs to filter by (10, 20, 30, etc.)
  excludeFound?: boolean;
  enabled?: boolean;
  zoom?: number; // Current zoom level
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
  statusIds,
  excludeFound = false,
  enabled = true,
  zoom = 7,
}: UseMapTrigsOptions) {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  
  return useQuery<TrigsResponse>({
    // Different query keys for different modes
    // When zoomed out, only invalidate on filter changes, not viewport
    // When zoomed in, include bounds in key
    queryKey: zoom < 9 
      ? ["map-trigs-all", statusIds, excludeFound] 
      : ["map-trigs-viewport", bounds, statusIds, excludeFound],
    enabled: enabled && !!bounds,
    // For zoomed out (all trigpoints), cache for 1 hour
    // For zoomed in (viewport), cache for 2 minutes
    staleTime: zoom < 9 ? 60 * 60 * 1000 : 2 * 60 * 1000,
    gcTime: zoom < 9 ? 2 * 60 * 60 * 1000 : 5 * 60 * 1000, // Keep in cache longer
    queryFn: async () => {
      if (!bounds) {
        throw new Error("Bounds are required");
      }
      
      const { lat, lon, maxKm } = boundsToCenter(bounds);
      const apiBase = import.meta.env.VITE_API_BASE as string;
      
      // For zoomed out views (zoom < 9), get ALL trigpoints for proper heatmap
      // For zoomed in views, get trigpoints within viewport
      const isZoomedOut = zoom < 9;
      
      // Get auth token if authenticated (needed for status_max and exclude_found)
      const headers: Record<string, string> = {};
      if (isAuthenticated) {
        try {
          const token = await getAccessTokenSilently({ cacheMode: "on" });
          headers["Authorization"] = `Bearer ${token}`;
        } catch (error) {
          console.error("Failed to get access token for map trigs:", error);
          // Continue without auth - backend will use default status_max
        }
      }
      
      if (isZoomedOut) {
        // Fetch ALL trigpoints for heatmap using parallel batch requests
        // Note: status filter is NOT applied - we filter client-side
        const batchSize = 3000; // Larger batches for fewer requests
        const numBatches = 4; // Parallel requests
        
        // Create parallel fetch promises
        const fetchPromises = Array.from({ length: numBatches }, (_, i) => {
          const skip = i * batchSize;
          const params = new URLSearchParams();
          params.append("limit", batchSize.toString());
          params.append("skip", skip.toString());
          
          // Apply filters (backend auto-applies status_max for authenticated users)
          if (excludeFound) {
            params.append("exclude_found", "true");
          }
          
          if (statusIds && statusIds.length > 0) {
            params.append("status_ids", statusIds.join(","));
          }
          
          return fetch(`${apiBase}/v1/trigs?${params.toString()}`, { headers })
            .then(res => {
              if (!res.ok) throw new Error("Failed to fetch batch");
              return res.json() as Promise<TrigsResponse>;
            });
        });
        
        // Wait for all batches to complete
        const results = await Promise.all(fetchPromises);
        
        // Combine all results
        const allTrigpoints: Trig[] = [];
        let totalCount = 0;
        
        for (const data of results) {
          allTrigpoints.push(...data.items);
          if (data.pagination.total > totalCount) {
            totalCount = data.pagination.total;
          }
        }
        
        // Return combined response
        return {
          items: allTrigpoints,
          pagination: {
            total: totalCount,
            limit: allTrigpoints.length,
            offset: 0,
            has_more: false,
          },
          links: {
            self: '',
            next: null,
            prev: null,
          },
        };
      } else {
        // Get trigpoints within viewport for marker display
        // Use parallel batches for faster loading
        const batchSize = 500;
        const numBatches = 2; // Fetch up to 1000 markers
        
        // Note: status filter is applied on backend (auto status_max for authenticated users)
        const fetchPromises = Array.from({ length: numBatches }, (_, i) => {
          const skip = i * batchSize;
          const params = new URLSearchParams();
          params.append("limit", batchSize.toString());
          params.append("skip", skip.toString());
          params.append("lat", lat.toString());
          params.append("lon", lon.toString());
          params.append("max_km", maxKm.toString());
          params.append("order", "distance");
          
          // Apply filters
          if (excludeFound) {
            params.append("exclude_found", "true");
          }
          
          if (statusIds && statusIds.length > 0) {
            params.append("status_ids", statusIds.join(","));
          }
          
          return fetch(`${apiBase}/v1/trigs?${params.toString()}`, { headers })
            .then(res => {
              if (!res.ok) throw new Error("Failed to fetch batch");
              return res.json() as Promise<TrigsResponse>;
            })
            .catch(() => null); // Gracefully handle partial failures
        });
        
        // Wait for all batches
        const results = await Promise.all(fetchPromises);
        
        // Combine results
        const allTrigpoints: Trig[] = [];
        let totalCount = 0;
        
        for (const data of results) {
          if (data) {
            allTrigpoints.push(...data.items);
            if (data.pagination.total > totalCount) {
              totalCount = data.pagination.total;
            }
          }
        }
        
        // Return combined response
        return {
          items: allTrigpoints,
          pagination: {
            total: totalCount,
            limit: allTrigpoints.length,
            offset: 0,
            has_more: false,
          },
          links: {
            self: '',
            next: null,
            prev: null,
          },
        };
      }
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

