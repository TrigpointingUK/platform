import { useQuery } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";

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
      const token = await getAccessTokenSilently();
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(`${apiBase}/v1/users/me`, {
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });
      if (!response.ok) {
        throw new Error("Failed to fetch current user");
      }
      return response.json();
    },
    enabled: isAuthenticated,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });
}

