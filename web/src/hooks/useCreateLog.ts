import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { createLog, LogCreateInput, Log } from "../lib/api";

export function useCreateLog(trigId: number) {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<Log, Error, LogCreateInput>({
    mutationFn: async (data: LogCreateInput) => {
      const token = await getAccessTokenSilently();
      return createLog(trigId, data, token);
    },
    onSuccess: () => {
      // Invalidate logs query to refresh the list
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId }] });
      queryClient.invalidateQueries({ queryKey: ["trig", trigId] });
    },
  });
}

