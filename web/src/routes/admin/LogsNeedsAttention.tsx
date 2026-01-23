import { useCallback, useEffect, useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import { Link } from "react-router-dom";
import Layout from "../../components/layout/Layout";
import Card from "../../components/ui/Card";
import Spinner from "../../components/ui/Spinner";
import Button from "../../components/ui/Button";
import { useAdminAuth } from "../../hooks/useAdminAuth";
import { useConditionInfo } from "../../hooks/useConditionInfo";
import {
  fetchLogsNeedsAttention,
  deleteOrphanedLog,
  deleteDuplicateLog,
  LogNeedsAttentionItem,
  OrphanedLogItem,
  DuplicateLogItem,
  DuplicateLogGroupEntry,
} from "../../lib/api";

const ADMIN_AUTH_PARAMS = {
  audience: import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined,
  scope: "openid profile email api:write api:read-pii offline_access api:admin",
};

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
  getConditionInfo: (code: string | null | undefined) => { icon: string; label: string };
}

function LogAttentionCard({ log, onDelete, isDeleting, getConditionInfo }: LogCardProps) {
  const formattedDate = log.date
    ? new Date(log.date).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Unknown date";

  const isOrphaned = isOrphanedLog(log);
  const isDuplicate = isDuplicateLog(log);

  // Duplicate cards render multiple logs, each with their own confirm state.
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);
  const [showConfirmOrphaned, setShowConfirmOrphaned] = useState(false);

  const duplicateGroup = isDuplicate ? (log as DuplicateLogItem) : null;
  const tpCode = duplicateGroup?.trig_id
    ? `TP${String(duplicateGroup.trig_id).padStart(4, "0")}`
    : null;

  const formattedGroupDate = duplicateGroup?.date
    ? new Date(duplicateGroup.date).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : "Unknown date";

  const renderDuplicateLogRow = (entry: DuplicateLogGroupEntry) => {
    const entryConditionInfo = getConditionInfo(entry.condition);
    const entryTime =
      entry.time && entry.time !== "12:00:00" ? entry.time : null;

    return (
      <div key={entry.id} className="rounded-md border border-gray-200 dark:border-gray-600">
        <div className="flex items-start justify-between gap-4 p-3">
          <div className="flex-1 min-w-0">
            <Link to={`/logs/${entry.id}`} className="block">
              <div className="flex flex-wrap items-center gap-2 text-sm text-gray-700 dark:text-gray-300">
                <span className="font-semibold">Log #{entry.id}</span>
                <span className="text-gray-400">·</span>
                <img
                  src={`/icons/conditions/${entryConditionInfo.icon}`}
                  alt={entryConditionInfo.label}
                  title={entryConditionInfo.label}
                  className="w-4 h-4"
                />
                <span>{entryConditionInfo.label}</span>
                {entryTime && (
                  <>
                    <span className="text-gray-400">·</span>
                    <span>{entryTime}</span>
                  </>
                )}
              </div>
            </Link>

            {entry.comment && (
              <Link to={`/logs/${entry.id}`} className="block mt-2">
                <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md">
                  <p className="text-sm text-gray-700 dark:text-gray-300 whitespace-pre-wrap line-clamp-4">
                    {entry.comment}
                  </p>
                </div>
              </Link>
            )}
          </div>

          <div className="shrink-0">
            {confirmDeleteId !== entry.id ? (
              <Button
                onClick={(e) => {
                  e?.preventDefault();
                  e?.stopPropagation();
                  setConfirmDeleteId(entry.id);
                }}
                variant="danger"
                disabled={isDeleting}
              >
                Delete
              </Button>
            ) : (
              <div className="flex items-center gap-2">
                <span className="text-sm text-gray-600 dark:text-gray-400">Are you sure?</span>
                <Button
                  onClick={(e) => {
                    e?.preventDefault();
                    e?.stopPropagation();
                    onDelete(entry.id, "duplicate").finally(() => {
                      setConfirmDeleteId(null);
                    });
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
                    setConfirmDeleteId(null);
                  }}
                  variant="secondary"
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  return (
    <Card className="hover:shadow-lg transition-shadow">
      {/* Issue Type Banner */}
      <div className={`-mx-4 -mt-4 px-4 py-2 mb-3 rounded-t-md ${
        isOrphaned ? "bg-red-100 dark:bg-red-900/40 text-red-800 dark:text-red-300" : "bg-amber-100 dark:bg-amber-900/40 text-amber-800 dark:text-amber-300"
      }`}>
        <span className="font-medium text-sm">
          {isOrphaned
            ? "Log for deleted trigpoint"
            : `Duplicate logs (${(log as DuplicateLogItem).duplicate_count} copies)`}
        </span>
      </div>

      {isOrphaned ? (
        <>
          <Link to={`/logs/${log.id}`} className="block">
            <div className="flex items-start justify-between mb-3">
              <div className="flex-1">
                <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-1">
                  Log #{log.id}
                  {log.trig_id && (
                    <>
                      <span className="text-gray-400 mx-2">·</span>
                      <span className="font-normal text-red-600 dark:text-red-400">
                        Trig ID: {log.trig_id} (deleted)
                      </span>
                    </>
                  )}
                </h2>
                <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
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
                  {(() => {
                    const conditionInfo = getConditionInfo(log.condition);
                    return (
                      <>
                        <img
                          src={`/icons/conditions/${conditionInfo.icon}`}
                          alt={conditionInfo.label}
                          title={conditionInfo.label}
                          className="w-4 h-4"
                        />
                        <span>{conditionInfo.label}</span>
                      </>
                    );
                  })()}
                  <span className="text-gray-400">·</span>
                  <span>{formattedDate}</span>
                  {log.time && log.time !== "12:00:00" && (
                    <span className="text-gray-500 dark:text-gray-400">{log.time}</span>
                  )}
                </div>
              </div>
            </div>

            {log.comment && (
              <div className="bg-gray-50 dark:bg-gray-700 p-3 rounded-md mb-3">
                <p className="text-sm text-gray-700 dark:text-gray-300 line-clamp-3">{log.comment}</p>
              </div>
            )}

            <div className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 text-sm font-medium">
              View log details →
            </div>
          </Link>

          {/* Orphaned delete button */}
          <div className="mt-4 pt-4 border-t border-gray-200 dark:border-gray-600">
            {!showConfirmOrphaned ? (
              <Button
                onClick={(e) => {
                  e?.preventDefault();
                  e?.stopPropagation();
                  setShowConfirmOrphaned(true);
                }}
                variant="danger"
                disabled={isDeleting}
              >
                Delete log
              </Button>
            ) : (
              <div className="flex items-center gap-3">
                <span className="text-sm text-gray-600 dark:text-gray-400">Are you sure?</span>
                <Button
                  onClick={(e) => {
                    e?.preventDefault();
                    e?.stopPropagation();
                    onDelete(log.id, "orphaned").finally(() => {
                      setShowConfirmOrphaned(false);
                    });
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
                    setShowConfirmOrphaned(false);
                  }}
                  variant="secondary"
                  disabled={isDeleting}
                >
                  Cancel
                </Button>
              </div>
            )}
          </div>
        </>
      ) : (
        <>
          {/* Duplicate group header */}
          <div className="mb-3">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-1">
              {duplicateGroup?.trig_id ? (
                <Link
                  to={`/trigs/${duplicateGroup.trig_id}`}
                  className="hover:underline"
                >
                  {tpCode}
                  {duplicateGroup.trig_name ? ` - ${duplicateGroup.trig_name}` : ""}
                </Link>
              ) : (
                <span>Unknown trig</span>
              )}
            </h2>
            <div className="text-sm text-gray-600 dark:text-gray-400">
              by{" "}
              {duplicateGroup?.user_id ? (
                <Link
                  to={`/profile/${duplicateGroup.user_id}`}
                  className="text-trig-green-600 dark:text-trig-green-400 hover:underline font-semibold"
                >
                  {duplicateGroup.user_name ?? `User #${duplicateGroup.user_id}`}
                </Link>
              ) : (
                <span>{duplicateGroup?.user_name ?? "Unknown user"}</span>
              )}{" "}
              <span className="text-gray-400">·</span> {formattedGroupDate}
            </div>
          </div>

          <div className="grid grid-cols-1 gap-3">
            {duplicateGroup?.logs?.map(renderDuplicateLogRow)}
          </div>
        </>
      )}
    </Card>
  );
}

export default function LogsNeedsAttention() {
  const { getAccessTokenSilently } = useAuth0();
  const { hasAdminRole, hasAdminScope, isLoading: isAuthLoading } = useAdminAuth();
  const { getConditionInfo } = useConditionInfo();
  const [logs, setLogs] = useState<LogNeedsAttentionItem[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [skip, setSkip] = useState(0);
  const [total, setTotal] = useState(0);
  const [hasMore, setHasMore] = useState(false);
  const [deletingLogId, setDeletingLogId] = useState<number | null>(null);
  const limit = 50;

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
    if (!hasAdminRole || !hasAdminScope) {
      return;
    }

    fetchLogs();
  }, [hasAdminRole, hasAdminScope, fetchLogs]);

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

      // Remove the deleted log from the list:
      // - orphaned: remove the card
      // - duplicate: remove the log from its group; if group drops below 2 logs, remove the card
      setLogs((prev) => {
        if (type === "orphaned") {
          const next = prev.filter(
            (item) => !(item.issue_type === "orphaned" && item.id === logId)
          );
          if (next.length !== prev.length) setTotal((t) => Math.max(0, t - 1));
          return next;
        }

        let removedCard = false;
        const next: LogNeedsAttentionItem[] = [];

        for (const item of prev) {
          if (item.issue_type !== "duplicate") {
            next.push(item);
            continue;
          }

          const dup = item as DuplicateLogItem;
          const nextLogs = dup.logs.filter((l) => l.id !== logId);
          if (nextLogs.length === dup.logs.length) {
            next.push(item);
            continue;
          }

          if (nextLogs.length < 2) {
            removedCard = true;
            continue;
          }

          next.push({ ...dup, logs: nextLogs, duplicate_count: nextLogs.length });
        }

        if (removedCard) setTotal((t) => Math.max(0, t - 1));
        return next;
      });
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
              <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-4">
                Access Denied
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                You do not have permission to access this page.
              </p>
            </div>
          </Card>
        </div>
      </Layout>
    );
  }

  // Show loading state while checking admin scope
  if (isAuthLoading || !hasAdminScope) {
    return (
      <Layout>
        <title>Logs Needs Attention | TrigpointingUK</title>
        <div className="max-w-6xl mx-auto">
          <Card>
            <div className="flex flex-col items-center justify-center py-12">
              <Spinner size="lg" />
              <span className="mt-3 text-gray-600 dark:text-gray-400">
                {isAuthLoading ? "Verifying admin permissions..." : "Requesting elevated permissions..."}
              </span>
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
              <h1 className="text-3xl font-bold text-gray-800 dark:text-gray-100 mb-2">
                Logs Needing Attention
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                Manage orphaned and duplicate log entries
              </p>
            </div>
            <Link
              to="/admin"
              className="text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400 dark:hover:text-trig-green-300 font-medium"
            >
              ← Back to Admin
            </Link>
          </div>
        </Card>

        {isLoading && (
          <Card>
            <div className="flex items-center justify-center py-12">
              <Spinner size="lg" />
              <span className="ml-3 text-gray-600 dark:text-gray-400">Loading logs...</span>
            </div>
          </Card>
        )}

        {error && (
          <Card>
            <div className="text-center py-12">
              <p className="text-red-600 dark:text-red-400">Error: {error}</p>
              <Button onClick={fetchLogs} className="mt-4">
                Retry
              </Button>
            </div>
          </Card>
        )}

        {!isLoading && !error && logs.length === 0 && (
          <Card>
            <div className="text-center py-12">
              <p className="text-gray-600 dark:text-gray-400">
                No logs currently need attention.
              </p>
            </div>
          </Card>
        )}

        {!isLoading && !error && logs.length > 0 && (
          <>
            <div className="grid grid-cols-1 gap-4 mb-6">
              {logs.map((log) => (
                (() => {
                  const isDeletingCard =
                    log.issue_type === "orphaned"
                      ? deletingLogId === log.id
                      : (log as DuplicateLogItem).logs.some(
                          (l) => l.id === deletingLogId
                        );

                  return (
                <LogAttentionCard
                  key={
                    log.issue_type === "orphaned"
                      ? `orphaned-${log.id}`
                      : `duplicate-${(log as DuplicateLogItem).trig_id ?? "x"}-${(log as DuplicateLogItem).user_id ?? "x"}-${(log as DuplicateLogItem).date ?? "x"}`
                  }
                  log={log}
                  onDelete={handleDelete}
                  isDeleting={isDeletingCard}
                  getConditionInfo={getConditionInfo}
                />
                  );
                })()
              ))}
            </div>

            <Card>
              <div className="flex items-center justify-between">
                <div className="text-sm text-gray-600 dark:text-gray-400">
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
