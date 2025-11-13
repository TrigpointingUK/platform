import { Link } from "react-router-dom";
import { LocationSearchResult } from "../../../hooks/useSearchResults";

interface TrigpointResultItemProps {
  item: LocationSearchResult;
}

export function TrigpointResultItem({ item }: TrigpointResultItemProps) {
  return (
    <Link
      to={`/trigs/${item.id}`}
      className="block p-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors"
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">📍</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900">{item.name}</div>
          {item.description && (
            <div className="text-sm text-gray-500 mt-0.5">{item.description}</div>
          )}
          <div className="text-xs text-gray-400 mt-0.5 font-mono">
            {item.lat.toFixed(5)}, {item.lon.toFixed(5)}
          </div>
        </div>
      </div>
    </Link>
  );
}

