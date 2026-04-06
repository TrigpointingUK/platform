import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import toast from "react-hot-toast";
import {
  authenticatedPut,
  authenticatedDelete,
} from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

export interface PhotoRating {
  average_score: number | null;
  vote_count: number;
  user_score: number | null;
}

export function usePhotoRating(photoId: number | null) {
  const queryClient = useQueryClient();
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  const queryKey = ["photo-rating", photoId];

  const query = useQuery<PhotoRating>({
    queryKey,
    queryFn: async () => {
      const url = `${API_BASE}/v1/photos/${photoId}/rating`;
      const response = await fetch(url, {
        headers: { Accept: "application/json" },
      });
      if (!response.ok) throw new Error("Failed to fetch rating");
      return response.json();
    },
    enabled: photoId != null,
    staleTime: 60_000,
  });

  const rateMutation = useMutation<PhotoRating, Error, number>({
    mutationFn: async (score: number) => {
      return authenticatedPut<PhotoRating>(
        `${API_BASE}/v1/photos/${photoId}/rating`,
        { score },
        getAccessTokenSilently
      );
    },
    onMutate: async (score) => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<PhotoRating>(queryKey);
      if (previous) {
        queryClient.setQueryData<PhotoRating>(queryKey, {
          ...previous,
          user_score: score,
        });
      }
      return { previous };
    },
    onError: (_err, _score, context) => {
      if (context && typeof context === "object" && "previous" in context) {
        queryClient.setQueryData(queryKey, (context as { previous: PhotoRating }).previous);
      }
      toast.error("Failed to save rating");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const deleteMutation = useMutation<PhotoRating, Error, void>({
    mutationFn: async () => {
      return authenticatedDelete<PhotoRating>(
        `${API_BASE}/v1/photos/${photoId}/rating`,
        getAccessTokenSilently
      );
    },
    onMutate: async () => {
      await queryClient.cancelQueries({ queryKey });
      const previous = queryClient.getQueryData<PhotoRating>(queryKey);
      if (previous) {
        queryClient.setQueryData<PhotoRating>(queryKey, {
          ...previous,
          user_score: null,
        });
      }
      return { previous };
    },
    onError: (_err, _vars, context) => {
      if (context && typeof context === "object" && "previous" in context) {
        queryClient.setQueryData(queryKey, (context as { previous: PhotoRating }).previous);
      }
      toast.error("Failed to remove rating");
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey });
    },
  });

  const rate = (score: number) => {
    if (!isAuthenticated) return;
    if (score === 0) {
      deleteMutation.mutate();
    } else {
      rateMutation.mutate(score);
    }
  };

  return {
    rating: query.data ?? null,
    isLoading: query.isLoading,
    rate,
    isRating: rateMutation.isPending || deleteMutation.isPending,
    isAuthenticated,
  };
}
