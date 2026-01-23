import { useEffect, useMemo, useRef, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useLocation } from "react-router-dom";

interface UseAdminAuthResult {
  hasAdminRole: boolean;
  hasAdminScope: boolean | null;
  isCheckingScope: boolean;
  isLoading: boolean;
}

const ADMIN_SCOPE_CACHE_KEY = "trigpointing_admin_scope_verified";

/**
 * Get cached admin scope status from sessionStorage.
 * Returns true if admin scope was verified in this session, null otherwise.
 */
function getCachedAdminScope(): boolean | null {
  try {
    const cached = sessionStorage.getItem(ADMIN_SCOPE_CACHE_KEY);
    return cached === "true" ? true : null;
  } catch {
    return null;
  }
}

/**
 * Cache admin scope verification result in sessionStorage.
 */
function setCachedAdminScope(hasScope: boolean): void {
  try {
    if (hasScope) {
      sessionStorage.setItem(ADMIN_SCOPE_CACHE_KEY, "true");
    } else {
      sessionStorage.removeItem(ADMIN_SCOPE_CACHE_KEY);
    }
  } catch {
    // Ignore storage errors
  }
}

/**
 * Custom hook to handle admin authentication flow.
 * Checks if user has api-admin role and api:admin scope.
 * Handles re-authentication if needed.
 * Caches successful scope verification in sessionStorage to avoid
 * loading flashes when navigating between admin pages.
 */
export function useAdminAuth(): UseAdminAuthResult {
  const { user, getAccessTokenSilently, loginWithRedirect, isLoading: isAuth0Loading, isAuthenticated } = useAuth0();
  // Initialize from cache to avoid loading flash on navigation
  const [hasAdminScope, setHasAdminScope] = useState<boolean | null>(getCachedAdminScope);
  const [isActivelyChecking, setIsActivelyChecking] = useState(false);
  const location = useLocation();

  const adminAuthParams = useMemo(
    () => ({
      audience: import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined,
      scope: "openid profile email api:write api:read-pii api:admin",
    }),
    []
  );

  const decodeJwtPayload = (token: string): Record<string, unknown> => {
    const payload = token.split(".")[1];
    if (!payload) {
      throw new Error("Invalid JWT: missing payload");
    }

    // JWT payload is base64url (not base64)
    const base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    const padded = base64.padEnd(base64.length + ((4 - (base64.length % 4)) % 4), "=");
    return JSON.parse(atob(padded)) as Record<string, unknown>;
  };

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
      setIsActivelyChecking(false);
      setHasAdminScope(null);
      setCachedAdminScope(false);
      return;
    }

    // If we already have confirmed admin scope (from cache or previous check), skip re-checking
    if (hasAdminScope === true) {
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
        // IMPORTANT: request using the admin audience/scope cache key, otherwise Auth0 may
        // hand back a "basic" cached token even if we've previously acquired api:admin.
        const currentToken = await getAccessTokenSilently({
          authorizationParams: { ...adminAuthParams },
        });
        
        if (cancelled) return;

        // Decode the token to check scopes
        const payload = decodeJwtPayload(currentToken);
        const scopes = typeof payload.scope === "string" ? payload.scope.split(" ") : [];
        const permissions = Array.isArray(payload.permissions)
          ? payload.permissions.filter((permission): permission is string => typeof permission === "string")
          : [];
        
        // Check if we have api:admin in either scope or permissions
        const hasScope = scopes.includes("api:admin") || permissions.includes("api:admin");
        
        if (hasScope) {
          setHasAdminScope(true);
          setCachedAdminScope(true);
          setIsActivelyChecking(false);
          return;
        }

        // We don't have the admin scope, need to re-authenticate
        setHasAdminScope(false);
        setCachedAdminScope(false);
        // We're no longer "checking"; we're about to request elevation.
        setIsActivelyChecking(false);
        
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
                  ...adminAuthParams,
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
            // Switch UI to "requesting" while we schedule the redirect.
            setHasAdminScope(false);
            setIsActivelyChecking(false);
            setTimeout(() => {
              if (!cancelled) {
                loginWithRedirect({
                  authorizationParams: {
                    ...adminAuthParams,
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
      // React.StrictMode runs effects twice in dev (setup → cleanup → setup). If we keep the
      // "initiated" flag set across the simulated cleanup, the second run will be skipped,
      // leaving the hook stuck in a loading state.
      checkInitiatedRef.current = false;
      setIsActivelyChecking(false);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps -- hasAdminScope intentionally omitted to prevent re-checking loops
  }, [
    shouldCheckScope,
    getAccessTokenSilently,
    loginWithRedirect,
    location.pathname,
    adminAuthParams,
  ]);

  // Derive isCheckingScope from conditions - no effect needed for this
  const isCheckingScope = shouldCheckScope && (hasAdminScope === null || isActivelyChecking);

  // If we have a cached/verified admin scope, don't show loading even if Auth0 is still initializing.
  // This prevents the flash when navigating between admin pages.
  const hasCachedScope = hasAdminScope === true;

  return {
    hasAdminRole,
    hasAdminScope,
    isCheckingScope,
    isLoading: hasCachedScope ? false : (isAuth0Loading || isCheckingScope),
  };
}
