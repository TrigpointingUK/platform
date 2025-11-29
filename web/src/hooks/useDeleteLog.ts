import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { deleteLog } from "../lib/api";

export function useDeleteLog(logId: number, trigId: number) {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation<void, Error, void>({
    mutationFn: async () => {
      const token = await getAccessTokenSilently();
      return deleteLog(logId, token);
    },
    onSuccess: () => {
      // Invalidate relevant queries after deletion
      queryClient.invalidateQueries({ queryKey: ["log", logId] });
      queryClient.invalidateQueries({ queryKey: ["logs", { trigId }] });
      queryClient.invalidateQueries({ queryKey: ["trig", trigId] });
      queryClient.invalidateQueries({ queryKey: ["recentLogs"] });
      queryClient.invalidateQueries({ queryKey: ["userLogs"] });
    },
  });
}
