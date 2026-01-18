interface LoggedConditionFilterProps {
  showLogged: boolean;
  showNotLogged: boolean;
  onToggleLogged: () => void;
  onToggleNotLogged: () => void;
}

/**
 * Filter component for logged/not-logged trigpoints
 * Two toggle buttons:
 * - "Logged by you" with green/yellow/red icons
 * - "Not logged by you" with grey icon
 */
export function LoggedConditionFilter({
  showLogged,
  showNotLogged,
  onToggleLogged,
  onToggleNotLogged,
}: LoggedConditionFilterProps) {
  return (
    <div className="flex gap-2">
      {/* Logged by you button - shows green/yellow/red icons */}
      <button
        type="button"
        onClick={onToggleLogged}
        className={`
          inline-flex items-center justify-center
          h-10 px-2 rounded-lg
          transition-all duration-200
          ${
            showLogged
              ? "bg-trig-green-600 shadow-md scale-105 ring-2 ring-white dark:ring-gray-800"
              : "bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
          }
          focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
        `}
        title="Logged by you"
        aria-label={`${showLogged ? "Hide" : "Show"} trigpoints logged by you`}
        aria-pressed={showLogged}
      >
        <div className="flex items-center gap-0.5">
          <img 
            src="/icons/mapicon_pillar_green.png" 
            alt=""
            className={`w-6 h-6 object-contain ${showLogged ? '' : 'opacity-60'}`}
          />
          <img 
            src="/icons/mapicon_pillar_yellow.png" 
            alt=""
            className={`w-6 h-6 object-contain ${showLogged ? '' : 'opacity-60'}`}
          />
          <img 
            src="/icons/mapicon_pillar_red.png" 
            alt=""
            className={`w-6 h-6 object-contain ${showLogged ? '' : 'opacity-60'}`}
          />
        </div>
      </button>

      {/* Not logged by you button - shows grey icon */}
      <button
        type="button"
        onClick={onToggleNotLogged}
        className={`
          inline-flex items-center justify-center
          w-10 h-10 p-1 rounded-lg
          transition-all duration-200
          ${
            showNotLogged
              ? "bg-trig-green-600 shadow-md scale-105 ring-2 ring-white dark:ring-gray-800"
              : "bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600"
          }
          focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
        `}
        title="Not logged by you"
        aria-label={`${showNotLogged ? "Hide" : "Show"} trigpoints not logged by you`}
        aria-pressed={showNotLogged}
      >
        <img 
          src="/icons/mapicon_pillar_grey.png" 
          alt=""
          className={`w-full h-full object-contain ${showNotLogged ? '' : 'opacity-60'}`}
        />
      </button>
    </div>
  );
}
