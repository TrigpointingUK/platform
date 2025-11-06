import { TrigAttrsData } from "../../lib/api";

interface OfficialDataSectionProps {
  attrs?: TrigAttrsData[];
}

export default function OfficialDataSection({
  attrs,
}: OfficialDataSectionProps) {
  if (!attrs || attrs.length === 0) {
    return null;
  }

  return (
    <div className="space-y-6">
      {attrs.map((sourceData, sourceIndex) => {
        // Get sorted attr_ids for consistent column order
        const attrIds = Object.keys(sourceData.attr_names)
          .map(Number)
          .sort((a, b) => a - b);

        return (
          <div key={sourceIndex} className="overflow-x-auto">
            <table className="min-w-full border-collapse border border-gray-300 text-sm">
              <thead>
                {/* Source header row */}
                <tr className="bg-gray-100">
                  <th
                    colSpan={attrIds.length}
                    className="border border-gray-300 px-3 py-2 text-left"
                  >
                    {sourceData.source.url ? (
                      <a
                        href={sourceData.source.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-trig-green-600 hover:underline font-semibold"
                      >
                        {sourceData.source.name}
                      </a>
                    ) : (
                      <span className="font-semibold">
                        {sourceData.source.name}
                      </span>
                    )}
                  </th>
                </tr>
                {/* Column headers row */}
                <tr className="bg-gray-50">
                  {attrIds.map((attrId) => (
                    <td
                      key={attrId}
                      className="border border-gray-300 px-3 py-2 whitespace-nowrap font-medium"
                    >
                      {sourceData.attr_names[attrId]}
                    </td>
                  ))}
                </tr>
              </thead>
              <tbody>
                {/* Data rows */}
                {sourceData.attribute_sets.map((attrSet, rowIndex) => (
                  <tr key={rowIndex} className="hover:bg-gray-50">
                    {attrIds.map((attrId) => (
                      <td
                        key={attrId}
                        className="border border-gray-300 px-3 py-2 whitespace-nowrap"
                      >
                        {attrSet.values[attrId] || ""}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        );
      })}
    </div>
  );
}

