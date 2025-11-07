import { useState, useEffect } from "react";
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

export interface UseMapTrigsWithProgressOptions {
  bounds?: MapBounds;
  excludeFound?: boolean;
  enabled?: boolean;
  zoom?: number;
}

/**
 * Hook to fetch trigpoints with progress tracking
 * 
 * Uses parallel batch loading for better performance.
 */
export function useMapTrigsWithProgress({
  bounds,
  excludeFound = false,
  enabled = true,
  zoom = 7,
}: UseMapTrigsWithProgressOptions) {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  const [data, setData] = useState<Trig[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);
  
  useEffect(() => {
    if (!enabled || !bounds) {
      return;
    }
    
    const isZoomedOut = zoom < 9;
    
    // Create cache key based on filters
    const cacheKey = isZoomedOut 
      ? `map-trigs-all-${excludeFound}` 
      : `map-trigs-viewport-${bounds.north}-${bounds.south}-${bounds.east}-${bounds.west}-${excludeFound}`;
    
    // Check if we already have this data cached
    const cachedData = sessionStorage.getItem(cacheKey);
    const cacheTimestamp = sessionStorage.getItem(`${cacheKey}-timestamp`);
    const cacheAge = cacheTimestamp ? Date.now() - parseInt(cacheTimestamp) : Infinity;
    const maxAge = isZoomedOut ? 60 * 60 * 1000 : 2 * 60 * 1000; // 1 hour for all, 2 min for viewport
    
    if (cachedData && cacheAge < maxAge) {
      // Use cached data
      const parsed = JSON.parse(cachedData);
      setData(parsed.items);
      setTotalCount(parsed.total);
      setIsLoading(false);
      return;
    }
    
    // Fetch new data
    const fetchData = async () => {
      setIsLoading(true);
      setLoadingProgress(0);
      setError(null);
      
      try {
        const apiBase = import.meta.env.VITE_API_BASE as string;
        
        // Get auth token if needed
        const headers: Record<string, string> = {};
        if (excludeFound && isAuthenticated) {
          try {
            const token = await getAccessTokenSilently({ cacheMode: "on" });
            headers["Authorization"] = `Bearer ${token}`;
          } catch (error) {
            console.error("Failed to get access token:", error);
          }
        }
        
        if (isZoomedOut) {
          // Fetch ALL trigpoints using parallel batches
          const batchSize = 3000;
          const numBatches = 4;
          
          const fetchBatch = async (batchIndex: number): Promise<TrigsResponse | null> => {
            const skip = batchIndex * batchSize;
            const params = new URLSearchParams();
            params.append("limit", batchSize.toString());
            params.append("skip", skip.toString());
            
            if (excludeFound) {
              params.append("exclude_found", "true");
            }
            
            const res = await fetch(`${apiBase}/v1/trigs?${params.toString()}`, { headers });
            if (!res.ok) return null;
            
            const data = await res.json();
            setLoadingProgress((batchIndex + 1) / numBatches * 100);
            return data;
          };
          
          // Fetch batches in parallel
          const results = await Promise.all(
            Array.from({ length: numBatches }, (_, i) => fetchBatch(i))
          );
          
          // Combine results
          const allTrigpoints: Trig[] = [];
          let total = 0;
          
          for (const result of results) {
            if (result) {
              allTrigpoints.push(...result.items);
              if (result.pagination.total > total) {
                total = result.pagination.total;
              }
            }
          }
          
          setData(allTrigpoints);
          setTotalCount(total);
          
          // Cache the result
          sessionStorage.setItem(cacheKey, JSON.stringify({ items: allTrigpoints, total }));
          sessionStorage.setItem(`${cacheKey}-timestamp`, Date.now().toString());
        } else {
          // Fetch viewport trigpoints with parallel batches
          const { lat, lon, maxKm } = boundsToCenter(bounds);
          const batchSize = 500;
          const numBatches = 2;
          
          const fetchBatch = async (batchIndex: number): Promise<TrigsResponse | null> => {
            const skip = batchIndex * batchSize;
            const params = new URLSearchParams();
            params.append("limit", batchSize.toString());
            params.append("skip", skip.toString());
            params.append("lat", lat.toString());
            params.append("lon", lon.toString());
            params.append("max_km", maxKm.toString());
            params.append("order", "distance");
            
            if (excludeFound) {
              params.append("exclude_found", "true");
            }
            
            const res = await fetch(`${apiBase}/v1/trigs?${params.toString()}`, { headers });
            if (!res.ok) return null;
            
            const data = await res.json();
            setLoadingProgress((batchIndex + 1) / numBatches * 100);
            return data;
          };
          
          // Fetch batches in parallel
          const results = await Promise.all(
            Array.from({ length: numBatches }, (_, i) => fetchBatch(i))
          );
          
          // Combine results
          const allTrigpoints: Trig[] = [];
          let total = 0;
          
          for (const result of results) {
            if (result) {
              allTrigpoints.push(...result.items);
              if (result.pagination.total > total) {
                total = result.pagination.total;
              }
            }
          }
          
          setData(allTrigpoints);
          setTotalCount(total);
          
          // Cache the result
          sessionStorage.setItem(cacheKey, JSON.stringify({ items: allTrigpoints, total }));
          sessionStorage.setItem(`${cacheKey}-timestamp`, Date.now().toString());
        }
        
        setIsLoading(false);
        setLoadingProgress(100);
      } catch (err) {
        setError(err as Error);
        setIsLoading(false);
      }
    };
    
    fetchData();
  }, [bounds, excludeFound, enabled, zoom, getAccessTokenSilently, isAuthenticated]);
  
  return {
    data,
    totalCount,
    isLoading,
    loadingProgress,
    error,
  };
}

/**
 * Calculate center and radius from bounds
 */
function boundsToCenter(bounds: MapBounds): { lat: number; lon: number; maxKm: number } {
  const lat = (bounds.north + bounds.south) / 2;
  const lon = (bounds.east + bounds.west) / 2;
  
  // Calculate approximate radius in km
  const latDiff = bounds.north - bounds.south;
  const lonDiff = bounds.east - bounds.west;
  const degToKm = 111.32; // Approximate km per degree
  
  const latKm = latDiff * degToKm;
  const lonKm = lonDiff * degToKm * Math.cos((lat * Math.PI) / 180);
  
  // Use diagonal distance as radius
  const maxKm = Math.sqrt(latKm * latKm + lonKm * lonKm) / 2;
  
  return { lat, lon, maxKm };
}

