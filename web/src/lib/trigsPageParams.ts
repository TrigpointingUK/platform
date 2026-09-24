/**
 * Multi-select filters in the trigs page URL, so a filtered view survives a
 * refresh and can be shared as a link.
 *
 * - parameter absent: everything selected (the default)
 * - parameter present but empty (`conditions=`): nothing selected
 * - otherwise: a comma-separated list of the selected values
 */

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
