import { useCallback, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import Card from "../ui/Card";
import Spinner from "../ui/Spinner";
import { authenticatedGet, authenticatedDelete } from "../../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

interface ConnectedApp {
  grant_id: string;
  client_id: string;
  client_name: string | null;
  audience: string | null;
  scopes: string[];
}

interface ConnectedAppsResponse {
  apps: ConnectedApp[];
}

/** Human-readable labels for scopes shown on the consent screen. */
const SCOPE_LABELS: Record<string, string> = {
  openid: "Sign in",
  profile: "View your profile",
  offline_access: "Stay signed in",
  "api:write": "Create and update your logs and photos",
  "api:read-pii": "Read your email address and account details",
  "api:admin": "Administrative access",
};

export default function ConnectedAppsPanel() {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();
  const [revokingId, setRevokingId] = useState<string | null>(null);

  const {
    data,
    isLoading,
    error,
  } = useQuery<ConnectedAppsResponse>({
    queryKey: ["user", "connected-apps"],
    queryFn: () =>
      authenticatedGet<ConnectedAppsResponse>(
        `${API_BASE}/v1/users/me/connected-apps`,
        getAccessTokenSilently,
      ),
  });

  const handleRevoke = useCallback(
    async (app: ConnectedApp) => {
      const name = app.client_name || app.client_id;
      if (
        !window.confirm(
          `Revoke access for "${name}"? The application will no longer be able to access your account until you authorise it again.`,
        )
      ) {
        return;
      }
      setRevokingId(app.grant_id);
      try {
        await authenticatedDelete(
          `${API_BASE}/v1/users/me/connected-apps/${encodeURIComponent(app.grant_id)}`,
          getAccessTokenSilently,
        );
        queryClient.invalidateQueries({
          queryKey: ["user", "connected-apps"],
        });
        toast.success(`Access revoked for ${name}`);
      } catch (err) {
        console.error("Failed to revoke application access:", err);
        toast.error("Failed to revoke access");
      } finally {
        setRevokingId(null);
      }
    },
    [getAccessTokenSilently, queryClient],
  );

  const apps = data?.apps ?? [];

  return (
    <Card className="mb-6">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-2">
        Connected Applications
      </h2>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Applications you have authorised to access your TrigpointingUK
        account. Revoking access signs the application out; it can request
        access again the next time you use it.
      </p>

      {isLoading && (
        <div className="py-6 text-center">
          <Spinner size="md" />
        </div>
      )}

      {!isLoading && error != null && (
        <p className="text-sm text-red-600 dark:text-red-400">
          Failed to load connected applications
        </p>
      )}

      {!isLoading && !error && apps.length === 0 && (
        <p className="text-sm text-gray-500 dark:text-gray-400">
          You haven&apos;t authorised any applications.
        </p>
      )}

      {!isLoading && !error && apps.length > 0 && (
        <ul className="divide-y divide-gray-200 dark:divide-gray-700">
          {apps.map((app) => (
            <li
              key={app.grant_id}
              className="py-3 flex items-start justify-between gap-4"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-gray-900 dark:text-gray-100 truncate">
                  {app.client_name || app.client_id}
                </p>
                {app.scopes.length > 0 && (
                  <div className="mt-1 flex flex-wrap gap-1">
                    {app.scopes.map((scope) => (
                      <span
                        key={scope}
                        title={scope}
                        className="inline-block px-2 py-0.5 rounded-full text-xs bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300"
                      >
                        {SCOPE_LABELS[scope] ?? scope}
                      </span>
                    ))}
                  </div>
                )}
              </div>
              <button
                type="button"
                onClick={() => handleRevoke(app)}
                disabled={revokingId === app.grant_id}
                className="shrink-0 inline-flex items-center rounded-md border border-red-300 dark:border-red-800 px-3 py-1.5 text-sm font-medium text-red-700 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/30 disabled:opacity-50 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 dark:focus:ring-offset-gray-900"
              >
                {revokingId === app.grant_id ? "Revoking…" : "Revoke"}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
