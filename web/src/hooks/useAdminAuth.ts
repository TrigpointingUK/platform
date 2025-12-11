import { useEffect, useState, useRef } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useLocation } from "react-router-dom";

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
  const [isActivelyChecking, setIsActivelyChecking] = useState(false);
  const location = useLocation();

  // Check if user has api-admin role (from ID token)
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  // Track if we should be checking scope
  const shouldCheckScope = isAuthenticated && !isAuth0Loading && hasAdminRole;
  
  // Use ref to track if check has been initiated
  const checkInitiatedRef = useRef(false);

  useEffect(() => {
    // Reset check state when conditions change
    if (!shouldCheckScope) {
      checkInitiatedRef.current = false;
      return;
    }

    // Don't re-initiate if already initiated
    if (checkInitiatedRef.current) {
      return;
    }
    
    checkInitiatedRef.current = true;
    let cancelled = false;

    const checkAdminAuth = async () => {
      setIsActivelyChecking(true);
      
      try {
        // First, try to get the current token to check if we already have admin scope
        // Using default behaviour allows automatic token refresh if needed
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
          setIsActivelyChecking(false);
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
                setIsActivelyChecking(false);
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
          setIsActivelyChecking(false);
        }
      } catch (err: unknown) {
        console.error("Admin auth check failed:", err);

        const error =
          typeof err === "object" && err !== null
            ? (err as { error?: string })
            : undefined;
        
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
                  setIsActivelyChecking(false);
                });
              }
            }, 1500);
          } else {
            setIsActivelyChecking(false);
          }
        } else {
          if (!cancelled) {
            setHasAdminScope(false);
            setIsActivelyChecking(false);
          }
        }
      }
    };

    checkAdminAuth();

    return () => {
      cancelled = true;
    };
  }, [shouldCheckScope, getAccessTokenSilently, loginWithRedirect, location]);

  // Derive isCheckingScope from conditions - no effect needed for this
  const isCheckingScope = shouldCheckScope && (hasAdminScope === null || isActivelyChecking);

  return {
    hasAdminRole,
    hasAdminScope,
    isCheckingScope,
    isLoading: isAuth0Loading || isCheckingScope,
  };
}
