import { useCallback, useEffect, useMemo, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import toast from "react-hot-toast";

import AlertDialog from "../components/ui/AlertDialog";
import Button from "../components/ui/Button";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import Textarea from "../components/ui/Textarea";
import {
  type AccountDeletionMode,
  type AccountDeletionSummary,
  executeAccountDeletionMe,
  executeAdminAccountDeletion,
  fetchAccountDeletionSummaryMe,
  fetchAdminAccountDeletionSummary,
  postAccountDeletionEmailBackupMe,
  postAdminAccountDeletionEmailBackup,
} from "../lib/api";

const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_SCOPE = "api:admin";
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };

const MODE_OPTIONS: {
  id: AccountDeletionMode;
  title: string;
  body: string;
}[] = [
  {
    id: "anonymise_keep_photos",
    title: "Keep my logs and photos, anonymised",
    body: "Your visits and photos stay on TrigpointingUK under a placeholder name. Personal details and login are removed.",
  },
  {
    id: "anonymise_delete_photos",
    title: "Keep my logs anonymised, delete all photos",
    body: "Logs remain (anonymised); all of your photos are removed from the site and from storage.",
  },
  {
    id: "purge_all",
    title: "Delete all my logs and photos",
    body: "Everything you logged and every photo you uploaded is permanently removed. Your account record is deleted.",
  },
];

