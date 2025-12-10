import { useQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedGet } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

interface CurrentUser {
  id: number;
  name: string;
  email?: string;
  // Add other fields as needed
}

export function useCurrentUser() {
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  return useQuery<CurrentUser>({
    queryKey: ["currentUser"],
    queryFn: async () => {
      return authenticatedGet<CurrentUser>(
        `${API_BASE}/v1/users/me`,
        getAccessTokenSilently
      );
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

