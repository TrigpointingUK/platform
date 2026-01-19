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
}: TilesetSelectorProps) {
  const [tileLayers] = useState<TileLayer[]>(getAvailableTileLayers());
  
  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newLayerId = event.target.value;
    if (persistSelection) {
      setPreferredTileLayer(newLayerId);
    }
    onChange(newLayerId);
  };
  
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
        {tileLayers.map((layer) => (
          <option key={layer.id} value={layer.id} className="bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100">
            {layer.name}
          </option>
        ))}
      </select>
    </div>
  );
}
