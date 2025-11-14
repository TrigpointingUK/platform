import {
  ChangeEvent,
  FormEvent,
  useCallback,
  useEffect,
  useId,
  useMemo,
  useRef,
  useState,
} from "react";
import { useAuth0 } from "@auth0/auth0-react";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import {
  AdminUserSearchResult,
  migrateLegacyUser,
  searchLegacyUsers,
} from "../lib/api";

// const ADMIN_REAUTH_DELAY_MS = import.meta.env.MODE === "test" ? 0 : 5000;
const ADMIN_REAUTH_DELAY_MS = 0;
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

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

type GetAccessTokenSilently = ReturnType<typeof useAuth0>["getAccessTokenSilently"];

interface LegacyMigrationCardProps {
  getAccessTokenSilently: GetAccessTokenSilently;
}

function LegacyMigrationCard({ getAccessTokenSilently }: LegacyMigrationCardProps) {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AdminUserSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [hasSearched, setHasSearched] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [email, setEmail] = useState("");
  const [isMigrating, setIsMigrating] = useState(false);
  const [migrationError, setMigrationError] = useState<string | null>(null);
  const [migrationMessage, setMigrationMessage] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);

  const searchTimeoutRef = useRef<number | null>(null);
  const searchRequestRef = useRef(0);

  const searchInputId = useId();
  const selectId = useId();
  const emailInputId = useId();
  const replyTextareaId = useId();
  const panelId = useId();

  const selectedUser = useMemo(
    () => results.find((user) => user.id === selectedUserId) ?? null,
    [results, selectedUserId]
  );

  useEffect(() => {
    const trimmedQuery = query.trim();

    if (searchTimeoutRef.current !== null) {
      window.clearTimeout(searchTimeoutRef.current);
      searchTimeoutRef.current = null;
    }

    if (trimmedQuery.length < 2) {
      setResults([]);
      setHasSearched(false);
      setIsSearching(false);
      setSearchError(null);
      setSelectedUserId(null);
      return;
    }

    setIsSearching(true);
    setSearchError(null);
    const currentRequest = searchRequestRef.current + 1;
    searchRequestRef.current = currentRequest;

    searchTimeoutRef.current = window.setTimeout(() => {
      (async () => {
        try {
          const token = await getAccessTokenSilently({
            authorizationParams: { ...ADMIN_AUTH_PARAMS },
          });
          const data = await searchLegacyUsers(trimmedQuery, token);
          if (searchRequestRef.current !== currentRequest) {
            return;
          }
          setResults(data.items);
          setHasSearched(true);
          if (!data.items.some((user) => user.id === selectedUserId)) {
            setSelectedUserId(null);
          }
        } catch (error) {
          if (searchRequestRef.current !== currentRequest) {
            return;
          }
          setResults([]);
          setSelectedUserId(null);
          if (error instanceof Error) {
            setSearchError(error.message);
          } else {
            setSearchError("Failed to search for users. Please try again.");
          }
        } finally {
          if (searchRequestRef.current === currentRequest) {
            setIsSearching(false);
          }
        }
      })();
    }, 300);

    return () => {
      if (searchTimeoutRef.current !== null) {
        window.clearTimeout(searchTimeoutRef.current);
        searchTimeoutRef.current = null;
      }
    };
  }, [getAccessTokenSilently, query, selectedUserId]);

  const handleQueryChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    setQuery(event.target.value);
    setSearchError(null);
    setHasSearched(false);
    setMigrationError(null);
    setMigrationMessage(null);
  }, []);

  const handleSelectChange = useCallback(
    (event: ChangeEvent<HTMLSelectElement>) => {
      const value = event.target.value;
      if (!value) {
        setSelectedUserId(null);
        setEmail("");
        setMigrationMessage(null);
        setMigrationError(null);
        return;
      }

      const nextUserId = Number(value);
      setSelectedUserId(nextUserId);
      const match = results.find((user) => user.id === nextUserId);
      setEmail(match?.email ?? "");
      setMigrationMessage(null);
      setMigrationError(null);
    },
    [results]
  );

  const handleEmailChange = useCallback((event: ChangeEvent<HTMLInputElement>) => {
    setEmail(event.target.value);
    setMigrationMessage(null);
    setMigrationError(null);
  }, []);

  const handleMigrationSubmit = useCallback(
    async (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      if (!selectedUser) {
        return;
      }

      const trimmedEmail = email.trim();
      if (!EMAIL_PATTERN.test(trimmedEmail)) {
        setMigrationError("Please provide a valid email address before migrating.");
        return;
      }

      setIsMigrating(true);
      setMigrationError(null);
      setMigrationMessage(null);

      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { ...ADMIN_AUTH_PARAMS },
        });
        const response = await migrateLegacyUser(
          {
            user_id: selectedUser.id,
            email: trimmedEmail,
          },
          token
        );

        setMigrationMessage(response.message);
        setEmail(response.email);
        setResults((prev) =>
          prev.map((user) =>
            user.id === response.user_id
              ? {
                  ...user,
                  email: response.email,
                  auth0_user_id: response.auth0_user_id,
                  has_auth0_account: true,
                }
              : user
          )
        );
      } catch (error) {
        if (error instanceof Error) {
          setMigrationError(error.message);
        } else {
          setMigrationError("Migration failed. Please try again.");
        }
      } finally {
        setIsMigrating(false);
      }
    },
    [email, getAccessTokenSilently, selectedUser]
  );

  const trimmedEmail = email.trim();
  const emailIsValid = EMAIL_PATTERN.test(trimmedEmail);
  const canMigrate = Boolean(
    selectedUser && emailIsValid && !isMigrating && !selectedUser.has_auth0_account
  );

  const showExistingAuth0Notice =
    Boolean(selectedUser?.has_auth0_account) && migrationMessage === null;

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-controls={panelId}
          className="flex items-center gap-3 text-left focus:outline-none rounded-md text-[#046935]"
        >
          <svg
            className={`h-4 w-4 text-[#046935] transition-transform duration-200 ${
              isOpen ? "rotate-90" : ""
            }`}
            viewBox="0 0 8 12"
            fill="none"
            xmlns="http://www.w3.org/2000/svg"
            aria-hidden="true"
          >
            <path
              d="M1.5 1L6.5 6L1.5 11"
              stroke="currentColor"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </svg>
          <span className="text-2xl font-semibold">
            Legacy User Migration
          </span>
        </button>
      </div>

      {isOpen ? (
        <>
          <p className="text-gray-600 mb-4 mt-3">
            Search for a legacy account, confirm the preferred email address, and trigger the
            Auth0 migration workflow on the user&rsquo;s behalf.
          </p>

          <form
            id={panelId}
            onSubmit={handleMigrationSubmit}
            className="space-y-5"
          >
            <div>
              <label
                htmlFor={searchInputId}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Search legacy users
              </label>
              <input
                id={searchInputId}
                type="text"
                value={query}
                onChange={handleQueryChange}
                placeholder="Start typing a username or email fragment..."
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
              />
              <div className="flex items-center gap-2 mt-2">
                {isSearching && <Spinner size="sm" />}
                {searchError && <p className="text-sm text-red-600">{searchError}</p>}
                {!isSearching && hasSearched && results.length === 0 && !searchError ? (
                  <p className="text-sm text-gray-500">No matching users found.</p>
                ) : null}
              </div>
            </div>

            <div>
              <label
                htmlFor={selectId}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Matching users
              </label>
              <select
                id={selectId}
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 disabled:bg-gray-100"
                value={selectedUserId ?? ""}
                onChange={handleSelectChange}
                disabled={results.length === 0}
              >
                <option value="">Select a user…</option>
                {results.map((user) => (
                  <option
                    key={user.id}
                    value={user.id}
                    disabled={user.has_auth0_account}
                  >
                    {`${user.name} — ${user.email || "no email on file"}${
                      user.has_auth0_account ? " (already migrated)" : ""
                    }`}
                  </option>
                ))}
              </select>
              {showExistingAuth0Notice ? (
                <p className="mt-2 text-sm text-amber-600">
                  This account already has an Auth0 user identifier. Consider directing the
                  user to the Auth0 self-service password reset flow instead.
                </p>
              ) : null}
            </div>

            <div>
              <label
                htmlFor={emailInputId}
                className="block text-sm font-medium text-gray-700 mb-1"
              >
                Email address
              </label>
              <input
                id={emailInputId}
                type="email"
                value={email}
                onChange={handleEmailChange}
                placeholder="user@example.com"
                className="w-full rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
              />
              {!emailIsValid && email.length > 0 ? (
                <p className="mt-2 text-sm text-amber-600">
                  Please double-check the email address before proceeding.
                </p>
              ) : null}
            </div>

            {migrationError ? (
              <div className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-700">
                {migrationError}
              </div>
            ) : null}

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={!canMigrate}>
                {isMigrating ? (
                  <span className="flex items-center gap-2">
                    <Spinner size="sm" />
                    <span>Migrating…</span>
                  </span>
                ) : (
                  "Migrate"
                )}
              </Button>
              {migrationMessage ? (
                <p className="text-sm text-trig-green-700">Migration completed successfully.</p>
              ) : null}
            </div>

            {migrationMessage ? (
              <div>
                <label
                  className="block text-sm font-medium text-gray-700 mb-1"
                  htmlFor={replyTextareaId}
                >
                  Reply template for the user
                </label>
                <textarea
                  readOnly
                  value={migrationMessage}
                  id={replyTextareaId}
                  className="w-full h-32 rounded-md border border-gray-300 px-3 py-2 text-gray-800 shadow-sm focus:outline-none"
                />
              </div>
            ) : null}
          </form>
        </>
      ) : null}
    </Card>
  );
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

        <LegacyMigrationCard getAccessTokenSilently={getAccessTokenSilently} />

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

