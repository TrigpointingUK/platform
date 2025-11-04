import { useState } from "react";
import Badge from "../ui/Badge";

interface ConditionOption {
  value: string;
  label: string;
  variant: "good" | "damaged" | "missing" | "unknown";
}

const CONDITIONS: ConditionOption[] = [
  { value: "G", label: "Good", variant: "good" },
  { value: "D", label: "Damaged", variant: "damaged" },
  { value: "M", label: "Missing", variant: "missing" },
  { value: "P", label: "Possibly Missing", variant: "damaged" },
  { value: "U", label: "Unknown", variant: "unknown" },
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
          <div className="absolute z-20 w-full mt-1 bg-white border border-gray-300 rounded-md shadow-lg">
            {CONDITIONS.map((condition) => (
              <button
                key={condition.value}
                type="button"
                onClick={() => handleSelect(condition.value)}
                className={`w-full px-3 py-2 text-left hover:bg-gray-100 flex items-center gap-2 ${
                  condition.value === value ? "bg-gray-50" : ""
                }`}
              >
                <Badge variant={condition.variant}>{condition.label}</Badge>
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

