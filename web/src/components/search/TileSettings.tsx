import { useState } from "react";

export interface TileVisibility {
  trigpoints: boolean;
  station_numbers: boolean;
  places: boolean;
  users: boolean;
  postcodes: boolean;
  coordinates: boolean;
  log_substring: boolean;
  log_regex: boolean;
}

interface TileSettingsProps {
  visibility: TileVisibility;
  onChange: (visibility: TileVisibility) => void;
  showEmptyTiles: boolean;
  onToggleShowEmpty: () => void;
}

const TILE_LABELS: Record<keyof TileVisibility, { label: string; icon: string }> = {
  trigpoints: { label: "Trigpoints", icon: "📍" },
  station_numbers: { label: "Station Numbers", icon: "🔢" },
  places: { label: "Places", icon: "🏘️" },
  users: { label: "Users", icon: "👤" },
  postcodes: { label: "Postcodes", icon: "📮" },
  coordinates: { label: "Coordinates", icon: "🌐" },
  log_substring: { label: "Log Text", icon: "📝" },
  log_regex: { label: "Log Regex", icon: "🔍" },
};

export function TileSettings({
  visibility,
  onChange,
  showEmptyTiles,
  onToggleShowEmpty,
}: TileSettingsProps) {
  const [isOpen, setIsOpen] = useState(false);

  const toggleTile = (key: keyof TileVisibility) => {
    onChange({
      ...visibility,
      [key]: !visibility[key],
    });
  };

  const resetToDefault = () => {
    onChange({
      trigpoints: true,
      station_numbers: true,
      places: true,
      users: true,
      postcodes: true,
      coordinates: true,
      log_substring: true,
      log_regex: true,
    });
  };

  return (
    <div className="relative">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-4 py-2 bg-white dark:bg-gray-800 border border-gray-300 dark:border-gray-600 rounded-md hover:bg-gray-50 dark:hover:bg-gray-700 transition-colors text-gray-900 dark:text-gray-100"
      >
        <span>⚙️</span>
        <span className="text-sm font-medium">Manage Tiles</span>
      </button>

      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-40"
            onClick={() => setIsOpen(false)}
          />

          {/* Dropdown Menu */}
          <div className="absolute right-0 mt-2 w-72 bg-white dark:bg-gray-800 rounded-lg shadow-lg dark:shadow-gray-900/50 border border-gray-200 dark:border-gray-700 z-50">
            <div className="p-4">
              <h3 className="font-semibold text-gray-900 dark:text-gray-100 mb-3">
                Tile Visibility
              </h3>

              {/* Tile Toggles */}
              <div className="space-y-2 mb-4">
                {Object.entries(TILE_LABELS).map(([key, { label, icon }]) => (
                  <label
                    key={key}
                    className="flex items-center gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={visibility[key as keyof TileVisibility]}
                      onChange={() => toggleTile(key as keyof TileVisibility)}
                      className="rounded border-gray-300 dark:border-gray-600 text-trig-green-600 focus:ring-trig-green-500 dark:bg-gray-700"
                    />
                    <span className="text-lg">{icon}</span>
                    <span className="text-sm text-gray-700 dark:text-gray-300">{label}</span>
                  </label>
                ))}
              </div>

              {/* Show Empty Tiles Toggle */}
              <div className="border-t border-gray-200 dark:border-gray-700 pt-3 mb-3">
                <label className="flex items-center gap-2 p-2 hover:bg-gray-50 dark:hover:bg-gray-700 rounded cursor-pointer">
                  <input
                    type="checkbox"
                    checked={showEmptyTiles}
                    onChange={onToggleShowEmpty}
                    className="rounded border-gray-300 dark:border-gray-600 text-trig-green-600 focus:ring-trig-green-500 dark:bg-gray-700"
                  />
                  <span className="text-sm text-gray-700 dark:text-gray-300">
                    Show tiles with no results
                  </span>
                </label>
              </div>

              {/* Reset Button */}
              <button
                onClick={resetToDefault}
                className="w-full px-3 py-2 text-sm bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-md transition-colors"
              >
                Reset to Defaults
              </button>
            </div>
          </div>
        </>
      )}
    </div>
  );
}

