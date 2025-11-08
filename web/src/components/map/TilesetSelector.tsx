import { useState } from "react";
import {
  getAvailableTileLayers,
  setPreferredTileLayer,
  type TileLayer,
} from "../../lib/mapConfig";

interface TilesetSelectorProps {
  value: string;
  onChange: (tileLayerId: string) => void;
  className?: string;
}

/**
 * Dropdown to select and switch between available tile layers
 * 
 * Persists the user's selection to localStorage.
 */
export default function TilesetSelector({
  value,
  onChange,
  className = "",
}: TilesetSelectorProps) {
  const [tileLayers] = useState<TileLayer[]>(getAvailableTileLayers());
  
  const handleChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    const newLayerId = event.target.value;
    setPreferredTileLayer(newLayerId);
    onChange(newLayerId);
  };
  
  return (
    <div className={`bg-white rounded-lg shadow-md p-2 ${className}`}>
      <label htmlFor="tileset-selector" className="block text-xs font-medium text-gray-700 mb-1">
        Map Layer
      </label>
      <select
        id="tileset-selector"
        value={value}
        onChange={handleChange}
        className="w-full px-2 py-1 text-sm border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-trig-green-500"
      >
        {tileLayers.map((layer) => (
          <option key={layer.id} value={layer.id}>
            {layer.name}
          </option>
        ))}
      </select>
    </div>
  );
}

