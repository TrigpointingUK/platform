import { useState, useCallback, useMemo } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import toast from "react-hot-toast";
import Card from "../ui/Card";
import {
  updateUserProfile,
  type UserProfile,
} from "../../hooks/useUserProfile";
import { authenticatedGet, authenticatedPost } from "../../lib/api";

const API_BASE = import.meta.env.VITE_API_BASE as string;

const FREQUENCY_OPTIONS = [
  { value: "N", label: "Never" },
  { value: "Y", label: "Yearly" },
  { value: "M", label: "Monthly (or yearly if no recent activity)" },
  { value: "W", label: "Weekly (or monthly if no recent activity)" },
];

/** Shown in the UI only for api-admin (values still accepted by the API for any user). */
const ADMIN_EXTRA_FREQUENCY_OPTIONS = [
  { value: "D", label: "Daily" },
  {
    value: "B",
    label: "Daily (or weekly if no recent activity)",
  },
];

const FORMAT_OPTIONS = [
  { value: "C", label: "CSV only" },
  { value: "J", label: "CSV + JSON" },
  { value: "R", label: "CSV + HTML viewer" },
];

const STATUS_LABELS: Record<string, { text: string; className: string }> = {
  S: { text: "Sent", className: "text-green-700 dark:text-green-400" },
  F: { text: "Failed", className: "text-red-700 dark:text-red-400" },
  K: { text: "Skipped", className: "text-gray-500 dark:text-gray-400" },
};

const FORMAT_LABELS: Record<string, string> = {
  C: "CSV",
  J: "CSV+JSON",
  R: "CSV+viewer",
};

interface ArchiveRecord {
  id: number;
  status: string;
  frequency_at_send: string;
  format_at_send: string;
  log_count: number | null;
  file_size_bytes: number | null;
  error_message: string | null;
  created_at: string | null;
}

interface ArchiveHistoryResponse {
  items: ArchiveRecord[];
  pagination: {
    total: number;
    limit: number;
    offset: number;
    has_more: boolean;
  };
}

