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
    station_number: "🔢",
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
    if ((result.type === "trigpoint" || result.type === "station_number") && result.id) {
      // Navigate to individual trigpoint page
      navigate(`/trigs/${result.id}`);
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

    // Navigate to dedicated search page (even if empty)
    const searchQuery = query.trim();
    navigate(`/search${searchQuery ? `?q=${encodeURIComponent(searchQuery)}` : ''}`);
    setQuery("");
    setIsOpen(false);
    onSearch?.();
  };

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <form onSubmit={handleSubmit} className="relative">
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
          className="w-full px-4 py-2 pr-10 rounded-md text-gray-900 focus:outline-none focus:ring-2 focus:ring-trig-green-400"
          aria-label="Global search"
          aria-autocomplete="list"
          aria-controls="search-results"
          aria-expanded={isOpen}
        />
        <button
          type="submit"
          className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-trig-green-600 transition-colors"
          aria-label="Search"
        >
          <svg
            className="w-5 h-5"
            fill="none"
            strokeLinecap="round"
            strokeLinejoin="round"
            strokeWidth="2"
            viewBox="0 0 24 24"
            stroke="currentColor"
          >
            <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </button>
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

