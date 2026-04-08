import { useState, useRef, useEffect, FormEvent } from "react";
import { useNavigate } from "react-router-dom";
import { useLocationSearch } from "../../hooks/useLocationSearch";
import { getTrigIconUrl } from "../../lib/searchIcons";

interface SearchResult {
  type: string;
  name: string;
  lat: number;
  lon: number;
  description?: string;
  id?: string;
  location?: string;
  category_code?: string;
}

interface GlobalSearchProps {
  className?: string;
  placeholder?: string;
  onSearch?: () => void;
}

const NON_TRIG_ICONS: Record<string, string> = {
  town: "🏘️",
  postcode: "📮",
  gridref: "🗺️",
  latlon: "🌐",
  user: "👤",
};

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
          className="w-full px-4 py-2 pr-14 rounded-md text-gray-900 dark:text-gray-100 bg-white dark:bg-gray-800 border border-gray-200 dark:border-gray-600 shadow-sm focus:outline-none focus:ring-2 focus:ring-trig-green-400 focus:border-trig-green-400"
          aria-label="Global search"
          aria-autocomplete="list"
          aria-controls="search-results"
          aria-expanded={isOpen}
        />
        <button
          type="submit"
          className="absolute right-1.5 top-1.5 bottom-1.5 px-3 bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 text-gray-600 dark:text-gray-300 rounded border border-gray-200 dark:border-gray-600 flex items-center justify-center transition-colors"
          aria-label="Search"
          title="Go to search page"
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
          className="absolute z-50 w-full min-w-[320px] mt-1 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg dark:shadow-gray-900/50 max-h-96 overflow-y-auto"
          role="listbox"
        >
          {isLoading && (
            <div className="px-4 py-3 text-gray-500 dark:text-gray-400 text-center">
              Searching...
            </div>
          )}

          {!isLoading && results && results.length === 0 && (
            <div className="px-4 py-3 text-gray-500 dark:text-gray-400 text-center">
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
                    className="w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-b-0"
                    role="option"
                    aria-selected={false}
                  >
                    <div className="flex items-start gap-3">
                      {result.type === "trigpoint" || result.type === "station_number" ? (
                        <img
                          src={getTrigIconUrl(result.category_code)}
                          alt=""
                          className="w-7 h-7 mt-0.5 flex-shrink-0"
                        />
                      ) : (
                        <span className="text-2xl">
                          {NON_TRIG_ICONS[result.type] || "📍"}
                        </span>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 dark:text-gray-100">
                          {result.name}
                        </div>
                        {result.description && (
                          <div className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                            {result.description}
                          </div>
                        )}
                        {result.location && (
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {result.location}
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

