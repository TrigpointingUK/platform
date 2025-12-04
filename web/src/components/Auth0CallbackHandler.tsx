import { useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";

/**
 * Handles navigation after Auth0 redirect callback.
 * Must be inside Router context to use navigate().
 * 
 * This component checks for a saved return path in sessionStorage after Auth0
 * finishes loading. The return path is saved by onRedirectCallback in main.tsx.
 */
export default function Auth0CallbackHandler() {
  const navigate = useNavigate();
  const { isLoading } = useAuth0();
  const hasChecked = useRef(false);

  useEffect(() => {
    // Only check once after Auth0 finishes initial loading
    if (!isLoading && !hasChecked.current) {
      hasChecked.current = true;
      
      // Check for saved return path (set by onRedirectCallback in main.tsx)
      const savedReturnTo = sessionStorage.getItem('auth0_returnTo');
      if (savedReturnTo) {
        console.log('Auth0CallbackHandler: navigating to saved returnTo:', savedReturnTo);
        sessionStorage.removeItem('auth0_returnTo');
        // Navigate to the saved path
        navigate(savedReturnTo, { replace: true });
      }
    }
  }, [isLoading, navigate]);

  // Reset the check flag if auth state changes (e.g., logout then login)
  useEffect(() => {
    if (isLoading) {
      hasChecked.current = false;
    }
  }, [isLoading]);

  return null;
}

