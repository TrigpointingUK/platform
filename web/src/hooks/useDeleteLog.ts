import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedDelete, AuthenticationError } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

export function useDeleteLog(logId: number, trigId: number) {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      await authenticatedDelete<void>(
        `${API_BASE}/v1/logs/${logId}`,
        getAccessTokenSilently
      );
    },
    onSuccess: () => {
      // Invalidate relevant queries after deletion
      queryClient.invalidateQueries({ queryKey: ["log", logId] });
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId }] });
      queryClient.invalidateQueries({ queryKey: ["trig", trigId] });
      queryClient.invalidateQueries({ queryKey: ["recentLogs"] });
      queryClient.invalidateQueries({ queryKey: ["userLogs"] });
      queryClient.invalidateQueries({ queryKey: ["user", "logged-trigs"] });
    },
    onError: (error) => {
      // Handle authentication errors by redirecting to login
      if (error instanceof AuthenticationError) {
        loginWithRedirect({
          appState: { returnTo: window.location.pathname },
        });
      }
    },
  });
}
