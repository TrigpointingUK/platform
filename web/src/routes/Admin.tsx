import { useCallback, useEffect, useRef, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";

const ADMIN_REAUTH_DELAY_MS = import.meta.env.MODE === "test" ? 0 : 5000;
const ADMIN_DEBUG_LABEL = "[admin-scope]";
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_SCOPE = "api:admin";
const ADMIN_RETURN_PATH = "/admin";
const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };
const INTERACTIVE_AUTH_ERRORS = new Set([
  "login_required",
  "consent_required",
  "missing_scope",
  "missing_required_scope",
  "missing_refresh_token",
  "invalid_scope",
  "invalid_grant",
  "access_denied",
  "interaction_required",
  "unauthorized",
]);

const INTERACTIVE_AUTH_ERROR_HINTS = [
  "missing scope",
  "missing_required_scope",
  "missing required scope",
  "missing refresh token",
  "consent required",
  "login required",
  "interaction required",
  "access denied",
  "unauthorized",
];

// Helper function to decode JWT payload
interface JWTPayload {
  scope?: string;
  permissions?: string[];
  [key: string]: unknown;
}

function decodeJWT(token: string): JWTPayload | null {
  try {
    const base64Url = token.split(".")[1];
    const base64 = base64Url.replace(/-/g, "+").replace(/_/g, "/");
    const jsonPayload = decodeURIComponent(
      atob(base64)
        .split("")
        .map((c) => "%" + ("00" + c.charCodeAt(0).toString(16)).slice(-2))
        .join("")
    );
    return JSON.parse(jsonPayload) as JWTPayload;
  } catch (error) {
    console.error("Failed to decode JWT:", error);
    return null;
  }
}
>>>>>>> ffbb67f (docs: capture admin scope step-up flow)

function extractScopes(payload: JWTPayload | null): string[] {
  if (!payload) {
    return [];
  }

  if (typeof payload.scope === "string" && payload.scope.trim().length > 0) {
    return payload.scope.split(" ").map((scope) => scope.trim()).filter((scope) => scope.length > 0);
  }

  return [];
}

function logAdminDebug(message: string, details?: Record<string, unknown>) {
  if (!import.meta.env.DEV) {
    return;
  }

  if (details && Object.keys(details).length > 0) {
    console.debug(`${ADMIN_DEBUG_LABEL} ${message}`, details);
  } else {
    console.debug(`${ADMIN_DEBUG_LABEL} ${message}`);
  }
}

function isInteractiveAuthError(error: unknown): boolean {
  if (!error) {
    return false;
  }

  const candidate = error as { error?: string; message?: string; error_description?: string };
  const values = [candidate.error, candidate.message, candidate.error_description].filter(
    (value): value is string => typeof value === "string" && value.trim().length > 0
  );

  if (values.length === 0) {
    return false;
  }

  return values.some((rawValue) => {
    const code = rawValue.trim().toLowerCase();

    if (INTERACTIVE_AUTH_ERRORS.has(code)) {
      return true;
    }

    return INTERACTIVE_AUTH_ERROR_HINTS.some((hint) => code.includes(hint));
  });
}

