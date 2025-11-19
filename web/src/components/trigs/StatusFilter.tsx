interface StatusFilterProps {
  selectedStatuses: number[];
  onToggleStatus: (statusId: number) => void;
  visibleStatuses?: number[]; // Only show these statuses
}

// Status levels with icons and colors
const STATUS_LEVELS = [
  { id: 10, name: "Pillar", icon: "/icons/t_pillar.png", color: "bg-blue-600" },
  { id: 20, name: "Major mark", icon: "/icons/t_fbm.png", color: "bg-green-600" },
  { id: 30, name: "Minor mark", icon: "/icons/t_passive.png", color: "bg-yellow-600" },
  { id: 40, name: "Intersected", icon: "/icons/t_intersected.png", color: "bg-orange-600" },
  { id: 50, name: "User Added", icon: "/icons/t_user_added.svg", color: "bg-red-600" },
  { id: 60, name: "Controversial", icon: "/icons/t_controversial.svg", color: "bg-gray-600" },
];

export function StatusFilter({
  selectedStatuses,
  onToggleStatus,
  visibleStatuses,
}: StatusFilterProps) {
  const statusesToShow = visibleStatuses
    ? STATUS_LEVELS.filter((s) => visibleStatuses.includes(s.id))
    : STATUS_LEVELS;

  return (
    <div className="flex flex-wrap gap-2">
      {statusesToShow.map((status) => {
        const isSelected = selectedStatuses.includes(status.id);
        return (
          <button
            key={status.id}
            type="button"
            onClick={() => onToggleStatus(status.id)}
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
            title={status.name}
            aria-label={`${isSelected ? "Deselect" : "Select"} ${status.name}`}
            aria-pressed={isSelected}
          >
            <img 
              src={status.icon} 
              alt={status.name}
              className={`w-full h-full object-contain ${isSelected ? '' : 'opacity-60'}`}
            />
          </button>
        );
      })}
    </div>
  );
}

