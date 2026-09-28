/**
 * Multi-select filters in the trigs page URL, so a filtered view survives a
 * refresh and can be shared as a link.
 *
 * - parameter absent: everything selected (the default)
 * - parameter present but empty (`conditions=`): nothing selected
 * - otherwise: a comma-separated list of the selected values
 */

import type { ListFilter } from "../components/experiment/chips/listFilter";

/**
 * Read a selection from the URL. Values not in `all` are dropped; if that
 * leaves nothing from a non-empty list (e.g. an old link with codes that no
 * longer exist), fall back to everything rather than showing no trigs.
 */
export function readSelection<T extends string | number>(
  params: URLSearchParams,
  key: string,
  all: readonly T[],
): T[] {
  const raw = params.get(key);
  if (raw === null) return [...all];
  if (raw === "") return [];
  const byString = new Map(all.map((value) => [String(value), value]));
  const selected = raw
    .split(",")
    .map((value) => byString.get(value))
    .filter((value): value is T => value !== undefined);
  return selected.length > 0 ? selected : [...all];
}

/** Write a selection to the URL, omitting it when everything is selected. */
export function writeSelection<T extends string | number>(
  params: URLSearchParams,
  key: string,
  selected: readonly T[],
  all: readonly T[],
): void {
  if (all.length > 0 && all.every((value) => selected.includes(value))) return;
  params.set(key, selected.join(","));
}

/** Area IDs from the URL (`areas=12,34`); an empty list means no area filter. */
export function readAreaIds(params: URLSearchParams): number[] {
  return (params.get("areas") ?? "")
    .split(",")
    .map(Number)
    .filter((id) => Number.isInteger(id) && id > 0);
}

/**
 * The trig list filter: `lists=1,2` keeps trigs on any of those lists, and
 * `listsMode=not` turns it into "on none of them".
 */
export function readListFilter(params: URLSearchParams): ListFilter {
  const listIds = (params.get("lists") ?? "")
    .split(",")
    .map(Number)
    .filter((id) => Number.isInteger(id) && id > 0);
  if (listIds.length === 0) return { mode: "all", listIds: [] };
  return { mode: params.get("listsMode") === "not" ? "not_in" : "in", listIds };
}

/** Write the trig list filter to the URL, omitting it when it's off. */
export function writeListFilter(
  params: URLSearchParams,
  filter: ListFilter,
): void {
  if (filter.mode === "all" || filter.listIds.length === 0) return;
  params.set("lists", filter.listIds.join(","));
  if (filter.mode === "not_in") params.set("listsMode", "not");
}
