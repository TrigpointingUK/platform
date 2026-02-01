/**
 * RadiusChip - Filter chip for distance/radius filter
 */

import { Circle } from "lucide-react";
import { FilterChip } from "../FilterChip";

// Preset distance options
const DISTANCE_PRESETS = [
  { value: 5, label: "5 km" },
  { value: 10, label: "10 km" },
  { value: 25, label: "25 km" },
  { value: 50, label: "50 km" },
  { value: 100, label: "100 km" },
  { value: 200, label: "200 km" },
  { value: 500, label: "500 km" },
  { value: null, label: "No limit" },
];

export interface RadiusChipProps {
  maxKm: number | null;
  onChange: (maxKm: number | null) => void;
  disabled?: boolean;
}

export function RadiusChip({
  maxKm,
  onChange,
  disabled = false,
}: RadiusChipProps) {
  const summary = maxKm === null ? "∞" : `${maxKm} km`;
  const isActive = maxKm !== null;

  return (
    <FilterChip
      label="Radius"
      summary={summary}
      isActive={isActive}
      clearable={isActive}
      onClear={() => onChange(null)}
      popoverWidth="sm"
      icon={<Circle className="w-3.5 h-3.5" />}
    >
      <div className="py-1">
        {DISTANCE_PRESETS.map((preset) => (
          <button
            key={preset.label}
            type="button"
            onClick={() => onChange(preset.value)}
            disabled={disabled}
            className={`
              w-full px-3 py-2 text-left text-sm
              hover:bg-gray-50 dark:hover:bg-gray-700/50 transition-colors
              disabled:opacity-50 disabled:cursor-not-allowed
              ${maxKm === preset.value 
                ? "bg-trig-green-50 dark:bg-trig-green-900/30 text-trig-green-700 dark:text-trig-green-300 font-medium" 
                : "text-gray-700 dark:text-gray-300"
              }
            `}
          >
            {preset.label}
          </button>
        ))}
      </div>
      
      {/* Custom input */}
      <div className="px-3 py-2 border-t border-gray-200 dark:border-gray-700">
        <label className="text-xs text-gray-500 dark:text-gray-400 mb-1 block">
          Custom distance
        </label>
        <div className="flex items-center gap-2">
          <input
            type="number"
            value={maxKm ?? ""}
            onChange={(e) => {
              const val = e.target.value;
              onChange(val === "" ? null : parseInt(val, 10));
            }}
            placeholder="km"
            min={1}
            max={2000}
            disabled={disabled}
            className="w-20 px-2 py-1 text-sm border border-gray-300 dark:border-gray-600 
                       rounded bg-white dark:bg-gray-700 text-gray-900 dark:text-gray-100
                       focus:ring-1 focus:ring-trig-green-500 focus:border-trig-green-500
                       disabled:opacity-50"
          />
          <span className="text-sm text-gray-500 dark:text-gray-400">km</span>
        </div>
      </div>
    </FilterChip>
  );
}

export default RadiusChip;

