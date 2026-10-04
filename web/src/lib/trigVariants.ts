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
 * of the selected types once the Type filter has been narrowed, plus any group
 * with an unticked variant (so an applied filter is never hidden). Unticking
 * "not recorded" keeps every group visible. Empty means the filter is hidden.
 */
export function relevantVariantGroups(
  groups: readonly VariantGroup[],
  selectedTypes: readonly string[],
  allTypeCodes: readonly string[],
  typeGroups: ReadonlyMap<string, string>,
  selectedVariants: readonly string[],
): VariantGroup[] {
  const typesNarrowed = selectedTypes.length < allTypeCodes.length;
  const wanted = new Set<string>();
  if (typesNarrowed) {
    for (const code of selectedTypes) {
      const group = typeGroups.get(code);
      if (group) wanted.add(group);
    }
  }
  const notRecordedUnticked = !selectedVariants.includes(VARIANT_NOT_RECORDED);
  return groups.filter(
    (group) =>
      notRecordedUnticked ||
      wanted.has(group.code) ||
      group.values.some((v) => !selectedVariants.includes(v.value))
  );
}
