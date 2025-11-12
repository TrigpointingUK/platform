import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useAuth0 } from "@auth0/auth0-react";

/**
 * Handles navigation after Auth0 redirect callback.
 * Must be inside Router context to use navigate().
 */
export default function Auth0CallbackHandler() {
  const navigate = useNavigate();
  const location = useLocation();
  const { isLoading } = useAuth0();

  useEffect(() => {
    // Only act after Auth0 finishes loading
    if (!isLoading) {
      // Check if we just came back from Auth0 (state param in URL)
      const params = new URLSearchParams(location.search);
      if (params.has('code') && params.has('state')) {
        // Auth0 is processing the callback - check for saved return path
        const savedReturnTo = sessionStorage.getItem('auth0_returnTo');
        if (savedReturnTo) {
          console.log('Navigating to saved returnTo:', savedReturnTo);
          sessionStorage.removeItem('auth0_returnTo');
          // Navigate to the saved path
          navigate(savedReturnTo, { replace: true });
        }
      }
    }
  }, [isLoading, location, navigate]);

  return null;
}

