import { useQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedGet, authenticatedPatch, type GetAccessTokenSilently } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

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

interface UIPrefs {
  distance_ind?: string;
  show_trig_condition?: boolean;
}

interface UserPrefs {
  status_max: number;
  distance_ind: string;
  public_ind: string;
  online_map_type: string;
  online_map_type2: string;
  email: string;
  email_valid: string;
  ui_prefs?: UIPrefs;
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
      // Include prefs (email) when fetching own profile
      const includes = isMeQuery 
        ? "stats,breakdown,prefs" 
        : "stats,breakdown";
      
      const url = `${API_BASE}/v1/users/${userId}?include=${includes}`;
      
      // Use authenticated fetch for own profile, regular fetch for others
      if (isMeQuery) {
        if (!isAuthenticated) {
          throw new Error("Not authenticated - please log in");
        }
        
        return authenticatedGet<UserProfile>(url, getAccessTokenSilently);
      }
      
      // Public profile - no auth needed
      const response = await fetch(url);
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
  getAccessTokenSilently: GetAccessTokenSilently
): Promise<void> {
  // Use authenticatedPatch which handles 401 retry automatically
  await authenticatedPatch<void>(
    `${API_BASE}/v1/users/me`,
    fields,
    getAccessTokenSilently
  );
}

