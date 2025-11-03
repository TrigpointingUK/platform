interface PhysicalTypeFilterProps {
  selectedTypes: string[];
  onToggleType: (type: string) => void;
}

// Common physical types with abbreviations
const PHYSICAL_TYPES = [
  { name: "Pillar", abbrev: "P", color: "bg-blue-600" },
  { name: "Bolt", abbrev: "B", color: "bg-green-600" },
  { name: "FBM", abbrev: "F", color: "bg-purple-600" },
  { name: "Passive Station", abbrev: "PS", color: "bg-orange-600" },
  { name: "Active Station", abbrev: "AS", color: "bg-red-600" },
  { name: "Intersection", abbrev: "I", color: "bg-yellow-600" },
  { name: "Other", abbrev: "O", color: "bg-gray-600" },
];

export function PhysicalTypeFilter({
  selectedTypes,
  onToggleType,
}: PhysicalTypeFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {PHYSICAL_TYPES.map((type) => {
        const isSelected = selectedTypes.includes(type.name);
        return (
          <button
            key={type.name}
            type="button"
            onClick={() => onToggleType(type.name)}
            className={`
              inline-flex items-center justify-center
              w-10 h-10 rounded-lg
              text-sm font-bold
              transition-all duration-200
              ${
                isSelected
                  ? `${type.color} text-white shadow-md scale-105`
                  : "bg-gray-200 text-gray-600 hover:bg-gray-300"
              }
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            `}
            title={type.name}
            aria-label={`${isSelected ? "Deselect" : "Select"} ${type.name}`}
            aria-pressed={isSelected}
          >
            {type.abbrev}
          </button>
        );
      })}
    </div>
  );
}

