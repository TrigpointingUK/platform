import { useVariantGroups } from "../../hooks/useReferenceData";
import type { TrigCategory } from "../../hooks/useTrigTypes";
import { typeVariantGroup } from "../../lib/trigVariants";

interface VariantSelectProps {
  categories: TrigCategory[] | undefined;
  typeId: number | null;
  value: string | null;
  onChange: (code: string | null) => void;
}

/**
 * Variant select for the admin trig forms, labelled with the variant group's
 * name (e.g. "Detector material"). Renders nothing unless the selected type
 * has a variant group.
 */
export default function VariantSelect({
  categories,
  typeId,
  value,
  onChange,
}: VariantSelectProps) {
  const { data: groups } = useVariantGroups();

  const groupCode = typeVariantGroup(categories, typeId);
  const group = groups?.find((g) => g.code === groupCode);
  if (!group) return null;

  return (
    <div>
      <label
        htmlFor="trig-variant"
        className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
      >
        {group.name}
      </label>
      <select
        id="trig-variant"
        value={value ?? ""}
        onChange={(e) => onChange(e.target.value || null)}
        className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
      >
        <option value="">Not recorded</option>
        {group.values.map((v) => (
          <option key={v.value} value={v.value}>
            {v.label}
          </option>
        ))}
      </select>
    </div>
  );
}
