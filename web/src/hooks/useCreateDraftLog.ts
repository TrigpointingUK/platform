import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedFetch, AuthenticationError } from "../lib/authenticatedFetch";
import type { Log } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

/**
 * Hook to create a draft log for a trigpoint.
 *
 * Draft logs allow photos to be uploaded before the log is published.
 * If a draft already exists for this user/trig combination, it will be returned.
 */
export function useCreateDraftLog(trigId: number) {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<Log, Error, void>({
    mutationFn: async () => {
      // Create draft by passing draft=true with no body
      // Using authenticatedFetch directly to avoid sending an empty JSON body
      const response = await authenticatedFetch(
        `${API_BASE}/v1/logs?trig_id=${trigId}&draft=true`,
        {
          method: "POST",
          headers: {
            Accept: "application/json",
          },
        },
        getAccessTokenSilently
      );

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
      }

      return response.json() as Promise<Log>;
    },
    onSuccess: () => {
      // Invalidate logs query (though drafts won't appear in normal listings)
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId }] });
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

