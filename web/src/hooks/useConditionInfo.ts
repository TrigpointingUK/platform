/**
 * Hook to get condition info for display in cards and other components.
 *
 * Provides a function that returns icon filename and label for a condition code,
 * using API data when available with a hardcoded fallback.
 */
import { useMemo } from "react";
import { useConditions, buildConditionMap } from "./useConditions";
import {
  getConditionIcon,
  getConditionName,
  getConditionVariant,
  type ConditionVariant,
} from "../lib/conditionUtils";

/**
 * Hardcoded fallback condition info for when API data is loading.
 */
const FALLBACK_CONDITIONS: Record<string, { icon: string; label: string; variant: ConditionVariant }> = {
  Z: { icon: "c_unknown.png", label: "Not Logged", variant: "unknown" },
  N: { icon: "c_possiblymissing.png", label: "Couldn't Find", variant: "missing" },
  G: { icon: "c_good.png", label: "Good", variant: "good" },
  S: { icon: "c_slightlydamaged.png", label: "Slightly Damaged", variant: "good" },
  C: { icon: "c_slightlydamaged.png", label: "Converted", variant: "damaged" },
  D: { icon: "c_damaged.png", label: "Damaged", variant: "damaged" },
  R: { icon: "c_toppled.png", label: "Remains", variant: "damaged" },
  T: { icon: "c_toppled.png", label: "Toppled", variant: "damaged" },
  M: { icon: "c_toppled.png", label: "Moved", variant: "damaged" },
  Q: { icon: "c_possiblymissing.png", label: "Possibly Missing", variant: "missing" },
  X: { icon: "c_definitelymissing.png", label: "Destroyed", variant: "missing" },
  V: { icon: "c_unreachablebutvisible.png", label: "Unreachable but Visible", variant: "damaged" },
  P: { icon: "c_unknown.png", label: "Inaccessible", variant: "unknown" },
  U: { icon: "c_unknown.png", label: "Unknown", variant: "unknown" },
  "-": { icon: "c_nolog.png", label: "Not Visited", variant: "unknown" },
};

export interface ConditionInfo {
  icon: string;
  label: string;
  variant: ConditionVariant;
}

/**
 * Hook that provides a function to get condition info.
 *
 * Returns a memoised function that looks up condition info from API data
 * with a fallback to hardcoded values.
 */
export function useConditionInfo() {
  const { data: apiConditions } = useConditions();

  const conditionMap = useMemo(() => {
    if (!apiConditions) return null;
    return buildConditionMap(apiConditions);
  }, [apiConditions]);

  const getConditionInfo = useMemo(() => {
    return (code: string | null | undefined): ConditionInfo => {
      if (!code) {
        return FALLBACK_CONDITIONS["-"] || { icon: "c_unknown.png", label: "Unknown", variant: "unknown" };
      }

      const upperCode = code.toUpperCase();

      // Use API data if available
      if (conditionMap && conditionMap.size > 0) {
        const icon = getConditionIcon(conditionMap, upperCode);
        const label = getConditionName(conditionMap, upperCode);
        const variant = getConditionVariant(conditionMap, upperCode);

        // If we got data from API, use it
        if (icon || label !== "Unknown") {
          return {
            icon: icon || "c_unknown.png",
            label,
            variant,
          };
        }
      }

      // Fall back to hardcoded
      return FALLBACK_CONDITIONS[upperCode] || { icon: "c_unknown.png", label: code, variant: "unknown" };
    };
  }, [conditionMap]);

  return { getConditionInfo, isLoading: !apiConditions };
}

/**
 * Standalone function to get condition info without the hook.
 * Use this when you don't need reactivity or can't use hooks.
 *
 * @deprecated Prefer useConditionInfo hook for reactive updates
 */
export function getConditionInfoFallback(code: string): ConditionInfo {
  const upperCode = code?.toUpperCase() || "-";
  return FALLBACK_CONDITIONS[upperCode] || { icon: "c_unknown.png", label: code, variant: "unknown" };
}

