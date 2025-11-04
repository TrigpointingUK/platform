import { useState } from "react";

interface ScoreSelectorProps {
  value: number;
  onChange: (value: number) => void;
  required?: boolean;
}

export default function ScoreSelector({
  value,
  onChange,
  required = false,
}: ScoreSelectorProps) {
  const [hoverValue, setHoverValue] = useState<number | null>(null);
  const [showDropdown, setShowDropdown] = useState(false);

  // Convert 0-10 score to 0-5 stars (divide by 2)
  const starValue = value / 2;
  const displayValue = hoverValue !== null ? hoverValue / 2 : starValue;

  const handleStarClick = (starIndex: number, event: React.MouseEvent<HTMLButtonElement>) => {
    // Get click position within the star to determine full vs half
    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();
    const clickX = event.clientX - rect.left;
    const starWidth = rect.width;
    
    // If clicked on left half, use half star (subtract 0.5)
    // If clicked on right half, use full star
    const isLeftHalf = clickX < starWidth / 2;
    const scoreValue = isLeftHalf ? (starIndex * 2) - 1 : starIndex * 2;
    
    onChange(scoreValue);
  };

  const handleStarHover = (starIndex: number, event: React.MouseEvent<HTMLButtonElement>) => {
    // Get hover position within the star
    const button = event.currentTarget;
    const rect = button.getBoundingClientRect();
    const hoverX = event.clientX - rect.left;
    const starWidth = rect.width;
    
    const isLeftHalf = hoverX < starWidth / 2;
    const scoreValue = isLeftHalf ? (starIndex * 2) - 1 : starIndex * 2;
    
    setHoverValue(scoreValue);
  };

  const handleMouseLeave = () => {
    setHoverValue(null);
  };

  const handleDropdownSelect = (score: number) => {
    onChange(score);
    setShowDropdown(false);
  };

  return (
    <div>
      <label className="block text-sm font-semibold text-gray-700 mb-1">
        Score {required && <span className="text-red-500">*</span>}
      </label>

      <div className="flex items-center gap-3">
        {/* Interactive Stars */}
        <div
          className="flex items-center gap-1"
          onMouseLeave={handleMouseLeave}
        >
          {[1, 2, 3, 4, 5].map((starIndex) => {
            const isFilled = displayValue >= starIndex;
            const isHalfFilled = displayValue >= starIndex - 0.5 && displayValue < starIndex;

            return (
              <button
                key={starIndex}
                type="button"
                onClick={(e) => handleStarClick(starIndex, e)}
                onMouseMove={(e) => handleStarHover(starIndex, e)}
                className="relative text-2xl focus:outline-none transition-transform hover:scale-110 cursor-pointer"
                title={`Click left for ${(starIndex * 2) - 1}/10, right for ${starIndex * 2}/10`}
              >
                {isFilled ? (
                  <span className="text-yellow-400">★</span>
                ) : isHalfFilled ? (
                  <span className="relative inline-block">
                    <span className="text-gray-300">★</span>
                    <span 
                      className="absolute inset-0 text-yellow-400 overflow-hidden" 
                      style={{ width: "50%" }}
                    >
                      ★
                    </span>
                  </span>
                ) : (
                  <span className="text-gray-300">★</span>
                )}
              </button>
            );
          })}
        </div>

        {/* Score Display and Dropdown Trigger */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowDropdown(!showDropdown)}
            className="px-3 py-1 border border-gray-300 rounded-md bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-trig-green-500 flex items-center gap-2 min-w-[80px]"
          >
            <span className="text-sm font-semibold">
              {value === 0 ? "----" : `${value}/10`}
            </span>
            <svg
              className={`w-4 h-4 text-gray-400 transition-transform ${
                showDropdown ? "transform rotate-180" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M19 9l-7 7-7-7"
              />
            </svg>
          </button>

          {/* Dropdown Menu */}
          {showDropdown && (
            <>
              {/* Backdrop */}
              <div
                className="fixed inset-0 z-10"
                onClick={() => setShowDropdown(false)}
              />

              {/* Options */}
              <div className="absolute z-20 right-0 mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-48 overflow-y-auto">
                <button
                  type="button"
                  onClick={() => handleDropdownSelect(0)}
                  className={`w-full px-3 py-2 text-left hover:bg-gray-100 whitespace-nowrap ${
                    value === 0 ? "bg-gray-50 font-semibold" : ""
                  }`}
                >
                  ----
                </button>
                {[...Array(10)].map((_, i) => {
                  const score = i + 1;
                  return (
                    <button
                      key={score}
                      type="button"
                      onClick={() => handleDropdownSelect(score)}
                      className={`w-full px-3 py-2 text-left hover:bg-gray-100 whitespace-nowrap ${
                        value === score ? "bg-gray-50 font-semibold" : ""
                      }`}
                    >
                      {score}/10
                      {value === score && (
                        <span className="ml-2 text-trig-green-600">✓</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Helper text */}
      <p className="text-xs text-gray-500 mt-1">
        Click left/right side of stars for half/full scores, or use dropdown
      </p>
    </div>
  );
}

