import LogCard from "./LogCard";
import Spinner from "../ui/Spinner";
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
      <div className="py-12">
        <Spinner size="lg" />
        <p className="text-center text-gray-600 dark:text-gray-400 mt-4">Loading logs...</p>
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

