import { useState } from "react";
import Card from "../ui/Card";
import Spinner from "../ui/Spinner";
import { useAreaTypes } from "../../hooks/useAreaTypes";
import { useUserAreaBreakdown } from "../../hooks/useUserAreaBreakdown";

interface AreaBreakdownProps {
  userId: number | string;
}

export default function AreaBreakdown({ userId }: AreaBreakdownProps) {
  const [selectedAreaTypeCode, setSelectedAreaTypeCode] = useState("county_1991");
  
  const { data: areaTypes, isLoading: isLoadingTypes } = useAreaTypes();
  const { 
    data: breakdown, 
    isLoading: isLoadingBreakdown,
    error: breakdownError 
  } = useUserAreaBreakdown(userId, selectedAreaTypeCode);

  const handleAreaTypeChange = (event: React.ChangeEvent<HTMLSelectElement>) => {
    setSelectedAreaTypeCode(event.target.value);
  };

  // Show spinner while loading area types
  if (isLoadingTypes) {
    return (
      <Card>
        <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
          Area
        </h3>
        <div className="flex justify-center py-4">
          <Spinner size="sm" />
        </div>
      </Card>
    );
  }

  return (
    <Card>
      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
        Area
      </h3>
      
      {/* Area Type Dropdown */}
      <div className="mb-3">
        <select
          value={selectedAreaTypeCode}
          onChange={handleAreaTypeChange}
          className="w-full px-3 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-md shadow-sm focus:outline-none focus:ring-1 focus:ring-trig-green-500 focus:border-trig-green-500 text-gray-900 dark:text-gray-100"
        >
          {areaTypes?.map((type) => (
            <option key={type.code} value={type.code}>
              {type.name}
            </option>
          ))}
        </select>
      </div>

      {/* Area Type Description */}
      {breakdown?.area_type?.description && (
        <div className="mb-3 p-2 bg-gray-50 dark:bg-gray-700/50 rounded text-xs text-gray-600 dark:text-gray-400">
          {breakdown.area_type.description}
        </div>
      )}

      {/* Loading state */}
      {isLoadingBreakdown && (
        <div className="flex justify-center py-4">
          <Spinner size="sm" />
        </div>
      )}

      {/* Error state */}
      {breakdownError && (
        <p className="text-red-600 dark:text-red-400 text-sm">
          Failed to load area breakdown
        </p>
      )}

      {/* Area counts list */}
      {!isLoadingBreakdown && !breakdownError && breakdown && (
        <div className="space-y-2 max-h-64 overflow-y-auto">
          {breakdown.items.length > 0 ? (
            breakdown.items.map((item) => (
              <div key={item.area_name} className="flex justify-between text-sm">
                <span className="text-gray-700 dark:text-gray-300 truncate pr-2">
                  {item.area_name}
                </span>
                <span className="font-medium text-trig-green-600 flex-shrink-0">
                  {item.count}
                </span>
              </div>
            ))
          ) : (
            <p className="text-gray-400 dark:text-gray-500 text-sm italic">
              No data for this area type
            </p>
          )}
        </div>
      )}
    </Card>
  );
}

