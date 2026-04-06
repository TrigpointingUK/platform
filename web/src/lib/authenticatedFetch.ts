/**
 * Authenticated fetch utility with automatic 401 retry logic.
 *
 * This module provides a fetch wrapper that:
 * 1. Automatically adds Bearer token authentication
 * 2. Retries once on 401 errors with a fresh token
 * 3. Provides consistent error handling for auth failures
 */

import type { GetTokenSilentlyOptions } from "@auth0/auth0-react";

/**
 * Type for the getAccessTokenSilently function from Auth0
 */
export type GetAccessTokenSilently = (
  options?: GetTokenSilentlyOptions
) => Promise<string>;

/**
 * Custom error class for authentication failures
 */
export class AuthenticationError extends Error {
  public readonly code: string;
  public readonly status?: number;

  constructor(code: string, message: string, status?: number) {
    super(message);
    this.name = "AuthenticationError";
    this.code = code;
    this.status = status;
  }
}

/**
 * Options for authenticatedFetch
 */
export interface AuthenticatedFetchOptions extends Omit<RequestInit, "headers"> {
  headers?: Record<string, string>;
}

/**
 * Perform an authenticated fetch request with automatic 401 retry.
 *
 * If the initial request returns a 401 Unauthorized, this function will:
 * 1. Force a token refresh (bypassing cache)
 * 2. Retry the request once with the new token
 * 3. If still 401, throw an AuthenticationError
 *
 * @param url - The URL to fetch
 * @param options - Fetch options (without Authorization header)
 * @param getAccessTokenSilently - The Auth0 getAccessTokenSilently function
 * @param retried - Internal flag to prevent infinite retry loops
 * @returns The fetch Response object
 * @throws AuthenticationError if authentication fails after retry
 */
export async function authenticatedFetch(
  url: string,
  options: AuthenticatedFetchOptions,
  getAccessTokenSilently: GetAccessTokenSilently,
  retried = false
): Promise<Response> {
  // Get access token (use default behaviour which auto-refreshes if needed)
  let token: string;
  try {
    token = await getAccessTokenSilently();
  } catch (error) {
    // Handle Auth0 errors from token retrieval (e.g., tokens deleted from localStorage)
    if (isAuth0Error(error)) {
      throw new AuthenticationError(
        error.error,
        error.error_description || "Authentication failed - please log in again",
        401
      );
    }
    throw new AuthenticationError(
      "token_retrieval_failed",
      "Failed to get authentication token - please log in again",
      401
    );
  }

  // Perform the request with the token
  const response = await fetch(url, {
    ...options,
    headers: {
      ...options.headers,
      Authorization: `Bearer ${token}`,
    },
  });

  // If we get a 401 and haven't retried yet, force a token refresh and retry
  if (response.status === 401 && !retried) {
    console.log("Received 401, forcing token refresh and retrying...");

    try {
      // Force token refresh by bypassing cache
      const freshToken = await getAccessTokenSilently({ cacheMode: "off" });

      // Retry the request with the fresh token
      const retryResponse = await fetch(url, {
        ...options,
        headers: {
          ...options.headers,
          Authorization: `Bearer ${freshToken}`,
        },
      });

      // If still 401 after refresh, the user needs to re-authenticate
      if (retryResponse.status === 401) {
        throw new AuthenticationError(
          "token_invalid_after_refresh",
          "Authentication failed. Please log out and log back in.",
          401
        );
      }

      return retryResponse;
    } catch (error) {
      // If token refresh itself fails, wrap the error
      if (error instanceof AuthenticationError) {
        throw error;
      }

      // Handle Auth0-specific errors
      if (isAuth0Error(error)) {
        throw new AuthenticationError(
          error.error,
          error.error_description || "Authentication failed",
          401
        );
      }

      throw new AuthenticationError(
        "token_refresh_failed",
        "Failed to refresh authentication token",
        401
      );
    }
  }

  return response;
}

/**
 * Check if an error is an Auth0 error object
 */
interface Auth0ErrorShape {
  error: string;
  error_description?: string;
}

function isAuth0Error(error: unknown): error is Auth0ErrorShape {
  return (
    typeof error === "object" &&
    error !== null &&
    "error" in error &&
    typeof (error as Auth0ErrorShape).error === "string"
  );
}

/**
 * Convenience function for authenticated GET requests
 */
export async function authenticatedGet<T>(
  url: string,
  getAccessTokenSilently: GetAccessTokenSilently,
  options?: Omit<AuthenticatedFetchOptions, "method">
): Promise<T> {
  const response = await authenticatedFetch(
    url,
    {
      ...options,
      method: "GET",
      headers: {
        Accept: "application/json",
        ...options?.headers,
      },
    },
    getAccessTokenSilently
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Convenience function for authenticated POST requests
 */
export async function authenticatedPost<T>(
  url: string,
  data: unknown,
  getAccessTokenSilently: GetAccessTokenSilently,
  options?: Omit<AuthenticatedFetchOptions, "method" | "body">
): Promise<T> {
  const response = await authenticatedFetch(
    url,
    {
      ...options,
      method: "POST",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options?.headers,
      },
      body: JSON.stringify(data),
    },
    getAccessTokenSilently
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Convenience function for authenticated PUT requests
 */
export async function authenticatedPut<T>(
  url: string,
  data: unknown,
  getAccessTokenSilently: GetAccessTokenSilently,
  options?: Omit<AuthenticatedFetchOptions, "method" | "body">
): Promise<T> {
  const response = await authenticatedFetch(
    url,
    {
      ...options,
      method: "PUT",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options?.headers,
      },
      body: JSON.stringify(data),
    },
    getAccessTokenSilently
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Convenience function for authenticated PATCH requests
 */
export async function authenticatedPatch<T>(
  url: string,
  data: unknown,
  getAccessTokenSilently: GetAccessTokenSilently,
  options?: Omit<AuthenticatedFetchOptions, "method" | "body">
): Promise<T> {
  const response = await authenticatedFetch(
    url,
    {
      ...options,
      method: "PATCH",
      headers: {
        Accept: "application/json",
        "Content-Type": "application/json",
        ...options?.headers,
      },
      body: JSON.stringify(data),
    },
    getAccessTokenSilently
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  return response.json() as Promise<T>;
}

/**
 * Convenience function for authenticated DELETE requests
 */
export async function authenticatedDelete<T = void>(
  url: string,
  getAccessTokenSilently: GetAccessTokenSilently,
  options?: Omit<AuthenticatedFetchOptions, "method">
): Promise<T> {
  const response = await authenticatedFetch(
    url,
    {
      ...options,
      method: "DELETE",
      headers: {
        Accept: "application/json",
        ...options?.headers,
      },
    },
    getAccessTokenSilently
  );

  if (!response.ok) {
    const text = await response.text().catch(() => "");
    throw new Error(`HTTP ${response.status}: ${text || response.statusText}`);
  }

  // Handle 204 No Content or empty responses (common for DELETE)
  if (response.status === 204 || response.headers.get("content-length") === "0") {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

