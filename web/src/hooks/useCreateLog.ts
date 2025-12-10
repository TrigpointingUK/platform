import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedPost, LogCreateInput, Log } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

export function useCreateLog(trigId: number) {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<Log, Error, LogCreateInput>({
    mutationFn: async (data: LogCreateInput) => {
      return authenticatedPost<Log>(
        `${API_BASE}/v1/logs?trig_id=${trigId}`,
        data,
        getAccessTokenSilently
      );
    },
    onSuccess: () => {
      // Invalidate logs query to refresh the list
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId }] });
      queryClient.invalidateQueries({ queryKey: ["trig", trigId] });
    },
  });
}

