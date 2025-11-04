import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { 
  getLogPhotos, 
  uploadPhoto, 
  updatePhoto, 
  deletePhoto,
  rotatePhoto,
  Photo 
} from "../lib/api";

/**
 * Hook to fetch photos for a log
 */
export function useLogPhotos(logId: number | undefined) {
  return useQuery<Photo[]>({
    queryKey: ["logPhotos", logId],
    queryFn: () => getLogPhotos(logId!),
    enabled: !!logId,
    staleTime: 60000, // 1 minute
  });
}

/**
 * Hook to upload a photo
 */
export function useUploadPhoto(logId: number) {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      file,
      caption,
      text_desc,
      type,
      license,
    }: {
      file: File;
      caption: string;
      text_desc: string;
      type: string;
      license: string;
    }) => {
      const token = await getAccessTokenSilently();
      return uploadPhoto(logId, file, caption, text_desc, type, license, token);
    },
    onSuccess: () => {
      // Invalidate and refetch log photos
      queryClient.invalidateQueries({ queryKey: ["logPhotos", logId] });
      // Also invalidate the log detail to update photo count
      queryClient.invalidateQueries({ queryKey: ["log", logId] });
    },
  });
}

/**
 * Hook to update photo metadata
 */
export function useUpdatePhoto() {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      photoId,
      updates,
    }: {
      photoId: number;
      updates: {
        caption?: string;
        text_desc?: string;
        type?: string;
        license?: string;
      };
    }) => {
      const token = await getAccessTokenSilently();
      return updatePhoto(photoId, updates, token);
    },
    onSuccess: (_, { photoId }) => {
      // Invalidate photo queries
      queryClient.invalidateQueries({ queryKey: ["photo", photoId] });
      queryClient.invalidateQueries({ queryKey: ["logPhotos"] });
    },
  });
}

/**
 * Hook to delete a photo
 */
export function useDeletePhoto() {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (photoId: number) => {
      const token = await getAccessTokenSilently();
      return deletePhoto(photoId, token);
    },
    onSuccess: () => {
      // Invalidate all photo queries
      queryClient.invalidateQueries({ queryKey: ["logPhotos"] });
      queryClient.invalidateQueries({ queryKey: ["photo"] });
    },
  });
}

/**
 * Hook to rotate a photo
 */
export function useRotatePhoto() {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      photoId,
      angle,
    }: {
      photoId: number;
      angle: number;
    }) => {
      const token = await getAccessTokenSilently();
      return rotatePhoto(photoId, angle, token);
    },
    onSuccess: () => {
      // Invalidate photo queries
      queryClient.invalidateQueries({ queryKey: ["logPhotos"] });
      queryClient.invalidateQueries({ queryKey: ["photo"] });
    },
  });
}

