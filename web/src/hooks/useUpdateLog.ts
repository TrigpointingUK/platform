import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { updateLog, LogUpdateInput, Log } from "../lib/api";

export function useUpdateLog(logId: number) {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<Log, Error, LogUpdateInput>({
    mutationFn: async (data: LogUpdateInput) => {
      const token = await getAccessTokenSilently();
      return updateLog(logId, data, token);
    },
    onSuccess: (updatedLog) => {
      // Invalidate and update relevant queries
      queryClient.invalidateQueries({ queryKey: ["log", logId] });
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId: updatedLog.trig_id }] });
      queryClient.invalidateQueries({ queryKey: ["trig", updatedLog.trig_id] });
    },
  });
}

