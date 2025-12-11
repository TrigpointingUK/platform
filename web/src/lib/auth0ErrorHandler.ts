/**
 * Centralised Auth0 error handling utilities.
 *
 * This module provides consistent handling for Auth0 authentication errors
 * across the application, ensuring users are properly redirected when their
 * session expires or requires re-authentication.
 */

import type { RedirectLoginOptions, LogoutOptions } from "@auth0/auth0-react";

/**
 * Known Auth0 error codes that we handle specifically
 */
export type Auth0ErrorCode =
  | "login_required"
  | "consent_required"
  | "missing_refresh_token"
  | "invalid_grant"
  | "interaction_required"
  | "access_denied";

/**
 * Shape of an Auth0 error object
 */
export interface Auth0Error {
  error: string;
  error_description?: string;
}

/**
 * Type guard to check if an error is an Auth0 error
 */
export function isAuth0Error(error: unknown): error is Auth0Error {
  return (
    typeof error === "object" &&
    error !== null &&
    "error" in error &&
    typeof (error as Auth0Error).error === "string"
  );
}

/**
 * Type for the loginWithRedirect function from Auth0
 */
export type LoginWithRedirect = (
  options?: RedirectLoginOptions
) => Promise<void>;

/**
 * Type for the logout function from Auth0
 */
export type LogoutFunction = (options?: LogoutOptions) => Promise<void>;

/**
 * Options for handling Auth0 errors
 */
export interface HandleAuth0ErrorOptions {
  /**
   * The current pathname to return to after re-authentication
   */
  returnTo?: string;

  /**
   * Whether to show a console warning for unhandled errors
   * @default true
   */
  logUnhandled?: boolean;
}

/**
 * Handle an Auth0 error by taking the appropriate action.
 *
 * This function handles common Auth0 errors:
 * - `login_required`: Session expired, redirect to login
 * - `consent_required`: Consent needed, redirect with prompt
 * - `missing_refresh_token`: Refresh token missing/invalid, logout and re-login
 * - `invalid_grant`: Refresh token revoked/expired, logout and re-login
 * - `interaction_required`: User interaction needed, redirect to login
 * - `access_denied`: Access was denied, logout
 *
 * @param error - The Auth0 error object
 * @param loginWithRedirect - The Auth0 loginWithRedirect function
 * @param logout - The Auth0 logout function
 * @param options - Additional options for error handling
 */
export function handleAuth0Error(
  error: Auth0Error,
  loginWithRedirect: LoginWithRedirect,
  logout: LogoutFunction,
  options: HandleAuth0ErrorOptions = {}
): void {
  const { returnTo = window.location.pathname, logUnhandled = true } = options;

  switch (error.error) {
    case "login_required":
    case "interaction_required":
      // Session expired or user interaction needed - redirect to login
      console.log(`Auth0 ${error.error}: redirecting to login...`);
      loginWithRedirect({
        appState: { returnTo },
      }).catch((err) => {
        console.error("Failed to redirect to login:", err);
      });
      break;

    case "consent_required":
      // Consent needed - redirect with consent prompt
      console.log("Auth0 consent_required: requesting consent...");
      loginWithRedirect({
        authorizationParams: {
          prompt: "consent",
        },
        appState: { returnTo },
      }).catch((err) => {
        console.error("Failed to redirect for consent:", err);
      });
      break;

    case "missing_refresh_token":
    case "invalid_grant":
      // Refresh token invalid/missing - full logout required
      console.log(`Auth0 ${error.error}: logging out and redirecting...`);
      logout({
        logoutParams: {
          returnTo: window.location.origin,
        },
      }).catch((err) => {
        console.error("Failed to logout:", err);
        // As a fallback, try to redirect to login anyway
        loginWithRedirect({
          appState: { returnTo },
        }).catch(() => {
          // Last resort: reload the page
          window.location.reload();
        });
      });
      break;

    case "access_denied":
      // Access was denied - just log out
      console.log("Auth0 access_denied: logging out...");
      logout({
        logoutParams: {
          returnTo: window.location.origin,
        },
      }).catch((err) => {
        console.error("Failed to logout:", err);
      });
      break;

    default:
      if (logUnhandled) {
        console.error("Unhandled Auth0 error:", error);
      }
  }
}

/**
 * Check if an error indicates that re-authentication is required
 */
export function requiresReauthentication(error: unknown): boolean {
  if (!isAuth0Error(error)) {
    return false;
  }

  const reAuthErrors: string[] = [
    "login_required",
    "consent_required",
    "missing_refresh_token",
    "invalid_grant",
    "interaction_required",
  ];

  return reAuthErrors.includes(error.error);
}

/**
 * Check if an error indicates a permanent authentication failure
 * (user should be logged out)
 */
export function requiresLogout(error: unknown): boolean {
  if (!isAuth0Error(error)) {
    return false;
  }

  const logoutErrors: string[] = [
    "missing_refresh_token",
    "invalid_grant",
    "access_denied",
  ];

  return logoutErrors.includes(error.error);
}

/**
 * Create an error message suitable for display to the user
 */
export function getAuth0ErrorMessage(error: Auth0Error): string {
  switch (error.error) {
    case "login_required":
      return "Your session has expired. Please log in again.";
    case "consent_required":
      return "Additional permissions are required. Please authorise the application.";
    case "missing_refresh_token":
    case "invalid_grant":
      return "Your session is no longer valid. Please log in again.";
    case "interaction_required":
      return "Please complete the login process.";
    case "access_denied":
      return "Access was denied. Please contact support if you believe this is an error.";
    default:
      return error.error_description || "An authentication error occurred.";
  }
}

