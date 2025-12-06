import { useState, useEffect, useMemo, useRef, useCallback } from "react";
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
  maxTrigpoints?: number;
}

/**
 * Hook to fetch trigpoints with progress tracking
 * 
 * Uses parallel batch loading for better performance.
 */
// In-memory cache for trigpoint data (persists for session but not across refreshes)
const trigsCache = new Map<string, { data: Trig[]; total: number; timestamp: number }>();

export function useMapTrigsWithProgress({
  bounds,
  excludeFound = false,
  enabled = true,
  zoom = 7,
  maxTrigpoints = 10000,
}: UseMapTrigsWithProgressOptions) {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  const [data, setData] = useState<Trig[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [isLoading, setIsLoading] = useState(false);
  const [loadingProgress, setLoadingProgress] = useState(0);
  const [error, setError] = useState<Error | null>(null);
  
  // Compute cache key
  const isZoomedOut = zoom < 9;
  const cacheKey = useMemo(() => {
    if (!enabled || !bounds) return null;
    return isZoomedOut 
      ? `map-trigs-all-${excludeFound}-${maxTrigpoints}` 
      : `map-trigs-viewport-${bounds.north.toFixed(2)}-${bounds.south.toFixed(2)}-${bounds.east.toFixed(2)}-${bounds.west.toFixed(2)}-${excludeFound}-${maxTrigpoints}`;
  }, [enabled, bounds, isZoomedOut, excludeFound, maxTrigpoints]);
  
  const maxAge = isZoomedOut ? 60 * 60 * 1000 : 2 * 60 * 1000;
  
  // Track previous cache key to detect changes
  const prevCacheKeyRef = useRef<string | null>(null);
  
  // Memoized fetch function
  const fetchData = useCallback(async () => {
    if (!bounds || !cacheKey) return;
    
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
        // Fetch trigpoints using parallel batches
        const batchSize = Math.min(3000, maxTrigpoints);
        const numBatches = Math.ceil(maxTrigpoints / batchSize);
        
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
        
        // Cache the result in memory
        trigsCache.set(cacheKey, {
          data: allTrigpoints,
          total,
          timestamp: Date.now(),
        });
      } else {
        // Fetch viewport trigpoints with parallel batches
        const { lat, lon, maxKm } = boundsToCenter(bounds);
        const batchSize = Math.min(500, Math.ceil(maxTrigpoints / 2));
        const numBatches = Math.min(2, Math.ceil(maxTrigpoints / batchSize));
        
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
        
        // Cache the result in memory
        trigsCache.set(cacheKey, {
          data: allTrigpoints,
          total,
          timestamp: Date.now(),
        });
      }
      
      setIsLoading(false);
      setLoadingProgress(100);
    } catch (err) {
      setError(err as Error);
      setIsLoading(false);
    }
  }, [bounds, cacheKey, excludeFound, isAuthenticated, isZoomedOut, maxTrigpoints, getAccessTokenSilently]);
  
  useEffect(() => {
    if (!enabled || !bounds || !cacheKey) {
      return;
    }
    
    // Check if cache key changed
    if (prevCacheKeyRef.current === cacheKey) {
      return;
    }
    prevCacheKeyRef.current = cacheKey;
    
    // Check cache (Date.now() is fine inside effect)
    const cached = trigsCache.get(cacheKey);
    if (cached && (Date.now() - cached.timestamp) < maxAge) {
      // Use cached data - this is reading from an external cache, not derived state
      // eslint-disable-next-line react-hooks/set-state-in-effect -- Reading from external memory cache
      setData(cached.data);
      setTotalCount(cached.total);
      setIsLoading(false);
      return;
    }
    
    // Fetch new data
    fetchData();
  }, [enabled, bounds, cacheKey, maxAge, fetchData]);
  
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
