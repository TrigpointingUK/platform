/**
 * Auth0 Error Boundary Component
 *
 * This component provides global error handling for Auth0 authentication errors
 * that occur during React Query operations or other async processes.
 *
 * It catches authentication errors and handles them appropriately:
 * - Session expired: Redirect to login
 * - Refresh token invalid: Full logout
 * - Other auth errors: Display user-friendly message
 */

import { Component, ReactNode } from "react";
import { useAuth0, Auth0ContextInterface } from "@auth0/auth0-react";
import Button from "./ui/Button";
import {
  isAuth0Error,
  handleAuth0Error,
  getAuth0ErrorMessage,
  requiresReauthentication,
} from "../lib/auth0ErrorHandler";
import { AuthenticationError } from "../lib/authenticatedFetch";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error?: Error;
  isAuthError: boolean;
}

/**
 * Wrapper to inject Auth0 context into the class component
 */
function Auth0ErrorBoundaryWithAuth0(props: Props) {
  const auth0 = useAuth0();
  return <Auth0ErrorBoundaryInner {...props} auth0={auth0} />;
}

interface InnerProps extends Props {
  auth0: Auth0ContextInterface;
}

class Auth0ErrorBoundaryInner extends Component<InnerProps, State> {
  public state: State = {
    hasError: false,
    isAuthError: false,
  };

  public static getDerivedStateFromError(error: Error): State {
    // Check if this is an authentication error
    const isAuthError =
      error instanceof AuthenticationError ||
      isAuth0Error(error) ||
      requiresReauthentication(error);

    return {
      hasError: true,
      error,
      isAuthError,
    };
  }

  public componentDidCatch(error: Error) {
    console.error("Auth0ErrorBoundary caught error:", error);

    // If it's an Auth0 error, try to handle it automatically
    if (isAuth0Error(error)) {
      const { loginWithRedirect, logout } = this.props.auth0;
      handleAuth0Error(error, loginWithRedirect, logout);
    }
  }

  private handleLogin = () => {
    const { loginWithRedirect } = this.props.auth0;
    loginWithRedirect({
      appState: { returnTo: window.location.pathname },
    }).catch((err) => {
      console.error("Failed to redirect to login:", err);
    });
  };

  private handleLogout = () => {
    const { logout } = this.props.auth0;
    logout({
      logoutParams: {
        returnTo: window.location.origin,
      },
    }).catch((err) => {
      console.error("Failed to logout:", err);
      // Fallback: reload the page
      window.location.reload();
    });
  };

  private handleRetry = () => {
    this.setState({ hasError: false, error: undefined, isAuthError: false });
  };

  public render() {
    if (this.state.hasError && this.state.isAuthError) {
      const errorMessage = this.state.error
        ? isAuth0Error(this.state.error)
          ? getAuth0ErrorMessage(this.state.error)
          : this.state.error.message
        : "An authentication error occurred.";

      return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50 px-4">
          <div className="max-w-md w-full text-center">
            <div className="text-6xl mb-4">🔐</div>
            <h1 className="text-3xl font-bold text-gray-800 mb-4">
              Authentication Required
            </h1>
            <p className="text-gray-600 mb-6">{errorMessage}</p>
            <div className="flex gap-4 justify-center">
              <Button onClick={this.handleLogin} variant="primary">
                Log In
              </Button>
              <Button onClick={this.handleLogout} variant="secondary">
                Log Out
              </Button>
            </div>
          </div>
        </div>
      );
    }

    // For non-auth errors, let them propagate to the regular ErrorBoundary
    if (this.state.hasError) {
      // Re-throw non-auth errors to be caught by parent ErrorBoundary
      throw this.state.error;
    }

    return this.props.children;
  }
}

export default Auth0ErrorBoundaryWithAuth0;

