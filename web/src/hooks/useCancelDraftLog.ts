import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedDelete, AuthenticationError } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

/**
 * Hook to cancel (delete) a draft log.
 *
 * This deletes the draft log and any photos that were uploaded to it.
 * Used when the user cancels log creation after starting a draft.
 */
export function useCancelDraftLog(logId: number | undefined, trigId: number) {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      if (!logId) {
        throw new Error("No draft log to cancel");
      }
      await authenticatedDelete<void>(
        `${API_BASE}/v1/logs/${logId}`,
        getAccessTokenSilently
      );
    },
    onSuccess: () => {
      // Invalidate relevant queries after deletion
      if (logId) {
        queryClient.invalidateQueries({ queryKey: ["log", logId] });
        queryClient.invalidateQueries({ queryKey: ["logPhotos", logId] });
      }
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId }] });
      queryClient.invalidateQueries({ queryKey: ["trig", trigId] });
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

