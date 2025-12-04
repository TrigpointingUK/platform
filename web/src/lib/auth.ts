import { useAuth0 } from "@auth0/auth0-react";

export function useAccessToken() {
  const { getAccessTokenSilently, isAuthenticated, loginWithRedirect } = useAuth0();
  
  const getToken = async (): Promise<string> => {
    if (!isAuthenticated) {
      await loginWithRedirect({
        appState: { returnTo: window.location.pathname }
      });
      return "";
    }
    return await getAccessTokenSilently();
  };
  
  return { getToken };
}

