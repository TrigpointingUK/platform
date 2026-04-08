import { useState, useRef, useEffect, useCallback } from "react";
import { Satellite } from "lucide-react";
import { useLocationSearch } from "../../hooks/useLocationSearch";
import { useDeviceLocation } from "../../hooks/useDeviceLocation";
import { getTrigIconUrl } from "../../lib/searchIcons";

interface LocationSearchResult {
  type: string;
  name: string;
  lat: number;
  lon: number;
  description?: string;
  location?: string;
  category_code?: string;
}

interface LocationSearchProps {
  onSelectLocation: (lat: number, lon: number, name: string) => void;
  onClear?: () => void;
  defaultLocation?: { lat: number; lon: number; name: string };
  autoFocus?: boolean;
  selectOnFocus?: boolean;
  inlineResults?: boolean;
  dropdownClassName?: string;
  dropdownMaxHeightClass?: string;
  resultItemClassName?: string;
  optimisticCurrentLocation?: boolean;
  onRequestClose?: () => void;
  clearButtonMode?: "clear" | "close";
  /** Types to exclude from search results (e.g., ["user"]) */
  excludeTypes?: string[];
}

function getLocationTypeIcon(type: string): string {
  const icons: Record<string, string> = {
    trigpoint: "📍",
    town: "🏘️",
    postcode: "📮",
    gridref: "🗺️",
    latlon: "🌐",
  };
  return icons[type] || "📍";
}

export function LocationSearch({
  onSelectLocation,
  onClear,
  defaultLocation,
  autoFocus = false,
  selectOnFocus = false,
  inlineResults = false,
  dropdownClassName = "bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-lg shadow-lg dark:shadow-gray-900/50",
  dropdownMaxHeightClass = "max-h-96",
  resultItemClassName = "w-full px-4 py-3 text-left hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors border-b border-gray-100 dark:border-gray-700 last:border-b-0",
  optimisticCurrentLocation = false,
  onRequestClose,
  clearButtonMode = "clear",
  excludeTypes,
}: LocationSearchProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState(defaultLocation);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const { data: rawResults, isLoading } = useLocationSearch(query, isOpen);
  
  // Filter out excluded types if specified
  const results = excludeTypes?.length 
    ? rawResults?.filter(r => !excludeTypes.includes(r.type))
    : rawResults;
  
  // Handle device location via callback (avoids useEffect sync)
  const handleDeviceLocationSuccess = useCallback((position: { lat: number; lon: number }) => {
    setSelectedLocation({
      lat: position.lat,
      lon: position.lon,
      name: "Current location",
    });
    onSelectLocation(position.lat, position.lon, "Current location");
    setIsOpen(false);
  }, [onSelectLocation]);
  
  const { position, isLoading: isGettingLocation, requestLocation } = useDeviceLocation({
    onSuccess: handleDeviceLocationSuccess,
  });

  // Close dropdown when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    if (autoFocus && inputRef.current) {
      inputRef.current.focus();
    }
  }, [autoFocus]);

  const handleSelectResult = (result: LocationSearchResult) => {
    setSelectedLocation({
      lat: result.lat,
      lon: result.lon,
      name: result.name,
    });
    onSelectLocation(result.lat, result.lon, result.name);
    setQuery("");
    setIsOpen(false);
    onRequestClose?.();
  };

  const handleUseDeviceLocation = () => {
    setIsOpen(false);
    if (optimisticCurrentLocation) {
      const fallbackLocation = position ?? defaultLocation;
      if (fallbackLocation) {
        setSelectedLocation({
          lat: fallbackLocation.lat,
          lon: fallbackLocation.lon,
          name: "Current location",
        });
        onSelectLocation(fallbackLocation.lat, fallbackLocation.lon, "Current location");
      }
    }
    onRequestClose?.();
    requestLocation();
  };

  const handleClear = () => {
    if (clearButtonMode === "close") {
      setIsOpen(false);
      onRequestClose?.();
      return;
    }
    setSelectedLocation(undefined);
    setQuery("");
    setIsOpen(false);
    onRequestClose?.();
    if (onClear) {
      onClear();
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      <div className="flex gap-2">
        <div className="flex-1">
          <input
            ref={inputRef}
            type="text"
            value={selectedLocation ? selectedLocation.name : query}
            onChange={(e) => {
              setQuery(e.target.value);
              setSelectedLocation(undefined);
              setIsOpen(true);
            }}
            onFocus={() => {
              setIsOpen(true);
              if (selectOnFocus && selectedLocation && inputRef.current) {
                requestAnimationFrame(() => inputRef.current?.select());
              }
            }}
            placeholder="Search location, postcode, grid ref..."
            className="w-full px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-gray-800 dark:text-gray-100 dark:placeholder-gray-400"
            aria-label="Location search"
            aria-autocomplete="list"
            aria-controls="location-results"
            aria-expanded={isOpen}
          />
        </div>
        
        <button
          type="button"
          onClick={handleUseDeviceLocation}
          disabled={isGettingLocation}
          className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          title="Use current device location"
          aria-label="Use current device location"
        >
          {isGettingLocation ? "..." : <Satellite className="w-4 h-4" aria-hidden="true" />}
        </button>
        
        {selectedLocation && (
          <button
            type="button"
            onClick={handleClear}
            className="px-4 py-2 bg-gray-300 dark:bg-gray-600 text-gray-700 dark:text-gray-200 rounded-lg hover:bg-gray-400 dark:hover:bg-gray-500 transition-colors"
            title="Clear location"
            aria-label="Clear location"
          >
            ✕
          </button>
        )}
      </div>

      {/* Dropdown results */}
      {isOpen && (query.length >= 2 || results) && (
        <div
          id="location-results"
          className={`${inlineResults ? "w-full mt-2" : "absolute z-10 w-full mt-1"} ${dropdownClassName} ${dropdownMaxHeightClass} overflow-y-auto`}
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
                    className={resultItemClassName}
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
                        <span className="text-2xl">{getLocationTypeIcon(result.type)}</span>
                      )}
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900 dark:text-gray-100">{result.name}</div>
                        {result.description && (
                          <div className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">
                            {result.description}
                          </div>
                        )}
                        {result.location ? (
                          <div className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                            {result.location}
                          </div>
                        ) : (
                          <div className="text-xs text-gray-400 dark:text-gray-500 mt-0.5 font-mono">
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

