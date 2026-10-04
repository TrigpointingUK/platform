import {
  useCurrentUseValues,
  useHistoricUseValues,
} from "../../hooks/useReferenceData";
import type { TrigUseKind } from "../../lib/api";

interface TrigUseSelectProps {
  kind: TrigUseKind;
  value: string;
  onChange: (value: string) => void;
}

/**
 * Historic use / recent use select for the admin trig forms. Options are the
 * values maintained at /admin/historic-use and /admin/recent-use. A trig's
 * existing value is kept as an option even if it isn't listed, so opening
 * the form never silently changes it.
 */
export default function TrigUseSelect({ kind, value, onChange }: TrigUseSelectProps) {
  const historic = useHistoricUseValues();
  const current = useCurrentUseValues();
  const { data: values } = kind === "historic" ? historic : current;

  const options = values?.map((v) => v.value) ?? [];
  if (!options.includes(value)) options.unshift(value);

  const id = `trig-${kind}-use`;
  return (
    <div>
      <label
        htmlFor={id}
        className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1"
      >
        {kind === "historic" ? "Historic Use" : "Recent Use"}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-gray-300 dark:border-gray-600 px-3 py-2 text-gray-800 dark:text-gray-100 bg-white dark:bg-gray-700 shadow-sm focus:border-trig-green-500 focus:ring-2 focus:ring-trig-green-400"
      >
        {options.map((use) => (
          <option key={use} value={use}>
            {use || "(blank)"}
          </option>
        ))}
      </select>
    </div>
  );
}
