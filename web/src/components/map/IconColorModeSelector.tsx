import { useState } from "react";
import {
  type IconColorMode,
  setPreferredIconColorMode,
  ICON_LEGENDS,
} from "../../lib/mapIcons";

interface IconColorModeSelectorProps {
  value: IconColorMode;
  onChange: (mode: IconColorMode) => void;
  className?: string;
  showLegend?: boolean;
  isAuthenticated?: boolean;
}

/**
 * Toggle to switch between icon color modes (condition vs user log status)
 * 
 * Optionally shows a legend for the current mode.
 */
export default function IconColorModeSelector({
  value,
  onChange,
  className = "",
  showLegend = true,
  isAuthenticated = false,
}: IconColorModeSelectorProps) {
  const [isExpanded, setIsExpanded] = useState(false);
  
  const handleChange = (mode: IconColorMode) => {
    setPreferredIconColorMode(mode);
    onChange(mode);
  };
  
  const currentLegend = ICON_LEGENDS[value];
  
  return (
    <div className={`bg-white rounded-lg shadow-md p-3 ${className}`}>
      <div className="mb-2">
        <label className="block text-xs font-medium text-gray-700 mb-2">
          Icon Colors
        </label>
        
        <div className="flex gap-2">
          <button
            onClick={() => handleChange('condition')}
            className={`${isAuthenticated ? 'flex-1' : 'w-full'} px-3 py-1.5 text-sm rounded transition-colors ${
              value === 'condition'
                ? 'bg-trig-green-600 text-white'
                : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
            }`}
          >
            Condition
          </button>
          {isAuthenticated && (
            <button
              onClick={() => handleChange('userLog')}
              className={`flex-1 px-3 py-1.5 text-sm rounded transition-colors ${
                value === 'userLog'
                  ? 'bg-trig-green-600 text-white'
                  : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
              }`}
            >
              My Logs
            </button>
          )}
        </div>
      </div>
      
      {showLegend && (
        <div className="border-t border-gray-200 pt-2">
          <button
            onClick={() => setIsExpanded(!isExpanded)}
            className="w-full text-left text-xs font-medium text-gray-600 hover:text-gray-800 flex items-center justify-between"
          >
            <span>Legend</span>
            <span className="text-lg">{isExpanded ? '▼' : '▶'}</span>
          </button>
          
          {isExpanded && (
            <div className="mt-2 space-y-1">
              {currentLegend.map((item) => (
                <div key={item.color} className="flex items-center gap-2 text-xs">
                  <div
                    className="w-3 h-3 rounded-full border border-gray-300"
                    style={{
                      backgroundColor:
                        item.color === 'green' ? '#22c55e' :
                        item.color === 'yellow' ? '#eab308' :
                        item.color === 'red' ? '#ef4444' :
                        '#6b7280',
                    }}
                  />
                  <span className="text-gray-700">{item.label}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

