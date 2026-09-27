import { useState } from "react";
import {
  getAvailableTileLayers,
  setPreferredTileLayer,
  type TileLayer,
} from "../../lib/mapConfig";
import type { TilesetSelectorProps } from "./types";

/**
 * Dropdown to select and switch between available tile layers
 * 
 * Persists the user's selection to localStorage unless persistSelection is false.
 */
export default function TilesetSelector({
  value,
  onChange,
  className = "",
  persistSelection = true,
  compactOnMobile = false,
}: TilesetSelectorProps) {
  const [tileLayers] = useState<TileLayer[]>(getAvailableTileLayers());
  
  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newLayerId = event.target.value;
    if (persistSelection) {
      setPreferredTileLayer(newLayerId);
    }
    onChange(newLayerId);
  };
  
  const options = tileLayers.map((layer) => (
    <option key={layer.id} value={layer.id} className="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
      {layer.name}
    </option>
  ));

  if (compactOnMobile) {
    return (
      <div className={className}>
        {/* Phones: the icon is the button; the invisible select over it opens the native picker */}
        <div className="lg:hidden relative w-10 h-10 bg-white dark:bg-gray-800 rounded-lg shadow-md dark:shadow-gray-900/50 flex items-center justify-center text-gray-700 dark:text-gray-200">
          <LayersIcon />
          <select
            aria-label="Map layer"
            value={value}
            onChange={handleChange}
            className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          >
            {options}
          </select>
        </div>
        <div className="hidden lg:block bg-white dark:bg-gray-800 rounded-lg shadow-md dark:shadow-gray-900/50 p-2">
          <label htmlFor="tileset-selector" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
            Map Layer
          </label>
          <select
            id="tileset-selector"
            value={value}
            onChange={handleChange}
            className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-2 focus:ring-trig-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
          >
            {options}
          </select>
        </div>
      </div>
    );
  }

  return (
    <div className={`bg-white dark:bg-gray-800 rounded-lg shadow-md dark:shadow-gray-900/50 p-2 ${className}`}>
      <label htmlFor="tileset-selector" className="block text-xs font-medium text-gray-700 dark:text-gray-300 mb-1">
        Map Layer
      </label>
      <select
        id="tileset-selector"
        value={value}
        onChange={handleChange}
        className="w-full px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 rounded focus:outline-none focus:ring-2 focus:ring-trig-green-500 bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100"
      >
        {options}
      </select>
    </div>
  );
}

/** Google Maps-style layers icon: a diamond with a chevron beneath */
function LayersIcon() {
  return (
    <svg
      viewBox="0 0 24 24"
      className="w-6 h-6"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M12 3 3 9.5 12 16l9-6.5z" fill="currentColor" fillOpacity={0.15} />
      <path d="m3 14.5 9 6.5 9-6.5" />
    </svg>
  );
}
