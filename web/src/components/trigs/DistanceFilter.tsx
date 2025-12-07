import { useState, useCallback, useEffect, useRef } from "react";

interface DistanceFilterProps {
  /** Current max distance in km, or null for no limit */
  value: number | null;
  /** Called when the distance changes (debounced) */
  onChange: (maxKm: number | null) => void;
  /** Whether the filter is disabled (e.g., no location selected) */
  disabled?: boolean;
}

// Detent values in km for snapping
const DETENTS = [1, 2, 5, 10, 20, 50, 100, 200, 500, 1000, 2000];

// Snap threshold as percentage of slider range
const SNAP_THRESHOLD = 3;

// Debounce delay in milliseconds
const DEBOUNCE_MS = 1000;

// Logarithmic scale factor: 100 / log10(2000) ≈ 30.29
const LOG_SCALE_FACTOR = 100 / Math.log10(2000);

// Convert slider position (0-100) to distance in km (logarithmic: 1-2000)
function positionToDistance(pos: number): number {
  // pos 0 -> 1km, pos ~30 -> 10km, pos ~61 -> 100km, pos ~91 -> 1000km, pos 100 -> 2000km
  return Math.round(Math.pow(10, pos / LOG_SCALE_FACTOR));
}

// Convert distance in km to slider position (0-100)
function distanceToPosition(km: number): number {
  return Math.log10(km) * LOG_SCALE_FACTOR;
}

// Find the nearest detent value and its position
function findNearestDetent(pos: number): { distance: number; position: number } | null {
  for (const detent of DETENTS) {
    const detentPos = distanceToPosition(detent);
    if (Math.abs(pos - detentPos) <= SNAP_THRESHOLD) {
      return { distance: detent, position: detentPos };
    }
  }
  return null;
}

// Format distance for display
function formatDistance(km: number): string {
  return `${km} km`;
}

// Convert position to value (with detent snapping)
function positionToValue(pos: number): number | null {
  if (pos >= 99.5) {
    return null; // No limit
  }
  const nearestDetent = findNearestDetent(pos);
  if (nearestDetent) {
    return nearestDetent.distance;
  }
  return positionToDistance(pos);
}

