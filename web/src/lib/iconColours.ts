/**
 * Icon colours for the Trigs v2 map. A trig is coloured by its current
 * (curated) condition, by the condition in the log user's latest log of it,
 * or by how far apart those two are in the conditions' sort order.
 */

import { getConditionColor, getUserLogColor, type IconColor } from "./mapIcons";

export type IconColourMode = "current" | "logged" | "difference";

// The condition code for "Not logged", which a log with no condition records
const NO_CONDITION = "Z";

export const ICON_COLOUR_MODES: IconColourMode[] = ["current", "logged", "difference"];

/** Every icon colour, in legend order */
export const ICON_COLOURS: IconColor[] = ["green", "yellow", "red", "grey"];

/** What each colour means in each mode: a short label and a fuller description */
export const ICON_COLOUR_LEGENDS: Record<
  IconColourMode,
  Record<IconColor, { label: string; description: string }>
> = {
  current: {
    green: { label: "Good", description: "Good or slightly damaged" },
    yellow: { label: "Damaged", description: "Damaged or compromised" },
    red: { label: "Missing", description: "Missing or destroyed" },
    grey: { label: "Unknown", description: "Unknown, inaccessible or never logged" },
  },
  logged: {
    green: { label: "Good", description: "Logged good or slightly damaged, or with no condition" },
    yellow: { label: "Damaged", description: "Logged damaged or compromised" },
    red: { label: "Missing", description: "Logged missing, destroyed, inaccessible or unknown" },
    grey: { label: "Not logged", description: "Not logged" },
  },
  difference: {
    green: { label: "Same", description: "Logged condition matches the current one" },
    yellow: { label: "One step", description: "Logged condition is one step from the current one" },
    red: { label: "Further", description: "Logged condition is two or more steps from the current one" },
    grey: { label: "Not logged", description: "Not logged, or logged with no condition" },
  },
};

interface ConditionInfo {
  code: string;
  sort_order: number;
  trig_colour?: string | null;
  log_colour?: string | null;
}

/** Condition codes' positions in the sort order, and their icon colours */
export interface ConditionScale {
  /** Codes sharing a sort order share a position, e.g. Q and N */
  rank: Map<string, number>;
  trigColour: Map<string, IconColor>;
  logColour: Map<string, IconColor>;
}

const isIconColour = (value: string | null | undefined): value is IconColor =>
  ICON_COLOURS.includes(value as IconColor);

export function conditionScale(conditions: ConditionInfo[]): ConditionScale {
  const sortOrders = [...new Set(conditions.map((c) => c.sort_order))].sort((a, b) => a - b);
  const scale: ConditionScale = { rank: new Map(), trigColour: new Map(), logColour: new Map() };
  for (const c of conditions) {
    const code = c.code.toUpperCase();
    scale.rank.set(code, sortOrders.indexOf(c.sort_order));
    if (isIconColour(c.trig_colour)) scale.trigColour.set(code, c.trig_colour);
    if (isIconColour(c.log_colour)) scale.logColour.set(code, c.log_colour);
  }
  return scale;
}

/**
 * A trig's icon colour. Logged and difference colours are grey when the log
 * user hasn't logged it. A difference is also grey when their log records no
 * condition, or either condition isn't on the scale (e.g. before the
 * conditions have loaded).
 */
export function trigIconColour(
  trig: { condition: string; logged_condition?: string | null },
  mode: IconColourMode,
  scale: ConditionScale,
): IconColor {
  const current = (trig.condition ?? "").toUpperCase();
  if (mode === "current") {
    return scale.trigColour.get(current) ?? getConditionColor(current);
  }

  if (trig.logged_condition == null) return "grey";
  const logged = trig.logged_condition.toUpperCase();
  if (mode === "logged") {
    return scale.logColour.get(logged) ?? getUserLogColor({ hasLogged: true, condition: logged });
  }

  if (logged === NO_CONDITION) return "grey";
  const currentRank = scale.rank.get(current);
  const loggedRank = scale.rank.get(logged);
  if (currentRank === undefined || loggedRank === undefined) return "grey";
  const steps = Math.abs(currentRank - loggedRank);
  return steps === 0 ? "green" : steps === 1 ? "yellow" : "red";
}
