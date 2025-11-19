import type { IconColor } from "../../lib/mapIcons";

interface ColorFilterProps {
  selectedColors: IconColor[];
  onToggleColor: (color: IconColor) => void;
}

// Color levels with icons
const COLOR_LEVELS: { color: IconColor; name: string; icon: string }[] = [
  { color: "green", name: "Green", icon: "/icons/mapicon_intersected_green.png" },
  { color: "yellow", name: "Yellow", icon: "/icons/mapicon_intersected_yellow.png" },
  { color: "red", name: "Red", icon: "/icons/mapicon_intersected_red.png" },
  { color: "grey", name: "Grey", icon: "/icons/mapicon_intersected_grey.png" },
];

export function ColorFilter({
  selectedColors,
  onToggleColor,
}: ColorFilterProps) {
  return (
    <div className="flex flex-wrap gap-2">
      {COLOR_LEVELS.map((colorLevel) => {
        const isSelected = selectedColors.includes(colorLevel.color);
        return (
          <button
            key={colorLevel.color}
            type="button"
            onClick={() => onToggleColor(colorLevel.color)}
            className={`
              inline-flex items-center justify-center
              w-10 h-10 p-1 rounded-lg
              transition-all duration-200
              ${
                isSelected
                  ? "bg-trig-green-600 shadow-md scale-105 ring-2 ring-white"
                  : "bg-gray-200 hover:bg-gray-300"
              }
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            `}
            title={colorLevel.name}
            aria-label={`${isSelected ? "Deselect" : "Select"} ${colorLevel.name}`}
            aria-pressed={isSelected}
          >
            <img 
              src={colorLevel.icon} 
              alt={colorLevel.name}
              className={`w-full h-full object-contain ${isSelected ? '' : 'opacity-60'}`}
            />
          </button>
        );
      })}
    </div>
  );
}