export function DistanceFilter({
  value,
  onChange,
  disabled = false,
}: DistanceFilterProps) {
  // Internal slider position (0-100), 100 means "no limit"
  const [sliderPosition, setSliderPosition] = useState<number>(() => {
    if (value === null) return 100;
    return distanceToPosition(value);
  });

  // Pending value waiting to be committed after debounce
  const [pendingValue, setPendingValue] = useState<number | null>(value);

  // Whether we have a pending change (for visual feedback)
  const [isPending, setIsPending] = useState(false);

  // Debounce timer ref
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Track the committed value to detect external changes
  const committedValueRef = useRef<number | null>(value);

  // Sync slider position when value changes externally (e.g., URL params on page load or clear filters)
  useEffect(() => {
    // Only sync if this is an external change (not from our own onChange)
    if (value !== committedValueRef.current) {
      committedValueRef.current = value;
      /* eslint-disable react-hooks/set-state-in-effect -- Syncing internal state with external controlled value */
      setPendingValue(value);
      setIsPending(false);

      // Cancel any pending debounce
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
        debounceTimerRef.current = null;
      }

      if (value === null) {
        setSliderPosition(100);
      } else {
        setSliderPosition(distanceToPosition(value));
      }
      /* eslint-enable react-hooks/set-state-in-effect */
    }
  }, [value]);

  // Cleanup timer on unmount
  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, []);

  const scheduleChange = useCallback(
    (newValue: number | null) => {
      // Update pending value immediately (for display)
      setPendingValue(newValue);
      setIsPending(true);

      // Cancel any existing timer
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }

      // Schedule the actual onChange call
      debounceTimerRef.current = setTimeout(() => {
        debounceTimerRef.current = null;
        setIsPending(false);
        committedValueRef.current = newValue;
        onChange(newValue);
      }, DEBOUNCE_MS);
    },
    [onChange]
  );

  const handleSliderChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      const pos = parseFloat(e.target.value);
      setSliderPosition(pos);

      const newValue = positionToValue(pos);
      scheduleChange(newValue);
    },
    [scheduleChange]
  );

  const handleNoLimitToggle = useCallback(() => {
    const currentDisplayValue = pendingValue;
    if (currentDisplayValue === null) {
      // Switch to a sensible default (100km)
      setSliderPosition(distanceToPosition(100));
      scheduleChange(100);
    } else {
      setSliderPosition(100);
      scheduleChange(null);
    }
  }, [pendingValue, scheduleChange]);

  // Use pending value for display (shows what will be applied)
  const displayValue =
    pendingValue === null ? "∞" : formatDistance(pendingValue);

  const isNoLimit = pendingValue === null;

  return (
    <div className={`${disabled ? "opacity-50" : ""}`}>
      <div className="flex items-center gap-3">
        {/* Min label */}
        <span className="text-xs text-gray-500 w-6 text-right">1</span>

        {/* Slider with floating label */}
        <div className="flex-1 min-w-[200px] relative pt-7 pb-1">
          {/* Floating value label above thumb */}
          <div
            className="absolute top-0 pointer-events-none"
            style={{
              left: `${sliderPosition}%`,
              transform: "translateX(-50%)",
            }}
          >
            <span
              className={`
                inline-block px-2 py-0.5 text-xs font-semibold rounded-md
                whitespace-nowrap shadow-sm
                transition-colors
                ${isNoLimit ? "bg-gray-600 text-white" : "bg-blue-600 text-white"}
                ${isPending ? "animate-pulse" : ""}
              `}
            >
              {displayValue}
            </span>
            {/* Triangle pointer */}
            <div
              className={`
                absolute left-1/2 -translate-x-1/2 top-full
                w-0 h-0
                border-l-[5px] border-l-transparent
                border-r-[5px] border-r-transparent
                border-t-[5px]
                ${isNoLimit ? "border-t-gray-600" : "border-t-blue-600"}
              `}
            />
          </div>

          {/* Slider input */}
          <input
            type="range"
            min="0"
            max="100"
            step="0.5"
            value={sliderPosition}
            onChange={handleSliderChange}
            disabled={disabled}
            className={`
              w-full h-2 rounded-lg appearance-none cursor-pointer
              bg-gray-200
              [&::-webkit-slider-thumb]:appearance-none
              [&::-webkit-slider-thumb]:w-4
              [&::-webkit-slider-thumb]:h-4
              [&::-webkit-slider-thumb]:rounded-full
              [&::-webkit-slider-thumb]:bg-blue-600
              [&::-webkit-slider-thumb]:cursor-pointer
              [&::-webkit-slider-thumb]:shadow-md
              [&::-webkit-slider-thumb]:transition-transform
              [&::-webkit-slider-thumb]:hover:scale-110
              [&::-moz-range-thumb]:w-4
              [&::-moz-range-thumb]:h-4
              [&::-moz-range-thumb]:rounded-full
              [&::-moz-range-thumb]:bg-blue-600
              [&::-moz-range-thumb]:border-0
              [&::-moz-range-thumb]:cursor-pointer
              [&::-moz-range-thumb]:shadow-md
              disabled:cursor-not-allowed
              disabled:[&::-webkit-slider-thumb]:bg-gray-400
              disabled:[&::-moz-range-thumb]:bg-gray-400
            `}
            aria-label="Maximum distance filter"
            aria-valuetext={pendingValue === null ? "No limit" : `${pendingValue} km`}
          />

          {/* Detent markers */}
          <div className="absolute top-10 left-0 right-0 pointer-events-none">
            {DETENTS.filter((d) => d >= 10 && d <= 1000).map((detent) => {
              const pos = distanceToPosition(detent);
              return (
                <div
                  key={detent}
                  className="absolute w-0.5 h-1.5 bg-gray-400 rounded-full"
                  style={{ left: `${pos}%`, transform: "translateX(-50%)" }}
                  title={`${detent} km`}
                />
              );
            })}
          </div>
        </div>

        {/* Max label */}
        <span className="text-xs text-gray-500 w-6">2k</span>

        {/* No limit toggle button */}
        <button
          type="button"
          onClick={handleNoLimitToggle}
          disabled={disabled}
          className={`
            px-2 py-1 text-xs font-medium rounded transition-colors
            ${isNoLimit
              ? "bg-blue-600 text-white hover:bg-blue-700"
              : "bg-gray-200 text-gray-600 hover:bg-gray-300"
            }
            disabled:opacity-50 disabled:cursor-not-allowed
          `}
          title={isNoLimit ? "Set a distance limit" : "Remove distance limit"}
        >
          {isNoLimit ? "∞" : "×"}
        </button>
      </div>
    </div>
  );
}

export default DistanceFilter;
