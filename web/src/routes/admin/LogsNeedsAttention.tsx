import { useCallback, useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Link } from "react-router-dom";
import Layout from "../../components/layout/Layout";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import Button from "../../components/ui/Button";
import {
  fetchLogsNeedsAttention,
  deleteOrphanedLog,
  deleteDuplicateLog,
  LogNeedsAttentionItem,
  OrphanedLogItem,
  DuplicateLogItem,
} from "../../lib/api";

const ADMIN_AUTH_PARAMS = {
  audience: import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined,
  scope: "openid profile email api:write api:read-pii offline_access api:admin",
};

// Helper function to get condition icon and label
function getConditionInfo(code: string | null): { icon: string; label: string } {
  if (!code) return { icon: "c_unknown.png", label: "Unknown" };
  
  const conditions: Record<string, { icon: string; label: string }> = {
    Z: { icon: "c_unknown.png", label: "Not Logged" },
    N: { icon: "c_possiblymissing.png", label: "Couldn't Find" },
    G: { icon: "c_good.png", label: "Good" },
    S: { icon: "c_slightlydamaged.png", label: "Slightly Damaged" },
    C: { icon: "c_slightlydamaged.png", label: "Converted" },
    D: { icon: "c_damaged.png", label: "Damaged" },
    R: { icon: "c_toppled.png", label: "Remains" },
    T: { icon: "c_toppled.png", label: "Toppled" },
    M: { icon: "c_toppled.png", label: "Moved" },
    Q: { icon: "c_possiblymissing.png", label: "Possibly Missing" },
    X: { icon: "c_definitelymissing.png", label: "Destroyed" },
    V: { icon: "c_unreachablebutvisible.png", label: "Unreachable but Visible" },
    P: { icon: "c_unknown.png", label: "Inaccessible" },
    U: { icon: "c_unknown.png", label: "Unknown" },
    "-": { icon: "c_nolog.png", label: "Not Visited" },
  };
  return conditions[code] || { icon: "c_unknown.png", label: code };
}

function isOrphanedLog(log: LogNeedsAttentionItem): log is OrphanedLogItem {
  return log.issue_type === "orphaned";
}

function isDuplicateLog(log: LogNeedsAttentionItem): log is DuplicateLogItem {
  return log.issue_type === "duplicate";
}

interface LogCardProps {
  log: LogNeedsAttentionItem;
  onDelete: (logId: number, type: "orphaned" | "duplicate") => Promise<void>;
  isDeleting: boolean;
}

function LogAttentionCard({ log, onDelete, isDeleting }: LogCardProps) {
  const [showConfirm, setShowConfirm] = useState(false);
  const conditionInfo = getConditionInfo(log.condition);
  
  const formattedDate = log.date
    ? new Date(log.date).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Unknown date";

  const handleDelete = async () => {
    await onDelete(log.id, log.issue_type);
    setShowConfirm(false);
  };

  const isOrphaned = isOrphanedLog(log);
  const isDuplicate = isDuplicateLog(log);

  return (
    <Card className="hover:shadow-lg transition-shadow">
      {/* Issue Type Banner */}
      <div className={`-mx-4 -mt-4 px-4 py-2 mb-3 rounded-t-md ${
        isOrphaned ? "bg-red-100 text-red-800" : "bg-amber-100 text-amber-800"
      }`}>
        <span className="font-medium text-sm">
          {isOrphaned ? "Log for deleted trigpoint" : `Duplicate log (${(log as DuplicateLogItem).duplicate_count} copies)`}
        </span>
      </div>

      <Link
        to={`/logs/${log.id}`}
        className="block"
      >
        <div className="flex items-start justify-between mb-3">
          <div className="flex-1">
            <h2 className="text-xl font-semibold text-gray-800 mb-1">
              Log #{log.id}
              {isDuplicate && (log as DuplicateLogItem).trig_name && (
                <>
                  <span className="text-gray-400 mx-2">·</span>
                  <span className="font-normal text-gray-700">
                    {(log as DuplicateLogItem).trig_waypoint && `${(log as DuplicateLogItem).trig_waypoint} - `}
                    {(log as DuplicateLogItem).trig_name}
                  </span>
                </>
              )}
              {isOrphaned && log.trig_id && (
                <>
                  <span className="text-gray-400 mx-2">·</span>
                  <span className="font-normal text-red-600">
                    Trig ID: {log.trig_id} (deleted)
                  </span>
                </>
              )}
            </h2>
            <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
              {log.user_name ? (
                <span>
                  by{" "}
                  <Link
                    to={`/profile/${log.user_id}`}
                    className="text-trig-green-600 hover:underline font-semibold"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {log.user_name}
                  </Link>
                </span>
              ) : log.user_id ? (
                <span>
                  by{" "}
                  <Link
                    to={`/profile/${log.user_id}`}
                    className="text-trig-green-600 hover:underline font-semibold"
                    onClick={(e) => e.stopPropagation()}
                  >
                    User #{log.user_id}
                  </Link>
                </span>
              ) : null}
              <span className="text-gray-400">·</span>
              <img 
                src={`/icons/conditions/${conditionInfo.icon}`}
                alt={conditionInfo.label}
                title={conditionInfo.label}
                className="w-4 h-4"
              />
              <span>{conditionInfo.label}</span>
              <span className="text-gray-400">·</span>
              <span>{formattedDate}</span>
              {log.time && log.time !== "12:00:00" && (
                <span className="text-gray-500">{log.time}</span>
              )}
            </div>
          </div>
        </div>

        {log.comment && (
          <div className="bg-gray-50 p-3 rounded-md mb-3">
            <p className="text-sm text-gray-700 line-clamp-3">{log.comment}</p>
          </div>
        )}

        <div className="text-[#046935] hover:text-[#035228] text-sm font-medium">
          View log details →
        </div>
      </Link>

      {/* Delete Button */}
      <div className="mt-4 pt-4 border-t border-gray-200">
        {!showConfirm ? (
          <Button
            onClick={(e) => {
              e?.preventDefault();
              e?.stopPropagation();
              setShowConfirm(true);
            }}
            variant="danger"
            disabled={isDeleting}
          >
            {isOrphaned ? "Delete log" : "Delete duplicate"}
          </Button>
        ) : (
          <div className="flex items-center gap-3">
            <span className="text-sm text-gray-600">Are you sure?</span>
            <Button
              onClick={(e) => {
                e?.preventDefault();
                e?.stopPropagation();
                handleDelete();
              }}
              variant="danger"
              disabled={isDeleting}
            >
              {isDeleting ? (
                <span className="flex items-center gap-2">
                  <Spinner size="sm" />
                  <span>Deleting...</span>
                </span>
              ) : (
                "Yes, delete"
              )}
            </Button>
            <Button
              onClick={(e) => {
                e?.preventDefault();
                e?.stopPropagation();
                setShowConfirm(false);
              }}
              variant="secondary"
              disabled={isDeleting}
            >
              Cancel
            </Button>
          </div>
        )}
      </div>
    </Card>
  );
}

