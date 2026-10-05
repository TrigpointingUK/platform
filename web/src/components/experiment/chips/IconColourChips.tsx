/**
 * IconColourChips - how the Trigs v2 map colours its icons (by current
 * condition, logged condition, or the difference), and which colours it shows
 */

import type { ReactNode } from "react";
import { ArrowLeftRight, NotebookPen, ShieldCheck } from "lucide-react";
import { getCategoryIconUrl, type IconColor } from "../../../lib/mapIcons";
import {
  ICON_COLOUR_LEGENDS,
  ICON_COLOURS,
  ICON_COLOUR_MODES,
  type IconColourMode,
} from "../../../lib/iconColours";

const MODES: Record<IconColourMode, { label: string; icon: ReactNode; needsLogs: boolean }> = {
  current: {
    label: "Current condition",
    icon: <ShieldCheck className="w-3.5 h-3.5" />,
    needsLogs: false,
  },
  logged: {
    label: "Logged condition",
    icon: <NotebookPen className="w-3.5 h-3.5" />,
    needsLogs: true,
  },
  difference: {
    label: "Difference",
    icon: <ArrowLeftRight className="w-3.5 h-3.5" />,
    needsLogs: true,
  },
};

export interface IconColourChipsProps {
  mode: IconColourMode;
  onModeChange: (mode: IconColourMode) => void;
  /** Whether there's someone's logs to colour by */
  hasLogUser: boolean;
  hiddenColours: IconColor[];
  onToggleColour: (colour: IconColor) => void;
  /** How many trigs each colour has, once the map's trigs have loaded */
  counts?: Record<IconColor, number>;
}

export function IconColourChips({
  mode,
  onModeChange,
  hasLogUser,
  hiddenColours,
  onToggleColour,
  counts,
}: IconColourChipsProps) {
  return (
    <>
      {/* One mode at a time */}
      <div className="flex flex-wrap gap-2" role="group" aria-label="Colour icons by">
        {ICON_COLOUR_MODES.map((m) => {
          const { label, icon, needsLogs } = MODES[m];
          const disabled = needsLogs && !hasLogUser;
          const active = mode === m;
          return (
            <button
              key={m}
              type="button"
              onClick={() => onModeChange(m)}
              disabled={disabled}
              aria-pressed={active}
              title={disabled ? "Sign in, or pick a user in the Logs filter" : undefined}
              className={`
                inline-flex items-center gap-1.5 px-3 py-1.5
                w-44 text-sm font-medium rounded-full
                border transition-all duration-150
                ${disabled
                  ? "bg-gray-100 dark:bg-gray-800 border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500 cursor-not-allowed"
                  : active
                    ? "bg-trig-green-50 dark:bg-trig-green-900/30 border-trig-green-300 dark:border-trig-green-700 text-trig-green-700 dark:text-trig-green-300"
                    : "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400 dark:hover:border-gray-500 cursor-pointer"
                }
              `}
            >
              <span className="flex-shrink-0">{icon}</span>
              <span className="flex-1 text-left truncate">{label}</span>
            </button>
          );
        })}
      </div>

      {/* Each colour shown or hidden; doubles as the legend */}
      <div className="flex flex-wrap gap-2 mt-3" role="group" aria-label="Show icons">
        {ICON_COLOURS.map((colour) => {
          const { label, description } = ICON_COLOUR_LEGENDS[mode][colour];
          const shown = !hiddenColours.includes(colour);
          return (
            <button
              key={colour}
              type="button"
              onClick={() => onToggleColour(colour)}
              aria-pressed={shown}
              title={`${description} - click to ${shown ? "hide" : "show"}`}
              className={`
                inline-flex items-center gap-1.5 pl-2 pr-3 py-1
                w-44 text-sm rounded-full border transition-all duration-150 cursor-pointer
                ${shown
                  ? "bg-white dark:bg-gray-800 border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:border-gray-400 dark:hover:border-gray-500"
                  : "bg-gray-100 dark:bg-gray-900 border-gray-200 dark:border-gray-700 text-gray-400 dark:text-gray-500"
                }
              `}
            >
              <img
                src={getCategoryIconUrl(colour)}
                alt=""
                className={`h-6 w-auto flex-shrink-0 ${shown ? "" : "opacity-40 grayscale"}`}
              />
              <span className={`flex-1 text-left truncate ${shown ? "" : "line-through"}`}>
                {label}
              </span>
              {counts && (
                <span className="flex-shrink-0 text-xs text-gray-500 dark:text-gray-400">
                  {counts[colour].toLocaleString("en-GB")}
                </span>
              )}
            </button>
          );
        })}
      </div>
    </>
  );
}

export default IconColourChips;
