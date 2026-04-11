import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedPost, AuthenticationError, LogCreateInput, Log } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

/**
 * Hook to publish a draft log.
 *
 * This converts a draft log (status='D') to a published log (status='P')
 * by setting all the required fields from the payload.
 */
export function usePublishLog(logId: number, trigId: number) {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<Log, Error, LogCreateInput>({
    mutationFn: async (data: LogCreateInput) => {
      return authenticatedPost<Log>(
        `${API_BASE}/v1/logs/${logId}/publish`,
        data,
        getAccessTokenSilently
      );
    },
    onSuccess: () => {
      // Invalidate relevant queries after publishing
      queryClient.invalidateQueries({ queryKey: ["log", logId] });
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId }] });
      queryClient.invalidateQueries({ queryKey: ["trig", trigId] });
      queryClient.invalidateQueries({ queryKey: ["recentLogs"] });
      queryClient.invalidateQueries({ queryKey: ["userLogs"] });
      // Also invalidate log photos since they're now part of a published log
      queryClient.invalidateQueries({ queryKey: ["logPhotos", logId] });
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

