import LogCard from "./LogCard";
import { Photo } from "../../lib/api";

interface Log {
  id: number;
  trig_id: number;
  user_id: number;
  trig_name?: string;
  user_name?: string;
  date: string;
  time: string;
  condition: string;
  comment: string;
  score: number;
  photos?: Photo[];
}

interface LogListProps {
  logs: Log[];
  isLoading?: boolean;
  emptyMessage?: string;
  currentUserId?: number;
  showTrigCondition?: boolean;
  /** Show the trig header line (waypoint, name, type). Default: true */
  showTrigInfo?: boolean;
  /** Show admin OG preview link on every card */
  isAdmin?: boolean;
}

export default function LogList({
  logs,
  isLoading = false,
  emptyMessage = "No logs found",
  currentUserId,
  showTrigCondition = false,
  showTrigInfo = true,
  isAdmin = false,
}: LogListProps) {
  if (isLoading) {
    return (
      <div className="space-y-4">
        {[1, 2, 3].map((i) => (
          <div
            key={i}
            className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700 p-4 animate-pulse"
          >
            <div className="flex items-center gap-3 mb-3">
              <div className="w-20 h-5 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="w-32 h-5 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
            <div className="space-y-2">
              <div className="w-3/4 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="w-1/2 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
            <div className="flex items-center gap-2 mt-3">
              <div className="w-6 h-6 bg-gray-200 dark:bg-gray-700 rounded-full" />
              <div className="w-24 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
              <div className="w-20 h-4 bg-gray-200 dark:bg-gray-700 rounded" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (!logs || logs.length === 0) {
    return (
      <div className="text-center py-12 text-gray-500 dark:text-gray-400">
        <p>{emptyMessage}</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {logs.map((log) => (
        <LogCard
          key={log.id}
          log={log}
          isCurrentUserLog={currentUserId !== undefined && log.user_id === currentUserId}
          showTrigCondition={showTrigCondition}
          showTrigInfo={showTrigInfo}
          isAdmin={isAdmin}
        />
      ))}
    </div>
  );
}

