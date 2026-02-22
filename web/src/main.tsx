import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Auth0Provider, AppState } from "@auth0/auth0-react";
import { Toaster } from "react-hot-toast";
import AppRouter from "./router";
import ChatWidget from "./components/chat/ChatWidget";
import ErrorBoundary from "./components/ErrorBoundary";
import Auth0ErrorBoundary from "./components/Auth0ErrorBoundary";
import { ThemeProvider } from "./contexts/ThemeContext";
import { AuthenticationError } from "./lib/authenticatedFetch";
import { isAuth0Error } from "./lib/auth0ErrorHandler";
import "./app.css";

/**
 * Check if an error is an authentication error that shouldn't be retried
 */
function isAuthError(error: unknown): boolean {
  return error instanceof AuthenticationError || isAuth0Error(error);
}

/**
 * Configure QueryClient with smart retry logic:
 * - Don't retry authentication errors (user needs to re-auth)
 * - Retry other errors up to 3 times with exponential backoff
 */
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: (failureCount, error) => {
        // Don't retry auth errors - user needs to re-authenticate
        if (isAuthError(error)) {
          return false;
        }
        // For other errors, retry up to 3 times
        return failureCount < 3;
      },
      staleTime: 5 * 60 * 1000, // 5 minutes default stale time
    },
    mutations: {
      retry: (failureCount, error) => {
        // Don't retry auth errors
        if (isAuthError(error)) {
          return false;
        }
        // For mutations, only retry once
        return failureCount < 1;
      },
    },
  },
});

const domain = import.meta.env.VITE_AUTH0_DOMAIN as string;
const clientId = import.meta.env.VITE_AUTH0_CLIENT_ID as string;
const audience = import.meta.env.VITE_AUTH0_AUDIENCE as string;

// Use the same base URL logic as vite.config.ts
// Local dev and staging: / (root)
// Production: /app/
const baseUrl = import.meta.env.BASE_URL || '/';
const redirectUri = window.location.origin + baseUrl;

// Debug logging for development
console.log('Auth0 Configuration:', {
  domain,
  clientId,
  audience,
  redirectUri,
  baseUrl,
});

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <ThemeProvider>
        <Auth0Provider
          domain={domain}
          clientId={clientId}
          authorizationParams={{
            audience,
            redirect_uri: redirectUri,
            scope: "openid profile email api:write api:read-pii offline_access",
          }}
          useRefreshTokens
          useRefreshTokensFallback
          cacheLocation="localstorage"
          onRedirectCallback={(appState?: AppState) => {
            console.log('Auth0 redirect callback:', appState);
            // Save the return path to sessionStorage so Auth0CallbackHandler can navigate
            const targetUrl = appState?.returnTo || window.location.pathname;
            if (targetUrl && targetUrl !== '/' && targetUrl !== baseUrl) {
              sessionStorage.setItem('auth0_returnTo', targetUrl);
            }
          }}
        >
          <Auth0ErrorBoundary>
            <QueryClientProvider client={queryClient}>
              <AppRouter />
              <ChatWidget />
              <Toaster
                position="top-right"
                containerStyle={{
                  top: '5rem', // Position below the 4rem (h-16) header with a small gap
                }}
                toastOptions={{
                  duration: 5000,
                  error: {
                    style: {
                      background: '#dc2626',
                      color: '#fff',
                    },
                  },
                  success: {
                    style: {
                      background: '#16a34a',
                      color: '#fff',
                    },
                  },
                }}
              />
            </QueryClientProvider>
          </Auth0ErrorBoundary>
        </Auth0Provider>
      </ThemeProvider>
    </ErrorBoundary>
  </React.StrictMode>
);

