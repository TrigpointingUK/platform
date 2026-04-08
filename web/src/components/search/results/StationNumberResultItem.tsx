import { Link } from "react-router-dom";
import { LocationSearchResult } from "../../../hooks/useSearchResults";
import { getTrigIconUrl } from "../../../lib/searchIcons";

interface StationNumberResultItemProps {
  item: LocationSearchResult;
}

export function StationNumberResultItem({ item }: StationNumberResultItemProps) {
  return (
    <Link
      to={`/trigs/${item.id}`}
      className="block p-3 hover:bg-gray-50 dark:hover:bg-gray-700 border-b border-gray-100 dark:border-gray-700 last:border-b-0 transition-colors"
    >
      <div className="flex items-start gap-3">
        <img
          src={getTrigIconUrl(item.category_code)}
          alt=""
          className="w-7 h-7 mt-0.5 flex-shrink-0"
        />
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 dark:text-gray-100">{item.name}</div>
          {item.description && (
            <div className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{item.description}</div>
          )}
          {item.location && (
            <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">{item.location}</div>
          )}
        </div>
      </div>
    </Link>
  );
}