interface ArchivePreferencesPanelProps {
  user: UserProfile;
  hasAdminRole: boolean;
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function formatDate(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export default function ArchivePreferencesPanel({
  user,
  hasAdminRole,
}: ArchivePreferencesPanelProps) {
  const { getAccessTokenSilently } = useAuth0();
  const queryClient = useQueryClient();
  const [sending, setSending] = useState(false);

  const currentFrequency = user.prefs?.archive_frequency ?? "N";
  const currentFormat = user.prefs?.archive_format ?? "R";

  const frequencySelectOptions = useMemo(() => {
    if (hasAdminRole) {
      return [...FREQUENCY_OPTIONS, ...ADMIN_EXTRA_FREQUENCY_OPTIONS];
    }
    if (currentFrequency === "D" || currentFrequency === "B") {
      const keep = ADMIN_EXTRA_FREQUENCY_OPTIONS.filter(
        (o) => o.value === currentFrequency,
      );
      return [...FREQUENCY_OPTIONS, ...keep];
    }
    return FREQUENCY_OPTIONS;
  }, [hasAdminRole, currentFrequency]);

  const {
    data: history,
    isLoading: historyLoading,
  } = useQuery<ArchiveHistoryResponse>({
    queryKey: ["user", "archives"],
    queryFn: () =>
      authenticatedGet<ArchiveHistoryResponse>(
        `${API_BASE}/v1/users/me/archives?limit=10`,
        getAccessTokenSilently,
      ),
  });

  const handleFieldUpdate = useCallback(
    async (field: string, value: string) => {
      try {
        await updateUserProfile(
          { [field]: value } as unknown as Partial<UserProfile>,
          getAccessTokenSilently,
        );
        queryClient.invalidateQueries({ queryKey: ["user", "profile"] });
        toast.success("Preference updated");
      } catch {
        toast.error("Failed to update preference");
      }
    },
    [getAccessTokenSilently, queryClient],
  );

  const handleSendNow = useCallback(async () => {
    setSending(true);
    try {
      const result = await authenticatedPost<{
        status: string;
        log_count: number;
        zip_size_bytes: number;
      }>(
        `${API_BASE}/v1/users/me/archive`,
        {},
        getAccessTokenSilently,
      );
      toast.success(
        `Archive sent — ${result.log_count} logs, ${formatBytes(result.zip_size_bytes)}`,
      );
      queryClient.invalidateQueries({ queryKey: ["user", "archives"] });
    } catch (err) {
      const message =
        err instanceof Error ? err.message : "Failed to send archive";
      if (message.includes("429") || message.includes("rate")) {
        toast.error(
          message.toLowerCase().includes("format")
            ? "This format was sent recently — pick another format or try again tomorrow"
            : "Archive already sent recently — please try again later",
        );
      } else {
        toast.error(message);
      }
    } finally {
      setSending(false);
    }
  }, [getAccessTokenSilently, queryClient]);

  return (
    <Card className="mb-6" id="data-archive">
      <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-1">
        Data Archive Emails
      </h2>
      <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
        Receive periodic email archives of your published logs as a zip file.
        The HTML viewer option includes an interactive log browser with a JSON
        download button.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-6">
        {/* Frequency */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Frequency
          </label>
          <select
            value={currentFrequency}
            onChange={(e) =>
              handleFieldUpdate("archive_frequency", e.target.value)
            }
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-blue-500 focus:border-blue-500"
          >
            {frequencySelectOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>

        {/* Format */}
        <div>
          <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
            Format
          </label>
          <select
            value={currentFormat}
            onChange={(e) =>
              handleFieldUpdate("archive_format", e.target.value)
            }
            className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-md bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100 focus:ring-blue-500 focus:border-blue-500"
          >
            {FORMAT_OPTIONS.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Send Now */}
      <div className="flex items-center gap-3 mb-6">
        <button
          type="button"
          onClick={handleSendNow}
          disabled={sending}
          className="px-4 py-2 text-sm font-medium rounded-md bg-trig-green-600 text-white hover:bg-trig-green-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
        >
          {sending ? "Sending…" : "Send archive now"}
        </button>
        <span className="text-xs text-gray-500 dark:text-gray-400">
          Sends an immediate archive to your registered email (max one per format
          per day).
        </span>
      </div>

      {/* History */}
      <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
        Archive History
      </h3>
      {historyLoading ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 py-2">
          Loading history…
        </p>
      ) : !history?.items.length ? (
        <p className="text-sm text-gray-500 dark:text-gray-400 py-2">
          No archives sent yet.
        </p>
      ) : (
        <div className="overflow-x-auto -mx-4 px-4">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 dark:border-gray-700 text-left text-gray-500 dark:text-gray-400">
                <th className="pb-2 pr-3 font-medium">Date</th>
                <th className="pb-2 pr-3 font-medium">Status</th>
                <th className="pb-2 pr-3 font-medium">Format</th>
                <th className="pb-2 pr-3 font-medium text-right">Logs</th>
                <th className="pb-2 font-medium text-right">Size</th>
              </tr>
            </thead>
            <tbody className="text-gray-700 dark:text-gray-300">
              {history.items.map((a) => {
                const status = STATUS_LABELS[a.status] ?? {
                  text: a.status,
                  className: "",
                };
                return (
                  <tr
                    key={a.id}
                    className="border-b border-gray-100 dark:border-gray-700/50 last:border-0"
                  >
                    <td className="py-1.5 pr-3 whitespace-nowrap">
                      {a.created_at ? formatDate(a.created_at) : "—"}
                    </td>
                    <td className={`py-1.5 pr-3 ${status.className}`}>
                      {status.text}
                      {a.error_message && (
                        <span
                          className="ml-1 cursor-help"
                          title={a.error_message}
                        >
                          ⓘ
                        </span>
                      )}
                    </td>
                    <td className="py-1.5 pr-3">
                      {FORMAT_LABELS[a.format_at_send] ?? a.format_at_send}
                    </td>
                    <td className="py-1.5 pr-3 text-right tabular-nums">
                      {a.log_count ?? "—"}
                    </td>
                    <td className="py-1.5 text-right tabular-nums">
                      {a.file_size_bytes != null
                        ? formatBytes(a.file_size_bytes)
                        : "—"}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          {history.pagination.has_more && (
            <p className="text-xs text-gray-400 dark:text-gray-500 mt-2">
              Showing {history.items.length} of {history.pagination.total}{" "}
              archives
            </p>
          )}
        </div>
      )}
    </Card>
  );
}
