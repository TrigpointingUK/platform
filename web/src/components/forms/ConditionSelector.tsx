import { useState } from "react";
import Badge from "../ui/Badge";

interface ConditionOption {
  value: string;
  label: string;
  icon: string;
  variant: "good" | "damaged" | "missing" | "unknown";
}

const CONDITIONS: ConditionOption[] = [
  { value: "G", label: "Good", icon: "c_good.png", variant: "good" },
  { value: "S", label: "Slightly Damaged", icon: "c_slightlydamaged.png", variant: "damaged" },
  { value: "D", label: "Damaged", icon: "c_damaged.png", variant: "damaged" },
  { value: "C", label: "Converted", icon: "c_slightlydamaged.png", variant: "damaged" },
  { value: "T", label: "Toppled", icon: "c_toppled.png", variant: "damaged" },
  { value: "R", label: "Remains", icon: "c_toppled.png", variant: "damaged" },
  { value: "M", label: "Moved", icon: "c_toppled.png", variant: "missing" },
  { value: "Q", label: "Possibly Missing", icon: "c_possiblymissing.png", variant: "damaged" },
  { value: "P", label: "Inaccessible", icon: "c_unknown.png", variant: "unknown" },
  { value: "X", label: "Destroyed", icon: "c_definitelymissing.png", variant: "missing" },
  { value: "V", label: "Unreachable but Visible", icon: "c_unreachablebutvisible.png", variant: "unknown" },
  { value: "N", label: "Couldn't Find", icon: "c_possiblymissing.png", variant: "missing" },
  { value: "U", label: "Unknown", icon: "c_unknown.png", variant: "unknown" },
];

interface ConditionSelectorProps {
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
}

export default function ConditionSelector({
  value,
  onChange,
  required = false,
}: ConditionSelectorProps) {
  const [isOpen, setIsOpen] = useState(false);
  
  const selectedCondition = CONDITIONS.find((c) => c.value === value) || CONDITIONS[0];

  const handleSelect = (conditionValue: string) => {
    onChange(conditionValue);
    setIsOpen(false);
  };

  return (
    <div className="relative">
      <label className="block text-sm font-semibold text-gray-700 mb-1">
        Condition {required && <span className="text-red-500">*</span>}
      </label>
      
      {/* Selected Condition Display (clickable) */}
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-3 py-2 border border-gray-300 rounded-md bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-trig-green-500 flex items-center justify-between"
      >
        <Badge variant={selectedCondition.variant}>
          <img
            src={`/icons/conditions/${selectedCondition.icon}`}
            alt=""
            className="w-4 h-4 inline-block mr-1.5"
          />
          {selectedCondition.label}
        </Badge>
        <svg
          className={`w-5 h-5 text-gray-400 transition-transform ${
            isOpen ? "transform rotate-180" : ""
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
      {isOpen && (
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-10"
            onClick={() => setIsOpen(false)}
          />
          
          {/* Options */}
          <div className="absolute z-20 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg max-h-64 overflow-y-auto">
            {CONDITIONS.map((condition) => (
              <button
                key={condition.value}
                type="button"
                onClick={() => handleSelect(condition.value)}
                className={`w-full px-3 py-2 text-left hover:bg-gray-100 flex items-center gap-2 ${
                  condition.value === value ? "bg-gray-50" : ""
                }`}
              >
                <Badge variant={condition.variant}>
                  <img
                    src={`/icons/conditions/${condition.icon}`}
                    alt=""
                    className="w-4 h-4 inline-block mr-1.5"
                  />
                  {condition.label}
                </Badge>
                {condition.value === value && (
                  <svg
                    className="w-4 h-4 text-trig-green-600 ml-auto"
                    fill="currentColor"
                    viewBox="0 0 20 20"
                  >
                    <path
                      fillRule="evenodd"
                      d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                      clipRule="evenodd"
                    />
                  </svg>
                )}
              </button>
            ))}
          </div>
        </>
      )}
    </div>
  );
}

