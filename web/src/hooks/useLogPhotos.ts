import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { 
  getLogPhotos, 
  authenticatedPatch,
  authenticatedDelete,
  AuthenticationError,
  Photo 
} from "../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

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
 *
 * Note: Photo uploads force a fresh token to avoid race conditions where a
 * cached token is close to expiration and expires between retrieval and
 * server-side validation. This is especially important for file uploads
 * which cannot be efficiently retried on 401.
 */
export function useUploadPhoto(logId: number) {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
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
      // Force a fresh token for uploads to avoid near-expiry race conditions.
      // File uploads are expensive to retry, so we proactively ensure we have
      // a token with maximum remaining lifetime.
      const freshToken = await getAccessTokenSilently({ cacheMode: "off" });

      const formData = new FormData();
      formData.append("file", file);
      formData.append("caption", caption);
      formData.append("text_desc", text_desc);
      formData.append("type", type);
      formData.append("license", license);

      const response = await fetch(`${API_BASE}/v1/photos?log_id=${logId}`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${freshToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
      }

      return response.json() as Promise<Photo>;
    },
    onSuccess: () => {
      // Invalidate and refetch log photos
      queryClient.invalidateQueries({ queryKey: ["logPhotos", logId] });
      // Also invalidate the log detail to update photo count
      queryClient.invalidateQueries({ queryKey: ["log", logId] });
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

/**
 * Hook to update photo metadata
 */
export function useUpdatePhoto() {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
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
      return authenticatedPatch<Photo>(
        `${API_BASE}/v1/photos/${photoId}`,
        updates,
        getAccessTokenSilently
      );
    },
    onSuccess: (_, { photoId }) => {
      // Invalidate photo queries
      queryClient.invalidateQueries({ queryKey: ["photo", photoId] });
      queryClient.invalidateQueries({ queryKey: ["logPhotos"] });
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

/**
 * Hook to delete a photo
 */
export function useDeletePhoto() {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (photoId: number) => {
      await authenticatedDelete<void>(
        `${API_BASE}/v1/photos/${photoId}`,
        getAccessTokenSilently
      );
    },
    onSuccess: () => {
      // Invalidate all photo queries
      queryClient.invalidateQueries({ queryKey: ["logPhotos"] });
      queryClient.invalidateQueries({ queryKey: ["photo"] });
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

/**
 * Hook to rotate a photo
 *
 * Note: Like uploads, rotation operations force a fresh token because the
 * server-side operation (download, rotate, re-upload to S3) takes significant
 * time and we want to avoid token expiry mid-operation.
 */
export function useRotatePhoto() {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async ({
      photoId,
      angle,
    }: {
      photoId: number;
      angle: number;
    }) => {
      // Force a fresh token for rotate operations which involve server-side
      // file processing (download, rotate, re-upload to S3).
      const freshToken = await getAccessTokenSilently({ cacheMode: "off" });

      const response = await fetch(`${API_BASE}/v1/photos/${photoId}/rotate`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${freshToken}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ angle }),
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
      }

      return response.json() as Promise<Photo>;
    },
    onSuccess: () => {
      // Invalidate photo queries
      queryClient.invalidateQueries({ queryKey: ["logPhotos"] });
      queryClient.invalidateQueries({ queryKey: ["photo"] });
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

