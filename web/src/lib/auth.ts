/**
 * Centralised authentication utilities and hooks.
 *
 * This module provides a robust token retrieval hook that:
 * 1. Handles Auth0 errors consistently
 * 2. Provides automatic re-authentication when needed
 * 3. Offers a clean interface for getting access tokens
 */

import { useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import {
  handleAuth0Error,
  isAuth0Error,
  requiresReauthentication,
} from "./auth0ErrorHandler";

/**
 * Custom error class for authentication failures
 */
export class AuthError extends Error {
  public readonly code: string;

  constructor(code: string, message: string) {
    super(message);
    this.name = "AuthError";
    this.code = code;
  }
}

/**
 * Result type for the useAuthToken hook
 */
export interface UseAuthTokenResult {
  /**
   * Get an access token for API requests.
   * @param forceRefresh - If true, bypasses cache and gets a fresh token
   * @throws AuthError if not authenticated
   */
  getToken: (forceRefresh?: boolean) => Promise<string>;

  /**
   * Whether the user is currently authenticated
   */
  isAuthenticated: boolean;

  /**
   * Whether Auth0 is still loading
   */
  isLoading: boolean;

  /**
   * Trigger a login redirect
   */
  login: () => Promise<void>;

  /**
   * Trigger a logout
   */
  logout: () => Promise<void>;
}

/**
 * Hook for centralised token retrieval with error handling.
 *
 * This hook provides a consistent way to get access tokens across the app,
 * handling common Auth0 errors automatically.
 *
 * @example
 * ```tsx
 * function MyComponent() {
 *   const { getToken, isAuthenticated } = useAuthToken();
 *
 *   const fetchData = async () => {
 *     const token = await getToken();
 *     const response = await fetch('/api/data', {
 *       headers: { Authorization: `Bearer ${token}` }
 *     });
 *   };
 * }
 * ```
 */
export function useAuthToken(): UseAuthTokenResult {
  const {
    getAccessTokenSilently,
    isAuthenticated,
    isLoading,
    loginWithRedirect,
    logout,
  } = useAuth0();

  const getToken = useCallback(
    async (forceRefresh = false): Promise<string> => {
      if (!isAuthenticated) {
        throw new AuthError("not_authenticated", "User is not authenticated");
      }

      try {
        return await getAccessTokenSilently({
          cacheMode: forceRefresh ? "off" : undefined,
        });
      } catch (error) {
        // Handle specific Auth0 errors
        if (isAuth0Error(error)) {
          // Check if this requires re-authentication
          if (requiresReauthentication(error)) {
            // Let the error handler deal with redirects
            handleAuth0Error(error, loginWithRedirect, logout);
          }
          // Re-throw so the caller knows the operation failed
          throw new AuthError(error.error, error.error_description || "Authentication failed");
        }

        // Re-throw unknown errors
        throw error;
      }
    },
    [getAccessTokenSilently, isAuthenticated, loginWithRedirect, logout]
  );

  const login = useCallback(async () => {
    await loginWithRedirect({
      appState: { returnTo: window.location.pathname },
    });
  }, [loginWithRedirect]);

  const performLogout = useCallback(async () => {
    await logout({
      logoutParams: {
        returnTo: window.location.origin,
      },
    });
  }, [logout]);

  return {
    getToken,
    isAuthenticated,
    isLoading,
    login,
    logout: performLogout,
  };
}

/**
 * Legacy hook for backwards compatibility.
 * @deprecated Use useAuthToken instead
 */
export function useAccessToken() {
  const { getAccessTokenSilently, isAuthenticated, loginWithRedirect } =
    useAuth0();

  const getToken = async (): Promise<string> => {
    if (!isAuthenticated) {
      await loginWithRedirect({
        appState: { returnTo: window.location.pathname },
      });
      return "";
    }
    return await getAccessTokenSilently();
  };

  return { getToken };
}
