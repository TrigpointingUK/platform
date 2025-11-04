import { useState, useRef, useEffect, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useLocationSearch } from "../../hooks/useLocationSearch";

interface SearchResult {
  type: string;
  name: string;
  lat: number;
  lon: number;
  description?: string;
  id?: string;
}

interface GlobalSearchProps {
  className?: string;
  placeholder?: string;
  onSearch?: () => void;
}

function getResultTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    trigpoint: "📍",
    town: "🏘️",
    postcode: "📮",
    gridref: "🗺️",
    latlon: "🌐",
    user: "👤",
  };
  return icons[type] || "📍";
}

export function GlobalSearch({
  className = "",
  placeholder = "Search trigs, places, users...",
  onSearch,
}: GlobalSearchProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();

  const { data: results, isLoading } = useLocationSearch(query, isOpen);

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (
        dropdownRef.current &&
        !dropdownRef.current.contains(event.target as Node)
      ) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const handleSelectResult = (result: SearchResult) => {
    // Route based on result type
    if (result.type === "trigpoint" && result.id) {
      // Navigate to individual trigpoint page
      navigate(`/trig/${result.id}`);
    } else if (result.type === "user" && result.id) {
      // Navigate to user profile page
      navigate(`/profile/${result.id}`);
    } else {
      // Navigate to /trigs page with location pre-populated
      const params = new URLSearchParams({
        lat: result.lat.toString(),
        lon: result.lon.toString(),
        location: result.name,
      });
      navigate(`/trigs?${params.toString()}`);
    }

    setQuery("");
    setIsOpen(false);
    onSearch?.();
  };

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();

    if (query.trim()) {
      // If user hits enter without selecting, go to /trigs page with query as location name
      // Use a default UK center location
      const params = new URLSearchParams({
        lat: "54.0",
        lon: "-2.0",
        location: query.trim(),
      });
      navigate(`/trigs?${params.toString()}`);
      setQuery("");
      setIsOpen(false);
      onSearch?.();
    }
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <form onSubmit={handleSubmit}>
        <input
          ref={inputRef}
          type="search"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value);
            setIsOpen(true);
          }}
          onFocus={() => setIsOpen(true)}
          placeholder={placeholder}
          className="w-full px-4 py-2 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-trig-green-400"
          aria-label="Global search"
          aria-autocomplete="list"
          aria-controls="search-results"
          aria-expanded={isOpen}
        />
      </form>

      {/* Dropdown results */}
      {isOpen && query.length >= 2 && (
        <div
          id="search-results"
          className="absolute z-50 w-full min-w-[320px] mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-96 overflow-y-auto"
          role="listbox"
        >
          {isLoading && (
            <div className="px-4 py-3 text-gray-500 text-center">
              Searching...
            </div>
          )}

          {!isLoading && results && results.length === 0 && (
            <div className="px-4 py-3 text-gray-500 text-center">
              No results found
            </div>
          )}

          {!isLoading && results && results.length > 0 && (
            <ul>
              {results.map((result, index) => (
                <li key={`${result.type}-${result.name}-${index}`}>
                  <button
                    type="button"
                    onClick={() => handleSelectResult(result)}
                    className="w-full px-4 py-3 text-left hover:bg-gray-100 transition-colors border-b border-gray-100 last:border-b-0"
                    role="option"
                    aria-selected={false}
                  >
                    <div className="flex items-start gap-3">
                      <span className="text-2xl">
                        {getResultTypeIcon(result.type)}
                      </span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900">
                          {result.name}
                        </div>
                        {result.description && (
                          <div className="text-sm text-gray-500 mt-0.5">
                            {result.description}
                          </div>
                        )}
                        {result.type !== "user" && (
                          <div className="text-xs text-gray-400 mt-0.5 font-mono">
                            {result.lat.toFixed(5)}, {result.lon.toFixed(5)}
                          </div>
                        )}
                      </div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

