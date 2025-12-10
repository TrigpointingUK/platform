import { useQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedGet } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

interface LoggedTrig {
  trig_id: number;
  condition: string;
}

/**
 * Hook to fetch the authenticated user's logged trigpoints
 * 
 * Returns a Map<trig_id, condition> for O(1) lookup performance.
 * Only fetches data when the user is authenticated.
 * 
 * This data is used to color map markers based on the user's log history.
 */
export function useUserLoggedTrigs() {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();
  
  return useQuery<Map<number, string>>({
    queryKey: ["user", "logged-trigs"],
    queryFn: async () => {
      const data = await authenticatedGet<LoggedTrig[]>(
        `${API_BASE}/v1/users/me/logged-trigs`,
        getAccessTokenSilently
      );
      
      // Build Map for O(1) lookup
      return new Map(data.map(log => [log.trig_id, log.condition]));
    },
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

