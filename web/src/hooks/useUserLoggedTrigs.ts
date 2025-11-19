import { useQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";

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
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const token = await getAccessTokenSilently();
      
      const response = await fetch(`${apiBase}/v1/users/me/logged-trigs`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) {
        throw new Error("Failed to fetch logged trigs");
      }
      
      const data: LoggedTrig[] = await response.json();
      
      // Build Map for O(1) lookup
      return new Map(data.map(log => [log.trig_id, log.condition]));
    },
    enabled: isAuthenticated,
    staleTime: 1000 * 60 * 60, // 1 hour
  });
}

