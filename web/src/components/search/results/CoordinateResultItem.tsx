import { useNavigate } from "react-router-dom";
import { LocationSearchResult } from "../../../hooks/useSearchResults";

interface CoordinateResultItemProps {
  item: LocationSearchResult;
}

export function CoordinateResultItem({ item }: CoordinateResultItemProps) {
  const navigate = useNavigate();

  const handleClick = () => {
    // Navigate to /trigs page with location pre-populated
    const params = new URLSearchParams({
      lat: item.lat.toString(),
      lon: item.lon.toString(),
      location: item.name,
    });
    navigate(`/trigs?${params.toString()}`);
  };

  const icon = item.type === "latlon" ? "🌐" : "🗺️";

  return (
    <button
      onClick={handleClick}
      className="w-full block p-3 hover:bg-gray-50 border-b border-gray-100 last:border-b-0 transition-colors text-left"
    >
      <div className="flex items-start gap-3">
        <span className="text-2xl">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-gray-900 font-mono">{item.name}</div>
          {item.description && (
            <div className="text-sm text-gray-500 mt-0.5">{item.description}</div>
          )}
        </div>
      </div>
    </button>
  );
}

