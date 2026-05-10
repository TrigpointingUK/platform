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
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Spinner from "../components/ui/Spinner";
import {
  AdminUserSearchResult,
  AdminMergeUsersPreview,
  AdminMergeUsersResponse,
  fetchNeedsAttentionSummary,
  fetchLogsNeedsAttentionSummary,
  LogNeedsAttentionSummary,
  mergeUsers,
  migrateLegacyUser,
  reissueLegacyUserEmail,
  searchLegacyUsers,
  TrigNeedsAttentionSummary,
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
  const [migrationWasReissue, setMigrationWasReissue] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [allowMigrated, setAllowMigrated] = useState(false);

  const searchTimeoutRef = useRef<number | null>(null);
  const searchRequestRef = useRef(0);

  const searchInputId = useId();
  const selectId = useId();
  const emailInputId = useId();
  const replyTextareaId = useId();
  const panelId = useId();
  const allowMigratedCheckboxId = useId();

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

      const isReissue = Boolean(selectedUser.has_auth0_account);

      if (isReissue) {
        const currentEmail = (selectedUser.email ?? "").trim();
        if (trimmedEmail.toLowerCase() === currentEmail.toLowerCase()) {
          setMigrationError("New email must differ from the current address.");
          return;
        }
        const confirmed = window.confirm(
          "This will delete the user's existing Auth0 account and create a new one bound to this email address. Continue?"
        );
        if (!confirmed) {
          return;
        }
      }

      setIsMigrating(true);
      setMigrationError(null);
      setMigrationMessage(null);

      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { ...ADMIN_AUTH_PARAMS },
        });
        const response = isReissue
          ? await reissueLegacyUserEmail(
              { user_id: selectedUser.id, email: trimmedEmail },
              token
            )
          : await migrateLegacyUser(
              { user_id: selectedUser.id, email: trimmedEmail },
              token
            );

        setMigrationMessage(response.message);
        setMigrationWasReissue(isReissue);
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
  const isReissue = Boolean(selectedUser?.has_auth0_account);
  const currentEmailForReissue = (selectedUser?.email ?? "").trim();
  const reissueEmailUnchanged =
    isReissue && trimmedEmail.length > 0
      ? trimmedEmail.toLowerCase() === currentEmailForReissue.toLowerCase()
      : false;
  const canMigrate = Boolean(
    selectedUser &&
      emailIsValid &&
      !isMigrating &&
      (isReissue ? !reissueEmailUnchanged : !selectedUser.has_auth0_account)
  );

  const showExistingAuth0Notice =
    Boolean(selectedUser?.has_auth0_account) && !allowMigrated && migrationMessage === null;

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-controls={panelId}
          className="flex items-center gap-3 text-left focus:outline-none rounded-md text-trig-green-600 dark:text-trig-green-400"
        >
          <svg
            className={`h-4 w-4 text-trig-green-600 dark:text-trig-green-400 transition-transform duration-200 ${
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
          <span className="text-2xl font-semibold text-gray-800 dark:text-gray-100">
            Legacy User Migration
          </span>
        </button>
      </div>

      {isOpen ? (
        <>
          <p className="text-gray-600 dark:text-gray-400 mb-4 mt-3">
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
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Search legacy users
              </label>
              <input
                id={searchInputId}
                type="text"
                value={query}
                onChange={handleQueryChange}
                placeholder="Start typing a username or email fragment..."
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 dark:placeholder-gray-400"
              />
              <div className="flex items-center gap-2 mt-2">
                {isSearching && <Spinner size="sm" />}
                {searchError && <p className="text-sm text-red-600 dark:text-red-400">{searchError}</p>}
                {!isSearching && hasSearched && results.length === 0 && !searchError ? (
                  <p className="text-sm text-gray-500 dark:text-gray-400">No matching users found.</p>
                ) : null}
              </div>
            </div>

            <div>
              <label
                htmlFor={selectId}
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Matching users
              </label>
              <div className="flex items-center gap-2 mb-2">
                <input
                  id={allowMigratedCheckboxId}
                  type="checkbox"
                  checked={allowMigrated}
                  onChange={(event) => {
                    const next = event.target.checked;
                    setAllowMigrated(next);
                    if (!next && selectedUser?.has_auth0_account) {
                      setSelectedUserId(null);
                      setEmail("");
                      setMigrationError(null);
                      setMigrationMessage(null);
                    }
                  }}
                  className="h-4 w-4 rounded border-gray-300 dark:border-gray-600 text-trig-green-600 focus:ring-trig-green-400"
                />
                <label
                  htmlFor={allowMigratedCheckboxId}
                  className="text-sm text-gray-700 dark:text-gray-300 select-none"
                >
                  Include users who already have an Auth0 account (re-issue email)
                </label>
              </div>
              <select
                id={selectId}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 disabled:bg-gray-100 dark:disabled:bg-gray-600"
                value={selectedUserId ?? ""}
                onChange={handleSelectChange}
                disabled={results.length === 0}
              >
                <option value="">Select a user…</option>
                {results.map((user) => (
                  <option
                    key={user.id}
                    value={user.id}
                    disabled={!allowMigrated && user.has_auth0_account}
                  >
                    {`${user.name} — ${user.email || "no email on file"}${
                      user.has_auth0_account
                        ? allowMigrated
                          ? " (already migrated — re-issue email)"
                          : " (already migrated)"
                        : ""
                    }`}
                  </option>
                ))}
              </select>
              {showExistingAuth0Notice ? (
                <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
                  This account already has an Auth0 user identifier. Consider directing the
                  user to the Auth0 self-service password reset flow instead.
                </p>
              ) : null}
            </div>

            <div>
              <label
                htmlFor={emailInputId}
                className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
              >
                Email address
              </label>
              <input
                id={emailInputId}
                type="email"
                value={email}
                onChange={handleEmailChange}
                placeholder="user@example.com"
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 dark:placeholder-gray-400"
              />
              {!emailIsValid && email.length > 0 ? (
                <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
                  Please double-check the email address before proceeding.
                </p>
              ) : null}
              {emailIsValid && reissueEmailUnchanged ? (
                <p className="mt-2 text-sm text-amber-600 dark:text-amber-400">
                  New email must differ from the current address.
                </p>
              ) : null}
            </div>

            {migrationError ? (
              <div className="rounded-md border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 px-3 py-2 text-sm text-red-700 dark:text-red-400">
                {migrationError}
              </div>
            ) : null}

            <div className="flex items-center gap-3">
              <Button type="submit" disabled={!canMigrate}>
                {isMigrating ? (
                  <span className="flex items-center gap-2">
                    <Spinner size="sm" />
                    <span>{isReissue ? "Updating…" : "Migrating…"}</span>
                  </span>
                ) : isReissue ? (
                  "New email"
                ) : (
                  "Migrate"
                )}
              </Button>
              {migrationMessage ? (
                <p className="text-sm text-trig-green-700 dark:text-trig-green-400">
                  {migrationWasReissue
                    ? "Email re-issued successfully."
                    : "Migration completed successfully."}
                </p>
              ) : null}
            </div>

            {migrationMessage ? (
              <div>
                <label
                  className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
                  htmlFor={replyTextareaId}
                >
                  Reply template for the user
                </label>
                <textarea
                  readOnly
                  value={migrationMessage}
                  id={replyTextareaId}
                  className="w-full h-32 rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:outline-none"
                />
              </div>
            ) : null}
          </form>
        </>
      ) : null}
    </Card>
  );
}

interface NeedsAttentionCardProps {
  getAccessTokenSilently: GetAccessTokenSilently;
}

function NeedsAttentionCard({ getAccessTokenSilently }: NeedsAttentionCardProps) {
  const [summary, setSummary] = useState<TrigNeedsAttentionSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(true);
  const panelId = useId();

  useEffect(() => {
    let cancelled = false;

    const fetchSummary = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { ...ADMIN_AUTH_PARAMS },
        });
        const data = await fetchNeedsAttentionSummary(token);

        if (!cancelled) {
          setSummary(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load summary");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchSummary();

    return () => {
      cancelled = true;
    };
  }, [getAccessTokenSilently]);

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-controls={panelId}
          className="flex items-center gap-3 text-left focus:outline-none rounded-md text-trig-green-600 dark:text-trig-green-400"
        >
          <svg
            className={`h-4 w-4 text-trig-green-600 dark:text-trig-green-400 transition-transform duration-200 ${
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
          <span className="text-2xl font-semibold text-gray-800 dark:text-gray-100">
            Trigpoints Needing Attention
          </span>
        </button>
      </div>

      {isOpen ? (
        <div id={panelId} className="mt-3">
          {isLoading && (
            <div className="flex items-center gap-2">
              <Spinner size="sm" />
              <span className="text-gray-600 dark:text-gray-400">Loading summary...</span>
            </div>
          )}

          {error && (
            <div className="text-red-600 dark:text-red-400 text-sm">
              Error: {error}
            </div>
          )}

          {summary && !isLoading && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-md">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Total flagged</div>
                  <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                    {summary.count}
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-md">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Latest update</div>
                  <div className="text-lg font-semibold text-gray-800 dark:text-gray-100">
                    {summary.latest_update
                      ? new Date(summary.latest_update).toLocaleString()
                      : "None"}
                  </div>
                </div>
              </div>

              <div className="mt-4">
                <a
                  href="/admin/needs-attention"
                  className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
                >
                  View all trigpoints needing attention →
                </a>
              </div>
            </div>
          )}
        </div>
      ) : null}
    </Card>
  );
}