export default function AccountDeletion() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const {
    isAuthenticated,
    isLoading: isAuth0Loading,
    user: auth0User,
    getAccessTokenSilently,
    logout,
    loginWithRedirect,
  } = useAuth0();

  const userRoles =
    (auth0User?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  const adminTargetUserId = useMemo(() => {
    const raw = searchParams.get("userId")?.trim();
    if (!raw || !/^\d+$/.test(raw)) return null;
    return Number(raw);
  }, [searchParams]);

  const isAdminContext = adminTargetUserId != null;

  const [summary, setSummary] = useState<AccountDeletionSummary | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [loadingSummary, setLoadingSummary] = useState(false);
  const [mode, setMode] = useState<AccountDeletionMode>("anonymise_keep_photos");
  const [feedback, setFeedback] = useState("");
  const [emailBackupBusy, setEmailBackupBusy] = useState(false);
  const [executeBusy, setExecuteBusy] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const permissionDenied =
    isAdminContext && !hasAdminRole && isAuthenticated;

  const fetchToken = useCallback(
    async (forAdminApi: boolean) => {
      if (forAdminApi) {
        return getAccessTokenSilently({
          authorizationParams: { ...ADMIN_AUTH_PARAMS },
        });
      }
      return getAccessTokenSilently();
    },
    [getAccessTokenSilently]
  );

  useEffect(() => {
    if (!isAuthenticated || isAuth0Loading || permissionDenied) {
      return;
    }

    let cancelled = false;
    (async () => {
      setLoadingSummary(true);
      setLoadError(null);
      try {
        const token = await fetchToken(isAdminContext);
        const data = isAdminContext
          ? await fetchAdminAccountDeletionSummary(adminTargetUserId!, token)
          : await fetchAccountDeletionSummaryMe(token);
        if (!cancelled) {
          setSummary(data);
        }
      } catch (e) {
        if (!cancelled) {
          setLoadError(e instanceof Error ? e.message : "Failed to load account summary");
        }
      } finally {
        if (!cancelled) {
          setLoadingSummary(false);
        }
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [
    adminTargetUserId,
    fetchToken,
    isAdminContext,
    isAuthenticated,
    isAuth0Loading,
    permissionDenied,
  ]);

  const handleEmailBackup = async () => {
    if (!summary) return;
    setEmailBackupBusy(true);
    try {
      const token = await fetchToken(isAdminContext);
      if (isAdminContext) {
        await postAdminAccountDeletionEmailBackup(adminTargetUserId!, token);
      } else {
        await postAccountDeletionEmailBackupMe(token);
      }
      toast.success("If your account has a valid email, you should receive a zip archive shortly.");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Could not send the backup email");
    } finally {
      setEmailBackupBusy(false);
    }
  };

  const runExecute = async () => {
    if (!summary) return;
    setExecuteBusy(true);
    try {
      const token = await fetchToken(isAdminContext);
      const payload = {
        mode,
        feedback: feedback.trim() || null,
      };
      const result = isAdminContext
        ? await executeAdminAccountDeletion(adminTargetUserId!, payload, token)
        : await executeAccountDeletionMe(payload, token);

      if (isAdminContext) {
        toast.success("The member account has been processed.");
        navigate("/admin");
      } else {
        toast.success(
          result.user_row_deleted
            ? "Your account and content have been removed."
            : "Your account has been anonymised. You will be signed out."
        );
        await logout({
          logoutParams: {
            returnTo: window.location.origin,
          },
        });
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Account deletion failed");
    } finally {
      setExecuteBusy(false);
    }
  };

  const confirmDescription = useMemo(() => {
    const opt = MODE_OPTIONS.find((o) => o.id === mode);
    const base = opt?.body ?? "";
    return `${base}\n\nThis cannot be undone. Are you sure you wish to continue?`;
  }, [mode]);

  if (isAuth0Loading) {
    return (
      <div className="flex justify-center py-24">
        <Spinner size="lg" />
      </div>
    );
  }

  if (!isAuthenticated) {
    return (
      <>
        <title>Delete account | TrigpointingUK</title>
        <div className="max-w-xl mx-auto px-4 py-12">
          <Card>
            <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-3">
              Delete account
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Sign in to review your account and choose how your data should be handled.
            </p>
            <Button
              onClick={() =>
                loginWithRedirect({
                  appState: {
                    returnTo: `${window.location.pathname}${window.location.search}`,
                  },
                })
              }
            >
              Sign in
            </Button>
          </Card>
        </div>
      </>
    );
  }

  if (permissionDenied) {
    return (
      <>
        <title>Delete account | TrigpointingUK</title>
        <div className="max-w-xl mx-auto px-4 py-12">
          <Card>
            <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-3">
              Admin access required
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              Opening the deletion flow for another user requires the api-admin role.
            </p>
            <Link
              to="/account/delete"
              className="text-trig-green-600 dark:text-trig-green-400 font-medium hover:underline"
            >
              Go to your own account deletion page
            </Link>
          </Card>
        </div>
      </>
    );
  }

  return (
    <>
      <title>Delete account | TrigpointingUK</title>
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100">
            {isAdminContext ? "Delete or anonymise a member account" : "Delete your account"}
          </h1>
          <p className="mt-2 text-gray-600 dark:text-gray-400">
            {isAdminContext
              ? "You are signed in as an administrator. Confirm the member below, choose a data option, then proceed."
              : "We are sorry to see you go. You can choose what happens to your logs and photos, request a backup email, and leave brief feedback if you wish."}
          </p>
        </div>

        {loadingSummary && (
          <div className="flex justify-center py-12">
            <Spinner size="lg" />
          </div>
        )}

        {loadError && !loadingSummary && (
          <Card>
            <p className="text-red-600 dark:text-red-400">{loadError}</p>
          </Card>
        )}

        {summary && !loadingSummary && (
          <>
            <Card>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-4">
                Account overview
              </h2>
              <dl className="grid grid-cols-1 sm:grid-cols-2 gap-3 text-sm">
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Username</dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">{summary.username}</dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Full Name</dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">
                    {summary.full_name?.trim() ? summary.full_name : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Email on file</dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">
                    {summary.email?.trim() ? summary.email : "—"}
                  </dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Log count</dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">{summary.log_count}</dd>
                </div>
                <div>
                  <dt className="text-gray-500 dark:text-gray-400">Photo count</dt>
                  <dd className="font-medium text-gray-900 dark:text-gray-100">{summary.photo_count}</dd>
                </div>
              </dl>
            </Card>

            <div>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
                What should happen to your data?
              </h2>
              <div className="grid grid-cols-1 gap-4">
                {MODE_OPTIONS.map((opt) => {
                  const selected = mode === opt.id;
                  return (
                    <button
                      key={opt.id}
                      type="button"
                      onClick={() => setMode(opt.id)}
                      className={`text-left rounded-lg border-2 p-4 transition-shadow focus:outline-none focus-visible:ring-2 focus-visible:ring-trig-green-500 ${
                        selected
                          ? "border-trig-green-600 bg-trig-green-50 shadow-md ring-2 ring-trig-green-500/40 dark:border-trig-green-500 dark:bg-trig-green-950 dark:shadow-md dark:ring-2 dark:ring-trig-green-400/40"
                          : "border-gray-200 dark:border-gray-600 bg-white dark:bg-gray-800 hover:border-gray-300 dark:hover:border-gray-500"
                      }`}
                    >
                      <div
                        className={`font-semibold text-gray-900 ${
                          selected ? "dark:text-gray-50" : "dark:text-gray-100"
                        }`}
                      >
                        {opt.title}
                      </div>
                      <p
                        className={`mt-2 text-sm text-gray-600 ${
                          selected ? "dark:text-gray-200" : "dark:text-gray-300"
                        }`}
                      >
                        {opt.body}
                      </p>
                    </button>
                  );
                })}
              </div>
            </div>

            <Card>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                Backup email
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                Email a zip copy of your published logs to the address on this account.
              </p>
              <Button
                variant="secondary"
                onClick={handleEmailBackup}
                disabled={emailBackupBusy || !summary.email?.trim()}
              >
                {emailBackupBusy ? (
                  <span className="flex items-center gap-2">
                    <Spinner size="sm" />
                    Sending…
                  </span>
                ) : (
                  "Email me a copy of my logs before deletion"
                )}
              </Button>
              {!summary.email?.trim() && (
                <p className="mt-2 text-xs text-amber-700 dark:text-amber-400">
                  Add an email address in preferences before you can use this option.
                </p>
              )}
            </Card>

            <Card>
              <h2 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                Feedback (optional)
              </h2>
              <p className="text-sm text-gray-600 dark:text-gray-400 mb-3">
                If you would like to tell us why you are leaving, we read every message. This is sent
                only to the site team, not displayed publicly.
              </p>
              <Textarea
                value={feedback}
                onChange={(e) => setFeedback(e.target.value)}
                rows={4}
                placeholder="Optional comments…"
              />
            </Card>

            <div className="flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
              <Button
                variant="danger"
                onClick={() => setConfirmOpen(true)}
                disabled={executeBusy}
              >
                Permanently delete my account
              </Button>
              <Link
                to="/preferences"
                className="text-sm text-trig-green-600 dark:text-trig-green-400 hover:underline"
              >
                Back to preferences
              </Link>
            </div>
          </>
        )}
      </div>

      <AlertDialog
        open={confirmOpen}
        onOpenChange={setConfirmOpen}
        title="Are you sure?"
        description={confirmDescription}
        cancelText="Cancel"
        confirmText="Yes, proceed"
        variant="danger"
        onConfirm={() => {
          void runExecute();
        }}
        confirmDisabled={executeBusy}
      />
    </>
  );
}
