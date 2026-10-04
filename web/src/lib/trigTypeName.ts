/**
 * Display name for a trig's type, qualified by its variant when one is
 * recorded: "Buried Block (concrete ring)".
 */
export function formatTypeName(typeName: string, variantName?: string | null): string {
  return variantName ? `${typeName} (${variantName.toLowerCase()})` : typeName;
}