export default function LogsNeedsAttention() {
  const { getAccessTokenSilently, user } = useAuth0();
  const [logs, setLogs] = useState<LogNeedsAttentionItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skip, setSkip] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [deletingLogId, setDeletingLogId] = useState<number | null>(null);
  const limit = 50;

  // Check if user has admin role
  const userRoles = (user?.["https://trigpointing.uk/roles"] as string[]) || [];
  const hasAdminRole = userRoles.includes("api-admin");

  const fetchLogs = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const token = await getAccessTokenSilently({
        authorizationParams: { ...ADMIN_AUTH_PARAMS },
      });
      const data = await fetchLogsNeedsAttention({ skip, limit }, token);

      setLogs(data.items);
      setTotal(data.pagination.total);
      setHasMore(data.pagination.has_more);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load logs");
    } finally {
      setIsLoading(false);
    }
  }, [getAccessTokenSilently, skip]);

  useEffect(() => {
    if (!hasAdminRole) {
      return;
    }

    fetchLogs();
  }, [hasAdminRole, fetchLogs]);

  const handleDelete = useCallback(async (logId: number, type: "orphaned" | "duplicate") => {
    setDeletingLogId(logId);
    
    try {
      const token = await getAccessTokenSilently({
        authorizationParams: { ...ADMIN_AUTH_PARAMS },
      });

      if (type === "orphaned") {
        await deleteOrphanedLog(logId, token);
      } else {
        await deleteDuplicateLog(logId, token);
      }

      // Remove the deleted log from the list
      setLogs((prev) => prev.filter((log) => log.id !== logId));
      setTotal((prev) => prev - 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to delete log");
    } finally {
      setDeletingLogId(null);
    }
  }, [getAccessTokenSilently]);

  if (!hasAdminRole) {
    return (
      <Layout>
        <title>Logs Needs Attention | TrigpointingUK</title>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="text-center py-12">
              <h1 className="text-2xl font-bold text-gray-800 mb-4">
                Access Denied
              </h1>
              <p className="text-gray-600">
                You do not have permission to access this page.
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  const handlePrevious = () => {
    setSkip(Math.max(0, skip - limit));
  };

  const handleNext = () => {
    setSkip(skip + limit);
  };

  return (
    <Layout>
      <title>Logs Needs Attention | TrigpointingUK</title>
      <div className="max-w-6xl mx-auto">
        <Card className="mb-6">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">
                Logs Needing Attention
              </h1>
              <p className="text-gray-600">
                Manage orphaned and duplicate log entries
              </p>
            </div>
            <Link
              to="/admin"
              className="text-[#046935] hover:text-[#035228] font-medium"
            >
              ← Back to Admin
            </Link>
          </div>
        </Card>

        {isLoading && (
          <Card>
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
              <span className="ml-3 text-gray-600">Loading logs...</span>
            </div>
          </Card>
        )}

        {error && (
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600">Error: {error}</p>
              <Button onClick={fetchLogs} className="mt-4">
                Retry
              </Button>
            </div>
          </Card>
        )}

        {!isLoading && !error && logs.length === 0 && (
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-600">
                No logs currently need attention.
              </p>
            </div>
          </Card>
        )}

        {!isLoading && !error && logs.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-4 mb-6">
              {logs.map((log) => (
                <LogAttentionCard
                  key={log.id}
                  log={log}
                  onDelete={handleDelete}
                  isDeleting={deletingLogId === log.id}
                />
              ))}
            </div>

            <Card>
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600">
                  Showing {skip + 1} - {Math.min(skip + limit, total)} of {total}{" "}
                  logs
                </div>
                <div className="flex gap-2">
                  <Button
                    onClick={handlePrevious}
                    disabled={skip === 0}
                    variant="secondary"
                  >
                    ← Previous
                  </Button>
                  <Button
                    onClick={handleNext}
                    disabled={!hasMore}
                    variant="secondary"
                  >
                    Next →
                  </Button>
                </div>
              </div>
            </Card>
          </>
        )}
      </div>
    </Layout>
  );
}
