import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { authenticatedPatch, LogUpdateInput, Log } from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

export function useUpdateLog(logId: number) {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<Log, Error, LogUpdateInput>({
    mutationFn: async (data: LogUpdateInput) => {
      return authenticatedPatch<Log>(
        `${API_BASE}/v1/logs/${logId}`,
        data,
        getAccessTokenSilently
      );
    },
    onSuccess: (updatedLog) => {
      // Invalidate and update relevant queries
      queryClient.invalidateQueries({ queryKey: ["log", logId] });
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId: updatedLog.trig_id }] });
      queryClient.invalidateQueries({ queryKey: ["trig", updatedLog.trig_id] });
    },
  });
}

