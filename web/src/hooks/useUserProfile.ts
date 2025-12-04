import { useQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";

interface UserBreakdown {
  by_current_use: Record<string, number>;
  by_historic_use: Record<string, number>;
  by_physical_type: Record<string, number>;
  by_condition: Record<string, number>;
}

interface UserStats {
  total_logs: number;
  total_trigs_logged: number;
  total_photos: number;
}

interface UserPrefs {
  status_max: number;
  distance_ind: string;
  public_ind: string;
  online_map_type: string;
  online_map_type2: string;
  email: string;
  email_valid: string;
}

export interface UserProfile {
  id: number;
  name: string;
  firstname: string;
  surname: string;
  homepage: string | null;
  about: string;
  member_since: string | null;
  auth0_user_id?: string;
  roles?: string[];
  stats?: UserStats;
  breakdown?: UserBreakdown;
  prefs?: UserPrefs;
}

export function useUserProfile(userId: string | number) {
  const { getAccessTokenSilently, isAuthenticated, isLoading } = useAuth0();
  
  // Only fetch "me" profile if authenticated and Auth0 has finished loading
  const isMeQuery = userId === "me";
  const shouldFetch = !isMeQuery || (isAuthenticated && !isLoading);
  
  return useQuery<UserProfile>({
    queryKey: ["user", "profile", userId],
    enabled: shouldFetch,
    queryFn: async () => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      
      // Get token if viewing own profile
      let headers: Record<string, string> = {};
      if (isMeQuery) {
        if (!isAuthenticated) {
          throw new Error("Not authenticated - please log in");
        }
        
        try {
          const token = await getAccessTokenSilently({
            cacheMode: 'on', // Try to use cached token first
          });
          headers = { Authorization: `Bearer ${token}` };
        } catch (error) {
          console.error("Failed to get access token:", error);
          // Don't trigger loginWithRedirect here - let the calling component handle auth state
          throw new Error("Failed to get access token");
        }
      }
      
      // Include prefs (email) when fetching own profile
      const includes = isMeQuery 
        ? "stats,breakdown,prefs" 
        : "stats,breakdown";
      
      const response = await fetch(
        `${apiBase}/v1/users/${userId}?include=${includes}`,
        { headers }
      );
      if (!response.ok) {
        throw new Error("Failed to fetch user profile");
      }
      return response.json();
    },
    retry: false, // Don't retry if token fails
  });
}

export async function updateUserProfile(
  fields: Partial<UserProfile>,
  getAccessToken: () => Promise<string>
): Promise<void> {
  const apiBase = import.meta.env.VITE_API_BASE as string;
  
  // Get the access token
  const token = await getAccessToken();
  
  const response = await fetch(`${apiBase}/v1/users/me`, {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(fields),
  });
  
  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Failed to update profile");
  }
}

