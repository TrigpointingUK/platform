import { useState, useRef, useEffect } from "react";
import { useLocationSearch } from "../../hooks/useLocationSearch";
import { useDeviceLocation } from "../../hooks/useDeviceLocation";

interface LocationSearchResult {
  type: string;
  name: string;
  lat: number;
  lon: number;
  description?: string;
}

interface LocationSearchProps {
  onSelectLocation: (lat: number, lon: number, name: string) => void;
  defaultLocation?: { lat: number; lon: number; name: string };
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
  defaultLocation,
}: LocationSearchProps) {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [selectedLocation, setSelectedLocation] = useState(defaultLocation);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  
  const { data: results, isLoading } = useLocationSearch(query, isOpen);
  const { position, isLoading: isGettingLocation, requestLocation } = useDeviceLocation();

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

  // Handle device location result
  useEffect(() => {
    if (position) {
      setSelectedLocation({
        lat: position.lat,
        lon: position.lon,
        name: "Current Location",
      });
      onSelectLocation(position.lat, position.lon, "Current Location");
      setIsOpen(false);
    }
  }, [position, onSelectLocation]);

  const handleSelectResult = (result: LocationSearchResult) => {
    setSelectedLocation({
      lat: result.lat,
      lon: result.lon,
      name: result.name,
    });
    onSelectLocation(result.lat, result.lon, result.name);
    setQuery("");
    setIsOpen(false);
  };

  const handleUseDeviceLocation = () => {
    requestLocation();
  };

  const handleClear = () => {
    setSelectedLocation(undefined);
    setQuery("");
    setIsOpen(false);
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
            onFocus={() => setIsOpen(true)}
            placeholder="Search location, postcode, grid ref..."
            className="w-full px-4 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
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
          {isGettingLocation ? "..." : "📍"}
        </button>
        
        {selectedLocation && (
          <button
            type="button"
            onClick={handleClear}
            className="px-4 py-2 bg-gray-300 text-gray-700 rounded-lg hover:bg-gray-400 transition-colors"
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
          className="absolute z-10 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-96 overflow-y-auto"
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
                      <span className="text-2xl">{getLocationTypeIcon(result.type)}</span>
                      <div className="flex-1 min-w-0">
                        <div className="font-medium text-gray-900">{result.name}</div>
                        {result.description && (
                          <div className="text-sm text-gray-500 mt-0.5">
                            {result.description}
                          </div>
                        )}
                        <div className="text-xs text-gray-400 mt-0.5 font-mono">
                          {result.lat.toFixed(5)}, {result.lon.toFixed(5)}
                        </div>
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