interface LogsNeedsAttentionCardProps {
  getAccessTokenSilently: GetAccessTokenSilently;
}

function LogsNeedsAttentionCard({ getAccessTokenSilently }: LogsNeedsAttentionCardProps) {
  const [summary, setSummary] = useState<LogNeedsAttentionSummary | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(true);
  const panelId = useId();

  useEffect(() => {
    let cancelled = false;

    const fetchSummary = async () => {
      setIsLoading(true);
      setError(null);

      try {
        const token = await getAccessTokenSilently({
          authorizationParams: { ...ADMIN_AUTH_PARAMS },
        });
        const data = await fetchLogsNeedsAttentionSummary(token);

        if (!cancelled) {
          setSummary(data);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "Failed to load summary");
        }
      } finally {
        if (!cancelled) {
          setIsLoading(false);
        }
      }
    };

    fetchSummary();

    return () => {
      cancelled = true;
    };
  }, [getAccessTokenSilently]);

  const totalIssues = summary ? summary.orphaned_count + summary.duplicate_count : 0;

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-controls={panelId}
          className="flex items-center gap-3 text-left focus:outline-none rounded-md text-trig-green-600 dark:text-trig-green-400"
        >
          <svg
            className={`h-4 w-4 text-trig-green-600 dark:text-trig-green-400 transition-transform duration-200 ${
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
          <span className="text-2xl font-semibold text-gray-800 dark:text-gray-100">
            Logs Needing Attention
          </span>
        </button>
      </div>

      {isOpen ? (
        <div id={panelId} className="mt-3">
          {isLoading && (
            <div className="flex items-center gap-2">
              <Spinner size="sm" />
              <span className="text-gray-600 dark:text-gray-400">Loading summary...</span>
            </div>
          )}

          {error && (
            <div className="text-red-600 dark:text-red-400 text-sm">
              Error: {error}
            </div>
          )}

          {summary && !isLoading && (
            <div className="space-y-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-md">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Total orphaned</div>
                  <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                    {summary.orphaned_count}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Logs for deleted trigpoints
                  </div>
                </div>
                <div className="bg-gray-50 dark:bg-gray-700 p-4 rounded-md">
                  <div className="text-sm text-gray-600 dark:text-gray-400">Total duplicates</div>
                  <div className="text-2xl font-bold text-gray-800 dark:text-gray-100">
                    {summary.duplicate_count}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                    Identical logs without photos
                  </div>
                </div>
              </div>

              {totalIssues > 0 && (
                <div className="mt-4">
                  <a
                    href="/admin/attention/logs"
                    className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
                  >
                    View all logs needing attention →
                  </a>
                </div>
              )}

              {totalIssues === 0 && (
                <div className="text-gray-600 dark:text-gray-400 text-sm mt-2">
                  No logs currently need attention.
                </div>
              )}
            </div>
          )}
        </div>
      ) : null}
    </Card>
  );
}

interface DeleteAccountAdminCardProps {
  getAccessTokenSilently: GetAccessTokenSilently;
}

function DeleteAccountAdminCard({ getAccessTokenSilently }: DeleteAccountAdminCardProps) {
  const [isOpen, setIsOpen] = useState(false);
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<AdminUserSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [selectedUserId, setSelectedUserId] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const searchTimeoutRef = useRef<number | null>(null);
  const searchRequestRef = useRef(0);
  const searchInputId = useId();
  const selectId = useId();
  const panelId = useId();

  useEffect(() => {
    const trimmed = query.trim();
    if (searchTimeoutRef.current !== null) {
      window.clearTimeout(searchTimeoutRef.current);
      searchTimeoutRef.current = null;
    }
    if (trimmed.length < 2) {
      setResults([]);
      setIsSearching(false);
      return;
    }
    setIsSearching(true);
    const currentRequest = searchRequestRef.current + 1;
    searchRequestRef.current = currentRequest;
    searchTimeoutRef.current = window.setTimeout(() => {
      (async () => {
        try {
          const token = await getAccessTokenSilently({
            authorizationParams: { ...ADMIN_AUTH_PARAMS },
          });
          const data = await searchLegacyUsers(trimmed, token);
          if (searchRequestRef.current !== currentRequest) {
            return;
          }
          setResults(data.items);
          setError(null);
        } catch (e) {
          if (searchRequestRef.current !== currentRequest) {
            return;
          }
          setResults([]);
          setError(e instanceof Error ? e.message : "Failed to search users");
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
  }, [getAccessTokenSilently, query]);

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-controls={panelId}
          className="flex items-center gap-3 text-left focus:outline-none rounded-md text-trig-green-600 dark:text-trig-green-400"
        >
          <svg
            className={`h-4 w-4 text-trig-green-600 dark:text-trig-green-400 transition-transform duration-200 ${
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
          <span className="text-2xl font-semibold text-gray-800 dark:text-gray-100">
            Delete member account
          </span>
        </button>
      </div>

      {isOpen ? (
        <>
          <p className="text-gray-600 dark:text-gray-400 text-sm mb-4 mt-3">
            Search by username or email fragment, select a member, then open the guided deletion page
            (same flow as self-service, with administrator actions).
          </p>
          <div id={panelId} className="space-y-4 max-w-xl">
            <div>
              <label htmlFor={searchInputId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Search users
              </label>
              <input
                id={searchInputId}
                type="text"
                value={query}
                onChange={(e) => setQuery(e.target.value)}
                placeholder="Start typing username or email…"
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 dark:placeholder-gray-400"
              />
              {isSearching && (
                <div className="flex items-center gap-2 mt-2">
                  <Spinner size="sm" />
                  <span className="text-sm text-gray-500 dark:text-gray-400">Searching…</span>
                </div>
              )}
            </div>
            <div>
              <label htmlFor={selectId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Select user
              </label>
              <select
                id={selectId}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 disabled:bg-gray-100 dark:disabled:bg-gray-600"
                value={selectedUserId ?? ""}
                onChange={(e) => setSelectedUserId(e.target.value ? Number(e.target.value) : null)}
                disabled={results.length === 0}
              >
                <option value="">Choose a user…</option>
                {results.map((u) => (
                  <option key={u.id} value={u.id}>
                    {`${u.name} — ${u.email || "no email"} — ID: ${u.id}`}
                  </option>
                ))}
              </select>
            </div>
            {error && (
              <div className="rounded-md border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 px-3 py-2 text-sm text-red-700 dark:text-red-400">
                {error}
              </div>
            )}
            <div>
              <a
                href={selectedUserId ? `/account/delete?userId=${selectedUserId}` : "#"}
                aria-disabled={!selectedUserId}
                className={
                  selectedUserId
                    ? "inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
                    : "inline-block bg-gray-300 dark:bg-gray-600 text-gray-500 dark:text-gray-400 font-medium px-4 py-2 rounded-md cursor-not-allowed pointer-events-none"
                }
                onClick={(e) => {
                  if (!selectedUserId) {
                    e.preventDefault();
                  }
                }}
              >
                Open account deletion page →
              </a>
            </div>
          </div>
        </>
      ) : null}
    </Card>
  );
}

interface MergeUsersCardProps {
  getAccessTokenSilently: GetAccessTokenSilently;
}

function MergeUsersCard({ getAccessTokenSilently }: MergeUsersCardProps) {
  const [targetQuery, setTargetQuery] = useState("");
  const [sourceQuery, setSourceQuery] = useState("");
  const [targetResults, setTargetResults] = useState<AdminUserSearchResult[]>([]);
  const [sourceResults, setSourceResults] = useState<AdminUserSearchResult[]>([]);
  const [isSearchingTarget, setIsSearchingTarget] = useState(false);
  const [isSearchingSource, setIsSearchingSource] = useState(false);
  const [selectedTargetUserId, setSelectedTargetUserId] = useState<number | null>(null);
  const [selectedSourceUserId, setSelectedSourceUserId] = useState<number | null>(null);
  const [preview, setPreview] = useState<AdminMergeUsersPreview | null>(null);
  const [mergeResult, setMergeResult] = useState<AdminMergeUsersResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [isOpen, setIsOpen] = useState(false);
  const [showConfirmDialog, setShowConfirmDialog] = useState(false);

  const targetSearchTimeoutRef = useRef<number | null>(null);
  const sourceSearchTimeoutRef = useRef<number | null>(null);
  const targetSearchRequestRef = useRef(0);
  const sourceSearchRequestRef = useRef(0);

  const targetSearchInputId = useId();
  const targetSelectId = useId();
  const sourceSearchInputId = useId();
  const sourceSelectId = useId();
  const panelId = useId();

  // Search for target users
  useEffect(() => {
    const trimmedQuery = targetQuery.trim();

    if (targetSearchTimeoutRef.current !== null) {
      window.clearTimeout(targetSearchTimeoutRef.current);
      targetSearchTimeoutRef.current = null;
    }

    if (trimmedQuery.length < 2) {
      setTargetResults([]);
      setIsSearchingTarget(false);
      return;
    }

    setIsSearchingTarget(true);
    const currentRequest = targetSearchRequestRef.current + 1;
    targetSearchRequestRef.current = currentRequest;

    targetSearchTimeoutRef.current = window.setTimeout(() => {
      (async () => {
        try {
          const token = await getAccessTokenSilently({
            authorizationParams: { ...ADMIN_AUTH_PARAMS },
          });
          const data = await searchLegacyUsers(trimmedQuery, token);
          if (targetSearchRequestRef.current !== currentRequest) {
            return;
          }
          setTargetResults(data.items);
        } catch (error) {
          if (targetSearchRequestRef.current !== currentRequest) {
            return;
          }
          setTargetResults([]);
          setError(error instanceof Error ? error.message : "Failed to search users");
        } finally {
          if (targetSearchRequestRef.current === currentRequest) {
            setIsSearchingTarget(false);
          }
        }
      })();
    }, 300);

    return () => {
      if (targetSearchTimeoutRef.current !== null) {
        window.clearTimeout(targetSearchTimeoutRef.current);
        targetSearchTimeoutRef.current = null;
      }
    };
  }, [getAccessTokenSilently, targetQuery]);

  // Search for source users
  useEffect(() => {
    const trimmedQuery = sourceQuery.trim();

    if (sourceSearchTimeoutRef.current !== null) {
      window.clearTimeout(sourceSearchTimeoutRef.current);
      sourceSearchTimeoutRef.current = null;
    }

    if (trimmedQuery.length < 2) {
      setSourceResults([]);
      setIsSearchingSource(false);
      return;
    }

    setIsSearchingSource(true);
    const currentRequest = sourceSearchRequestRef.current + 1;
    sourceSearchRequestRef.current = currentRequest;

    sourceSearchTimeoutRef.current = window.setTimeout(() => {
      (async () => {
        try {
          const token = await getAccessTokenSilently({
            authorizationParams: { ...ADMIN_AUTH_PARAMS },
          });
          const data = await searchLegacyUsers(trimmedQuery, token);
          if (sourceSearchRequestRef.current !== currentRequest) {
            return;
          }
          setSourceResults(data.items);
        } catch (error) {
          if (sourceSearchRequestRef.current !== currentRequest) {
            return;
          }
          setSourceResults([]);
          setError(error instanceof Error ? error.message : "Failed to search users");
        } finally {
          if (sourceSearchRequestRef.current === currentRequest) {
            setIsSearchingSource(false);
          }
        }
      })();
    }, 300);

    return () => {
      if (sourceSearchTimeoutRef.current !== null) {
        window.clearTimeout(sourceSearchTimeoutRef.current);
        sourceSearchTimeoutRef.current = null;
      }
    };
  }, [getAccessTokenSilently, sourceQuery]);

  const handlePreviewMerge = useCallback(async () => {
    if (!selectedTargetUserId || !selectedSourceUserId) {
      return;
    }

    setIsLoading(true);
    setError(null);
    setPreview(null);
    setMergeResult(null);

    try {
      const token = await getAccessTokenSilently({
        authorizationParams: { ...ADMIN_AUTH_PARAMS },
      });
      const response = await mergeUsers(
        {
          target_user_id: selectedTargetUserId,
          source_user_id: selectedSourceUserId,
          dry_run: true,
        },
        token
      );

      if ("dry_run" in response && response.dry_run) {
        setPreview(response);
        setShowConfirmDialog(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to preview merge");
    } finally {
      setIsLoading(false);
    }
  }, [selectedTargetUserId, selectedSourceUserId, getAccessTokenSilently]);

  const handleConfirmMerge = useCallback(async () => {
    if (!selectedTargetUserId || !selectedSourceUserId) {
      return;
    }

    setIsLoading(true);
    setError(null);

    try {
      const token = await getAccessTokenSilently({
        authorizationParams: { ...ADMIN_AUTH_PARAMS },
      });
      const response = await mergeUsers(
        {
          target_user_id: selectedTargetUserId,
          source_user_id: selectedSourceUserId,
          dry_run: false,
        },
        token
      );

      if ("success" in response && response.success) {
        setMergeResult(response);
        setShowConfirmDialog(false);
        setPreview(null);
        // Reset selections
        setSelectedTargetUserId(null);
        setSelectedSourceUserId(null);
        setTargetQuery("");
        setSourceQuery("");
        setTargetResults([]);
        setSourceResults([]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to execute merge");
    } finally {
      setIsLoading(false);
    }
  }, [selectedTargetUserId, selectedSourceUserId, getAccessTokenSilently]);

  const canPreview = Boolean(
    selectedTargetUserId &&
      selectedSourceUserId &&
      selectedTargetUserId !== selectedSourceUserId &&
      !isLoading
  );

  return (
    <Card className="mb-6">
      <div className="flex items-center justify-between">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          aria-expanded={isOpen}
          aria-controls={panelId}
          className="flex items-center gap-3 text-left focus:outline-none rounded-md text-trig-green-600 dark:text-trig-green-400"
        >
          <svg
            className={`h-4 w-4 text-trig-green-600 dark:text-trig-green-400 transition-transform duration-200 ${
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
          <span className="text-2xl font-semibold text-gray-800 dark:text-gray-100">Merge Users</span>
        </button>
      </div>

      {isOpen ? (
        <>
          <p className="text-gray-600 dark:text-gray-400 mb-4 mt-3">
            Merge a source user (to delete) into a target user (to keep). All logs and photo votes
            will be transferred, and blank profile fields will be filled from the source user.
          </p>

          <div id={panelId} className="space-y-5">
            {/* Target User Selection */}
            <div>
              <label htmlFor={targetSearchInputId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Search for target user (keep)
              </label>
              <input
                id={targetSearchInputId}
                type="text"
                value={targetQuery}
                onChange={(e) => setTargetQuery(e.target.value)}
                placeholder="Start typing username or email..."
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 dark:placeholder-gray-400"
              />
              {isSearchingTarget && (
                <div className="flex items-center gap-2 mt-2">
                  <Spinner size="sm" />
                  <span className="text-sm text-gray-500 dark:text-gray-400">Searching...</span>
                </div>
              )}
            </div>

            <div>
              <label htmlFor={targetSelectId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Target user (keep)
              </label>
              <select
                id={targetSelectId}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 disabled:bg-gray-100 dark:disabled:bg-gray-600"
                value={selectedTargetUserId ?? ""}
                onChange={(e) => setSelectedTargetUserId(e.target.value ? Number(e.target.value) : null)}
                disabled={targetResults.length === 0}
              >
                <option value="">Select target user…</option>
                {targetResults.map((user) => (
                  <option key={user.id} value={user.id}>
                    {`${user.name} — ${user.email || "no email"} — ID: ${user.id}`}
                  </option>
                ))}
              </select>
            </div>

            {/* Source User Selection */}
            <div>
              <label htmlFor={sourceSearchInputId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Search for source user (delete)
              </label>
              <input
                id={sourceSearchInputId}
                type="text"
                value={sourceQuery}
                onChange={(e) => setSourceQuery(e.target.value)}
                placeholder="Start typing username or email..."
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 dark:placeholder-gray-400"
              />
              {isSearchingSource && (
                <div className="flex items-center gap-2 mt-2">
                  <Spinner size="sm" />
                  <span className="text-sm text-gray-500 dark:text-gray-400">Searching...</span>
                </div>
              )}
            </div>

            <div>
              <label htmlFor={sourceSelectId} className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                Source user (delete)
              </label>
              <select
                id={sourceSelectId}
                className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400 disabled:bg-gray-100 dark:disabled:bg-gray-600"
                value={selectedSourceUserId ?? ""}
                onChange={(e) => setSelectedSourceUserId(e.target.value ? Number(e.target.value) : null)}
                disabled={sourceResults.length === 0}
              >
                <option value="">Select source user…</option>
                {sourceResults.map((user) => (
                  <option key={user.id} value={user.id}>
                    {`${user.name} — ${user.email || "no email"} — ID: ${user.id}`}
                  </option>
                ))}
              </select>
            </div>

            {selectedTargetUserId && selectedSourceUserId && selectedTargetUserId === selectedSourceUserId && (
              <p className="text-sm text-red-600 dark:text-red-400">Target and source users must be different!</p>
            )}

            {error && (
              <div className="rounded-md border border-red-200 dark:border-red-800 bg-red-50 dark:bg-red-900/30 px-3 py-2 text-sm text-red-700 dark:text-red-400">
                {error}
              </div>
            )}

            <div>
              <Button type="button" onClick={handlePreviewMerge} disabled={!canPreview}>
                {isLoading ? (
                  <span className="flex items-center gap-2">
                    <Spinner size="sm" />
                    <span>Loading...</span>
                  </span>
                ) : (
                  "Preview Merge"
                )}
              </Button>
            </div>

            {mergeResult && (
              <div className="rounded-md border border-green-200 dark:border-green-800 bg-green-50 dark:bg-green-900/30 px-4 py-3">
                <h3 className="font-semibold text-green-800 dark:text-green-400 mb-2">Merge Completed Successfully!</h3>
                <ul className="text-sm text-green-700 dark:text-green-400 space-y-1">
                  <li>• {mergeResult.updated_records.tlog} logs transferred</li>
                  <li>• {mergeResult.updated_records.tphotovote} photo votes transferred</li>
                  {mergeResult.profile_updated && <li>• Profile fields updated</li>}
                  {mergeResult.auth0_updated && <li>• Auth0 account synchronized</li>}
                </ul>
              </div>
            )}
          </div>

          {/* Confirmation Dialog */}
          {showConfirmDialog && preview && (
            <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
              <div className="bg-white dark:bg-gray-800 rounded-lg p-6 max-w-2xl w-full mx-4 max-h-[90vh] overflow-y-auto">
                <h2 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">Confirm User Merge</h2>

                <div className="space-y-4 mb-6">
                  <div className="border border-gray-200 dark:border-gray-600 rounded-md p-4">
                    <h3 className="font-semibold text-gray-800 dark:text-gray-100 mb-2">Target User (KEEP)</h3>
                    <div className="text-sm text-gray-600 dark:text-gray-400 space-y-1">
                      <p><strong>User ID:</strong> {preview.target_user.id}</p>
                      <p><strong>Name:</strong> {preview.target_user.name}</p>
                      <p><strong>Email:</strong> {preview.target_user.email || "(none)"}</p>
                      <p><strong>Auth0 ID:</strong> {preview.target_user.auth0_user_id || "(none)"}</p>
                    </div>
                  </div>

                  <div className="border border-red-200 dark:border-red-800 rounded-md p-4 bg-red-50 dark:bg-red-900/30">
                    <h3 className="font-semibold text-red-800 dark:text-red-400 mb-2">Source User (DELETE)</h3>
                    <div className="text-sm text-red-700 dark:text-red-400 space-y-1">
                      <p><strong>User ID:</strong> {preview.source_user.id}</p>
                      <p><strong>Name:</strong> {preview.source_user.name}</p>
                      <p><strong>Email:</strong> {preview.source_user.email || "(none)"}</p>
                      <p><strong>Auth0 ID:</strong> {preview.source_user.auth0_user_id || "(none)"}</p>
                    </div>
                  </div>

                  <div className="border border-blue-200 dark:border-blue-800 rounded-md p-4 bg-blue-50 dark:bg-blue-900/30">
                    <h3 className="font-semibold text-blue-800 dark:text-blue-400 mb-2">Changes</h3>
                    <div className="text-sm text-blue-700 dark:text-blue-400 space-y-1">
                      <p><strong>Logs to transfer:</strong> {preview.estimated_records.tlog}</p>
                      <p><strong>Photo votes to transfer:</strong> {preview.estimated_records.tphotovote}</p>
                      <p><strong>Member since:</strong> {preview.member_since}</p>
                      {Object.keys(preview.profile_updates).length > 0 && (
                        <>
                          <p className="mt-2"><strong>Profile fields to update:</strong></p>
                          <ul className="ml-4">
                            {Object.entries(preview.profile_updates).map(([field, value]) => (
                              <li key={field}>• {field}: {String(value)}</li>
                            ))}
                          </ul>
                        </>
                      )}
                      {preview.auth0_will_update && (
                        <p className="mt-2 font-semibold text-amber-700 dark:text-amber-400">⚠️ Auth0 account will be synchronized</p>
                      )}
                    </div>
                  </div>

                  <div className="rounded-md border border-red-300 dark:border-red-700 bg-red-100 dark:bg-red-900/50 px-4 py-3">
                    <p className="text-sm text-red-800 dark:text-red-300 font-semibold">
                      ⚠️ Warning: This action cannot be undone. The source user will be permanently deleted.
                    </p>
                  </div>
                </div>

                <div className="flex gap-3 justify-end">
                  <Button
                    type="button"
                    onClick={() => {
                      setShowConfirmDialog(false);
                      setPreview(null);
                    }}
                    disabled={isLoading}
                  >
                    Cancel
                  </Button>
                  <Button
                    type="button"
                    onClick={handleConfirmMerge}
                    disabled={isLoading}
                  >
                    {isLoading ? (
                      <span className="flex items-center gap-2">
                        <Spinner size="sm" />
                        <span>Merging...</span>
                      </span>
                    ) : (
                      "Confirm Merge"
                    )}
                  </Button>
                </div>
              </div>
            </div>
          )}
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
      <>
        <title>Admin | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
                Access Denied
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                You do not have permission to access the admin area.
              </p>
            </div>
          </Card>
        </div>
      </>
    );
  }

  // Loading or checking permissions
  if (isAuth0Loading || isCheckingScope || hasAdminScope === null) {
    return (
      <>
        <title>Admin | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <Spinner size="lg" />
              <p className="text-gray-600 dark:text-gray-400 mt-4">
                Verifying admin permissions...
              </p>
            </div>
          </Card>
        </div>
      </>
    );
  }

  // Has role but not scope - showing message before redirect
  if (!hasAdminScope) {
    return (
      <>
        <title>Admin | TrigpointingUK</title>
        <div className="max-w-4xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <Spinner size="lg" />
              <p className="text-gray-600 dark:text-gray-400 mt-4">
                Admin access requires re-authentication.
              </p>
              <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
                {redirectDelayLabel}
              </p>
            </div>
          </Card>
        </div>
      </>
    );
  }

  // Has both role and scope - show admin page
  return (
    <>
      <title>Admin | TrigpointingUK</title>
      <div className="max-w-6xl mx-auto">
        <Card className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-4">
            Admin Dashboard
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            Welcome to the admin area. More features coming soon.
          </p>
        </Card>

        <NeedsAttentionCard getAccessTokenSilently={getAccessTokenSilently} />

        <LogsNeedsAttentionCard getAccessTokenSilently={getAccessTokenSilently} />

        <MergeUsersCard getAccessTokenSilently={getAccessTokenSilently} />

        <LegacyMigrationCard getAccessTokenSilently={getAccessTokenSilently} />

        <DeleteAccountAdminCard getAccessTokenSilently={getAccessTokenSilently} />

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">
              Types &amp; Categories
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
              Manage trigpoint physical types and categories.
            </p>
            <a
              href="/admin/types"
              className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
            >
              Manage Types →
            </a>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">
              Trigpoint Statuses
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
              Manage trigpoint status values.
            </p>
            <a
              href="/admin/status"
              className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
            >
              Manage Statuses →
            </a>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">
              Condition Codes
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
              Manage trigpoint condition codes.
            </p>
            <a
              href="/admin/condition"
              className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
            >
              Manage Conditions →
            </a>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">
              Create Trigpoint
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
              Add a new trigpoint to the database.
            </p>
            <a
              href="/admin/trigs/new"
              className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
            >
              Create New Trigpoint →
            </a>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">
              OS Net Comparison
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
              Compare OS Net active GPS stations with database records.
            </p>
            <a
              href="/admin/osnet"
              className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
            >
              Compare Stations →
            </a>
          </Card>

          <Card>
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-3">
              Ireland Import
            </h2>
            <p className="text-gray-500 dark:text-gray-400 text-sm mb-4">
              Compare Ireland25 CSV data with Irish trigpoints in the database.
            </p>
            <a
              href="/admin/ireland-import"
              className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white font-medium px-4 py-2 rounded-md transition-colors"
            >
              Compare Irish Trigs →
            </a>
          </Card>
        </div>
      </div>
    </>
  );
}

