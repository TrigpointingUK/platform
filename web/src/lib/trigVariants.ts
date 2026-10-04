/**
 * Trig variant helpers. A variant qualifies a trig's type (e.g. a Buried
 * Block's detector material); trig_type.variant_group says which group of
 * variants, if any, a type's trigs may choose from.
 */

import type { TrigCategory } from "../hooks/useTrigTypes";
import type { VariantGroup } from "../hooks/useReferenceData";

/**
 * Pseudo variant for the trigs page's variant filter: trigs with no variant
 * recorded (most of them). Ticking it alongside every real variant means no
 * filter, as with the other multi-select filters.
 */
export const VARIANT_NOT_RECORDED = "NOT_RECORDED";

/** Every variant filter value: all groups' variants, then "not recorded". */
export function allVariantFilterValues(groups: readonly VariantGroup[]): string[] {
  return [...groups.flatMap((g) => g.values.map((v) => v.value)), VARIANT_NOT_RECORDED];
}

/** The variant group the given type accepts, or null if none. */
export function typeVariantGroup(
  categories: TrigCategory[] | undefined,
  typeId: number | null
): string | null {
  if (typeId === null || !categories) return null;
  for (const category of categories) {
    const type = category.types.find((t) => t.id === typeId);
    if (type) return type.variant_group ?? null;
  }
  return null;
}

/**
 * The variant groups the trigs page's variant filter should offer: the groups
 * of the selected types, but only when every selected type has one (e.g. only
 * Bolts and/or Buried Blocks). Selecting any type without variants, every
 * type, or none at all hides the filter. Empty means the filter is hidden and
 * doesn't apply.
 */
export function relevantVariantGroups(
  groups: readonly VariantGroup[],
  selectedTypes: readonly string[],
  typeGroups: ReadonlyMap<string, string>,
): VariantGroup[] {
  if (selectedTypes.length === 0) return [];
  const wanted = new Set<string>();
  for (const code of selectedTypes) {
    const group = typeGroups.get(code);
    if (!group) return [];
    wanted.add(group);
  }
  return groups.filter((group) => wanted.has(group.code));
}

/**
 * The variant values to filter by, given the groups on offer: undefined for
 * no filter (the filter is hidden, or everything on offer is ticked), else the
 * ticked values on offer (empty meaning show nothing).
 */
export function variantFilter(
  shownGroups: readonly VariantGroup[],
  selectedVariants: readonly string[],
): string[] | undefined {
  if (shownGroups.length === 0) return undefined;
  const offered = allVariantFilterValues(shownGroups);
  const selected = selectedVariants.filter((v) => offered.includes(v));
  if (selected.length === offered.length) return undefined;
  return selected;
}