export default function Admin() {
  const { user, getAccessTokenSilently, loginWithRedirect, isLoading: isAuth0Loading } = useAuth0();
  const [hasAdminScope, setHasAdminScope] = useState<boolean | null>(null);
  const [isCheckingScope, setIsCheckingScope] = useState(true);
  const redirectingRef = useRef(false);
  const reauthTimeoutRef = useRef<number | null>(null);
  const redirectDelayLabel =
    ADMIN_REAUTH_DELAY_MS >= 1000
      ? `Redirecting to login in ${ADMIN_REAUTH_DELAY_MS / 1000} seconds...`
      : "Redirecting to login...";

  const triggerAdminReauthentication = useCallback(() => {
    if (redirectingRef.current) {
      logAdminDebug("Re-authentication already in progress; skipping duplicate trigger.");
      return;
    }

    redirectingRef.current = true;
    sessionStorage.setItem("auth0_returnTo", ADMIN_RETURN_PATH);
    if (reauthTimeoutRef.current !== null) {
      window.clearTimeout(reauthTimeoutRef.current);
    }

    const timeoutId = window.setTimeout(() => {
      logAdminDebug("Initiating Auth0 re-authentication redirect.", {
        delayMs: ADMIN_REAUTH_DELAY_MS,
        scope: ADMIN_AUTH_PARAMS.scope,
        audience: ADMIN_AUTH_PARAMS.audience,
      });

      loginWithRedirect({
        authorizationParams: {
          ...ADMIN_AUTH_PARAMS,
          prompt: "consent",
        },
        appState: { returnTo: ADMIN_RETURN_PATH },
      })
        .catch((error) => {
          console.error("loginWithRedirect failed:", error);
          logAdminDebug("loginWithRedirect failed.", { error });
          redirectingRef.current = false;
        })
        .finally(() => {
          reauthTimeoutRef.current = null;
        });
    }, ADMIN_REAUTH_DELAY_MS);

    reauthTimeoutRef.current = timeoutId;
  }, [loginWithRedirect]);

  useEffect(() => {
    return () => {
      if (reauthTimeoutRef.current !== null) {
        window.clearTimeout(reauthTimeoutRef.current);
      }
    };
  }, []);

  // Check if user has api-admin role (from ID token)
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  // Check for api:admin scope in access token
  useEffect(() => {
    if (isAuth0Loading || !hasAdminRole) {
      return;
    }

    let cancelled = false;

    const checkAdminScope = async () => {
      setIsCheckingScope(true);

      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { ...ADMIN_AUTH_PARAMS },
        });

        if (cancelled) {
          return;
        }

        const decoded = decodeJWT(token);
        const scopes = extractScopes(decoded);
        const hasScope = scopes.includes(ADMIN_SCOPE);
        const permissionsClaim = decoded?.permissions;
        const permissions = Array.isArray(permissionsClaim)
          ? permissionsClaim.filter((permission): permission is string => typeof permission === "string")
          : [];
        const hasPermissionOnly = !hasScope && permissions.includes(ADMIN_SCOPE);

        logAdminDebug("Checked admin scope token", {
          hasScope,
          scopes,
          permissions,
          hasPermissionOnly,
          authTime: decoded?.auth_time,
          issuedAt: decoded?.iat,
          expiresAt: decoded?.exp,
          sessionReturnTo: sessionStorage.getItem("auth0_returnTo"),
        });

        setHasAdminScope(hasScope);

        if (hasScope) {
          if (reauthTimeoutRef.current !== null) {
            window.clearTimeout(reauthTimeoutRef.current);
            reauthTimeoutRef.current = null;
          }
          redirectingRef.current = false;
          logAdminDebug("Admin scope present; displaying admin dashboard.");
          return;
        }

        if (hasPermissionOnly) {
          console.info("api:admin permission detected without scope; requesting re-authentication.");
          logAdminDebug("Detected api:admin permission without scope; scheduling re-authentication.");
        }

        triggerAdminReauthentication();
      } catch (error) {
        console.error("Failed to check admin scope:", error);
        logAdminDebug("Failed to check admin scope.", { error });

        if (cancelled) {
          return;
        }

        setHasAdminScope(false);

        if (isInteractiveAuthError(error)) {
          console.info("Interactive Auth0 error detected; redirecting for admin re-authentication.");
          logAdminDebug("Interactive Auth0 error encountered during token check.", { error });
          triggerAdminReauthentication();
        } else {
          console.warn(
            "Auth0 returned a non-interactive error while checking admin scope. Forcing re-authentication as a fallback.",
            error
          );
          logAdminDebug("Non-interactive Auth0 error encountered; forcing re-authentication.", { error });
          triggerAdminReauthentication();
        }
      } finally {
        if (!cancelled) {
          setIsCheckingScope(false);
        }
      }
    };

    checkAdminScope();

    return () => {
      cancelled = true;
    };
  }, [getAccessTokenSilently, hasAdminRole, isAuth0Loading, triggerAdminReauthentication]);

  // User doesn't have admin role at all
  if (!hasAdminRole) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <h1 className="text-2xl font-bold text-gray-800 mb-4">
                Access Denied
              </h1>
              <p className="text-gray-600">
                You do not have permission to access the admin area.
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  // Loading or checking permissions
  if (isAuth0Loading || isCheckingScope || hasAdminScope === null) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <Spinner size="lg" />
              <p className="text-gray-600 mt-4">
                Verifying admin permissions...
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  // Has role but not scope - showing message before redirect
  if (!hasAdminScope) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <Spinner size="lg" />
              <p className="text-gray-600 mt-4">
                Admin access requires re-authentication.
              </p>
              <p className="text-sm text-gray-500 mt-2">
                {redirectDelayLabel}
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  // Has both role and scope - show admin page
  return (
    <Layout>
      <div className="max-w-6xl mx-auto">
        <Card className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-4">
            Admin Dashboard
          </h1>
          <p className="text-gray-600">
            Welcome to the admin area. More features coming soon.
          </p>
        </Card>

        {/* Placeholder sections for future admin features */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">
              User Management
            </h2>
            <p className="text-gray-500 text-sm">Coming soon...</p>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">
              Content Moderation
            </h2>
            <p className="text-gray-500 text-sm">Coming soon...</p>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">
              System Settings
            </h2>
            <p className="text-gray-500 text-sm">Coming soon...</p>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 mb-3">
              Analytics
            </h2>
            <p className="text-gray-500 text-sm">Coming soon...</p>
          </Card>
        </div>
      </div>
    </Layout>
  );
}

