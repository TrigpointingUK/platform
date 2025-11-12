import { useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useNavigate, useLocation } from "react-router-dom";

interface UseAdminAuthResult {
  hasAdminRole: boolean;
  hasAdminScope: boolean | null;
  isCheckingScope: boolean;
  isLoading: boolean;
}

/**
 * Custom hook to handle admin authentication flow.
 * Checks if user has api-admin role and api:admin scope.
 * Handles re-authentication if needed.
 */
export function useAdminAuth(): UseAdminAuthResult {
  const { user, getAccessTokenSilently, loginWithRedirect, isLoading: isAuth0Loading, isAuthenticated } = useAuth0();
  const [hasAdminScope, setHasAdminScope] = useState<boolean | null>(null);
  const [isCheckingScope, setIsCheckingScope] = useState(true);
  const navigate = useNavigate();
  const location = useLocation();

  // Check if user has api-admin role (from ID token)
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  useEffect(() => {
    if (!isAuthenticated || isAuth0Loading || !hasAdminRole) {
      setIsCheckingScope(false);
      return;
    }

    let cancelled = false;

    const checkAdminAuth = async () => {
      try {
        // First, try to get the current token to check if we already have admin scope
        const currentToken = await getAccessTokenSilently();
        
        if (cancelled) return;

        // Decode the token to check scopes
        const payload = JSON.parse(atob(currentToken.split('.')[1]));
        const scopes = payload.scope?.split(' ') || [];
        const permissions = payload.permissions || [];
        
        // Check if we have api:admin in either scope or permissions
        const hasScope = scopes.includes('api:admin') || permissions.includes('api:admin');
        
        if (hasScope) {
          setHasAdminScope(true);
          setIsCheckingScope(false);
          return;
        }

        // We don't have the admin scope, need to re-authenticate
        setHasAdminScope(false);
        
        // Check if we just came back from auth to avoid loops
        const urlParams = new URLSearchParams(window.location.search);
        const attemptedAuth = urlParams.get('admin_auth_attempted') === 'true';
        
        if (!attemptedAuth) {
          // Redirect to get admin scope
          console.log("Admin role detected but missing api:admin scope. Redirecting for elevated permissions...");
          
          // Small delay to show UI message
          setTimeout(() => {
            if (!cancelled) {
              loginWithRedirect({
                authorizationParams: {
                  audience: import.meta.env.VITE_AUTH0_AUDIENCE as string,
                  scope: "openid profile email api:write api:read-pii api:admin",
                  prompt: "login", // Force re-authentication for security
                  redirect_uri: `${window.location.origin}${location.pathname}?admin_auth_attempted=true`,
                },
                appState: { returnTo: location.pathname },
              }).catch((error) => {
                console.error("Failed to redirect for admin authentication:", error);
                setIsCheckingScope(false);
              });
            }
          }, 1500);
        } else {
          // Already attempted auth, clear the parameter and don't loop
          urlParams.delete('admin_auth_attempted');
          const newUrl = urlParams.toString() 
            ? `${location.pathname}?${urlParams.toString()}` 
            : location.pathname;
          window.history.replaceState({}, '', newUrl);
          setIsCheckingScope(false);
        }
      } catch (error: any) {
        console.error("Admin auth check failed:", error);
        
        // Check if this is a consent or login required error
        if (error?.error === 'consent_required' || error?.error === 'login_required') {
          const urlParams = new URLSearchParams(window.location.search);
          const attemptedAuth = urlParams.get('admin_auth_attempted') === 'true';
          
          if (!attemptedAuth && !cancelled) {
            setTimeout(() => {
              if (!cancelled) {
                loginWithRedirect({
                  authorizationParams: {
                    audience: import.meta.env.VITE_AUTH0_AUDIENCE as string,
                    scope: "openid profile email api:write api:read-pii api:admin",
                    prompt: "login",
                    redirect_uri: `${window.location.origin}${location.pathname}?admin_auth_attempted=true`,
                  },
                  appState: { returnTo: location.pathname },
                }).catch((redirectError) => {
                  console.error("Failed to redirect:", redirectError);
                  setIsCheckingScope(false);
                });
              }
            }, 1500);
          } else {
            setIsCheckingScope(false);
          }
        } else {
          if (!cancelled) {
            setHasAdminScope(false);
            setIsCheckingScope(false);
          }
        }
      }
    };

    checkAdminAuth();

    return () => {
      cancelled = true;
    };
  }, [isAuthenticated, isAuth0Loading, hasAdminRole, getAccessTokenSilently, loginWithRedirect, location, navigate]);

  return {
    hasAdminRole,
    hasAdminScope,
    isCheckingScope,
    isLoading: isAuth0Loading || isCheckingScope,
  };
}
