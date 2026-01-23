/**
 * Condition utility functions.
 *
 * These functions work with condition data from the API to provide
 * colour mapping, icon lookup, and disagreement detection.
 *
 * @stable - These utilities determine marker appearance and condition logic.
 */

import type { Condition } from "./api";

/**
 * Icon color type for map markers
 */
export type IconColor = "green" | "yellow" | "red" | "grey";

/**
 * Badge variant for condition display
 */
export type ConditionVariant = "good" | "damaged" | "missing" | "unknown";

/**
 * User log status for a trigpoint
 */
export interface UserLogStatus {
  hasLogged: boolean;
  condition?: string; // Condition code from the user's log
}

/**
 * Map trig_colour string to IconColor.
 * Handles common colour names and falls back to grey.
 */
export function mapTrigColourToIconColor(
  trigColour: string | null | undefined
): IconColor {
  if (!trigColour) return "grey";

  const colour = trigColour.toLowerCase();
  if (colour === "green") return "green";
  if (colour === "yellow" || colour === "orange" || colour === "amber")
    return "yellow";
  if (colour === "red") return "red";
  return "grey";
}

/**
 * Map log_colour string to IconColor.
 * Used for "My Logs" map mode where colours reflect the user's logged condition.
 */
export function mapLogColourToIconColor(
  logColour: string | null | undefined
): IconColor {
  if (!logColour) return "grey";

  const colour = logColour.toLowerCase();
  if (colour === "green") return "green";
  if (colour === "yellow" || colour === "orange" || colour === "amber")
    return "yellow";
  if (colour === "red") return "red";
  return "grey";
}

/**
 * Map trig_colour to badge variant for display components.
 */
export function mapTrigColourToVariant(
  trigColour: string | null | undefined
): ConditionVariant {
  if (!trigColour) return "unknown";

  const colour = trigColour.toLowerCase();
  if (colour === "green") return "good";
  if (colour === "yellow" || colour === "orange" || colour === "amber")
    return "damaged";
  if (colour === "red") return "missing";
  return "unknown";
}

/**
 * Get condition colour for "Condition" map mode.
 * Uses trig_colour from the condition record.
 */
export function getConditionColour(
  conditionMap: Map<string, Condition>,
  conditionCode: string | null | undefined
): IconColor {
  if (!conditionCode) return "grey";

  const condition = conditionMap.get(conditionCode.toUpperCase());
  if (!condition) return "grey";

  return mapTrigColourToIconColor(condition.trig_colour);
}

/**
 * Get colour for "My Logs" map mode.
 *
 * Uses log_colour from the condition record to determine marker colour.
 * Special handling:
 * - Not logged: grey
 * - Logged but no condition (empty/null/Z): green (user logged but didn't specify)
 * - Otherwise: use log_colour from condition record
 */
export function getUserLogColour(
  conditionMap: Map<string, Condition>,
  logStatus: UserLogStatus
): IconColor {
  if (!logStatus.hasLogged) {
    return "grey";
  }

  const conditionCode = logStatus.condition || "";
  const upperCode = conditionCode.toUpperCase();

  // Special case: Empty or Z (Not Logged) counts as green for userLog mode
  // The user logged but didn't specify a condition, which typically means it was fine
  if (upperCode === "" || upperCode === "Z") {
    return "green";
  }

  const condition = conditionMap.get(upperCode);
  if (!condition) return "grey";

  return mapLogColourToIconColor(condition.log_colour);
}

/**
 * Check if two condition codes are "similar" (don't disagree).
 *
 * Uses the similar_codes field from the condition table.
 * For example, if G has similar_codes="S", then G and S are similar.
 *
 * @param conditionMap - Map of conditions from API
 * @param code1 - First condition code
 * @param code2 - Second condition code
 * @returns true if conditions are similar (don't disagree)
 */
export function conditionsAreSimilar(
  conditionMap: Map<string, Condition>,
  code1: string | null | undefined,
  code2: string | null | undefined
): boolean {
  // Same code always similar
  if (code1 === code2) return true;

  // If either is null/undefined, can't compare
  if (!code1 || !code2) return false;

  const upper1 = code1.toUpperCase();
  const upper2 = code2.toUpperCase();

  // Same after uppercase
  if (upper1 === upper2) return true;

  // Check if code1's similar_codes includes code2
  const condition1 = conditionMap.get(upper1);
  if (condition1?.similar_codes?.includes(upper2)) {
    return true;
  }

  // Check if code2's similar_codes includes code1
  const condition2 = conditionMap.get(upper2);
  if (condition2?.similar_codes?.includes(upper1)) {
    return true;
  }

  return false;
}

/**
 * Check if a logged condition disagrees with a curated condition.
 *
 * Uses similar_codes from the condition table to determine matches.
 * Returns true if conditions disagree significantly.
 *
 * Special handling for certain logged conditions that should be ignored:
 * - Check the condition's log_colour - if it's null/grey, the condition
 *   is considered "uncertain" and doesn't count as a disagreement
 *
 * @param conditionMap - Map of conditions from API
 * @param loggedCondition - Condition code from the user's log
 * @param curatedCondition - Current curated condition of the trig
 * @returns true if conditions disagree
 */
export function conditionsDisagree(
  conditionMap: Map<string, Condition>,
  loggedCondition: string | null | undefined,
  curatedCondition: string | null | undefined
): boolean {
  // If no logged condition, no disagreement
  if (!loggedCondition) return false;

  // If no curated condition, can't compare
  if (!curatedCondition) return false;

  const upperLogged = loggedCondition.toUpperCase();
  const upperCurated = curatedCondition.toUpperCase();

  // Get the logged condition to check if it should be ignored
  const loggedCond = conditionMap.get(upperLogged);

  // If the logged condition has no log_colour (grey/null), it's uncertain
  // and shouldn't count as a disagreement (e.g., N, P, U, Z)
  if (!loggedCond?.log_colour || loggedCond.log_colour.toLowerCase() === "grey") {
    // Special case: V (Unreachable but visible) should show disagreement
    // if curated is missing/destroyed (Q, X)
    if (upperLogged === "V") {
      const curatedCond = conditionMap.get(upperCurated);
      // Only show V disagreement if curated condition is "red" (missing/destroyed)
      if (curatedCond?.trig_colour?.toLowerCase() === "red") {
        return true;
      }
    }
    return false;
  }

  // Check if conditions are similar
  return !conditionsAreSimilar(conditionMap, upperLogged, upperCurated);
}

/**
 * Get the icon filename for a condition.
 */
export function getConditionIcon(
  conditionMap: Map<string, Condition>,
  conditionCode: string | null | undefined
): string | null {
  if (!conditionCode) return null;

  const condition = conditionMap.get(conditionCode.toUpperCase());
  return condition?.icon_file ?? null;
}

/**
 * Get the display name for a condition.
 */
export function getConditionName(
  conditionMap: Map<string, Condition>,
  conditionCode: string | null | undefined
): string {
  if (!conditionCode) return "Unknown";

  const condition = conditionMap.get(conditionCode.toUpperCase());
  return condition?.name ?? "Unknown";
}

/**
 * Get the badge variant for a condition.
 */
export function getConditionVariant(
  conditionMap: Map<string, Condition>,
  conditionCode: string | null | undefined
): ConditionVariant {
  if (!conditionCode) return "unknown";

  const condition = conditionMap.get(conditionCode.toUpperCase());
  return mapTrigColourToVariant(condition?.trig_colour);
}

