import React from "react";
import ReactDOM from "react-dom/client";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Auth0Provider, AppState } from "@auth0/auth0-react";
import { Toaster } from "react-hot-toast";
import AppRouter from "./router";
import ErrorBoundary from "./components/ErrorBoundary";
import "./app.css";

const queryClient = new QueryClient();

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
      <Auth0Provider
        domain={domain}
        clientId={clientId}
        authorizationParams={{
          audience,
          redirect_uri: redirectUri,
          scope: "openid profile email api:write api:read-pii offline_access",
        }}
        useRefreshTokens
        cacheLocation="localstorage"
        onRedirectCallback={(appState?: AppState) => {
          console.log('Auth0 redirect callback:', appState);
          // Return to the URL specified in appState, or default to home
          return appState?.returnTo || window.location.pathname;
        }}
      >
        <QueryClientProvider client={queryClient}>
          <AppRouter />
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
      </Auth0Provider>
    </ErrorBoundary>
  </React.StrictMode>
);

