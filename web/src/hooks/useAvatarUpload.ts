import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useAuth0 } from "@auth0/auth0-react";
import { AuthenticationError } from "../lib/authenticatedFetch";

const API_BASE = import.meta.env.VITE_API_BASE as string;

interface AvatarResponse {
  avatar_url: string;
}

/**
 * Hook to upload a user avatar image.
 *
 * Forces a fresh token (like photo uploads) because file uploads are
 * expensive to retry on 401.  After a successful upload the Auth0 SDK
 * user object is refreshed so the Header picks up the new picture.
 */
export function useAvatarUpload() {
  const { getAccessTokenSilently, loginWithRedirect } = useAuth0();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (file: Blob): Promise<AvatarResponse> => {
      const freshToken = await getAccessTokenSilently({ cacheMode: "off" });

      const formData = new FormData();
      formData.append("file", file, "avatar.jpg");

      const response = await fetch(`${API_BASE}/v1/users/me/avatar`, {
        method: "POST",
        headers: {
          Authorization: `Bearer ${freshToken}`,
        },
        body: formData,
      });

      if (!response.ok) {
        const text = await response.text().catch(() => "");
        throw new Error(
          `HTTP ${response.status}: ${text || response.statusText}`
        );
      }

      return response.json() as Promise<AvatarResponse>;
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user", "profile"] });

      // Allow Auth0 a moment to propagate the picture change, then
      // refresh the SDK's user object so the Header avatar updates.
      setTimeout(() => {
        getAccessTokenSilently({ cacheMode: "off" }).catch(() => {});
      }, 2000);
    },
    onError: (error) => {
      if (error instanceof AuthenticationError) {
        loginWithRedirect({
          appState: { returnTo: window.location.pathname },
        });
      }
    },
  });
}
