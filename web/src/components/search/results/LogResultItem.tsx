import { Link } from "react-router-dom";
import { LogSearchResult } from "../../../hooks/useSearchResults";

interface LogResultItemProps {
  item: LogSearchResult;
}

export function LogResultItem({ item }: LogResultItemProps) {
  const dateStr = new Date(item.date).toLocaleDateString();

  return (
    <Link
      to={`/logs/${item.id}`}
      className="block p-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors"
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">📝</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 line-clamp-2">
            {item.comment_excerpt || item.comment}
          </div>
          <div className="flex flex-wrap gap-2 text-sm text-gray-500 mt-1">
            {item.trig_name && (
              <span className="font-medium">Trig: {item.trig_name}</span>
            )}
            {item.user_name && <span>by {item.user_name}</span>}
            <span className="text-gray-400">{dateStr}</span>
          </div>
        </div>
      </div>
    </Link>
  );
}

