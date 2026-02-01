/**
 * LocationChip - Filter chip for centre location
 */

import { MapPin } from "lucide-react";
import { FilterChip } from "../FilterChip";
import { LocationSearch } from "../../trigs/LocationSearch";

export interface LocationChipProps {
  locationName: string;
  lat: number | null;
  lon: number | null;
  onSelectLocation: (lat: number, lon: number, name: string) => void;
}

export function LocationChip({
  locationName,
  lat,
  lon,
  onSelectLocation,
}: LocationChipProps) {
  const hasLocation = lat !== null && lon !== null;
  const summary = hasLocation ? locationName || "Selected" : "Not set";

  return (
    <FilterChip
      label="Centre on"
      summary={summary}
      isActive={hasLocation}
      clearable={false}
      popoverWidth="lg"
      contentMaxHeightClass="max-h-none"
      icon={<MapPin className="w-3.5 h-3.5" />}
    >
      {({ close }) => (
        <div className="p-3">
          <LocationSearch
            onSelectLocation={onSelectLocation}
            defaultLocation={
              hasLocation
                ? { lat, lon, name: locationName }
                : undefined
            }
            autoFocus
            selectOnFocus
            inlineResults
            dropdownMaxHeightClass="max-h-[60vh]"
            dropdownClassName="bg-white dark:bg-gray-900 border border-trig-green-200 dark:border-gray-700 rounded-lg shadow-lg dark:shadow-gray-900/50"
            resultItemClassName="w-full px-4 py-3 text-left hover:bg-trig-green-50 dark:hover:bg-gray-800 transition-colors border-b border-trig-green-100 dark:border-gray-800 last:border-b-0"
            optimisticCurrentLocation
            onRequestClose={close}
            clearButtonMode="close"
            excludeTypes={["user"]}
          />
          {hasLocation && (
            <div className="mt-3 text-xs text-gray-500 dark:text-gray-400">
              <span className="font-mono">
                {lat?.toFixed(4)}, {lon?.toFixed(4)}
              </span>
            </div>
          )}
        </div>
      )}
    </FilterChip>
  );
}

export default LocationChip;

