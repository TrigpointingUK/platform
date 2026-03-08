import { useState, useEffect, useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import {
  CheckCircle2,
  AlertTriangle,
  HelpCircle,
  ChevronDown,
  ChevronUp,
  Plus,
  ArrowRightCircle,
  MapPin,
  AlertOctagon,
} from "lucide-react";
import toast from "react-hot-toast";

import Layout from "../../components/layout/Layout";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import {
  IrelandImportComparisonResponse,
  IrelandComparisonItem,
  IrelandDBTrigData,
  IrelandFieldDifference,
  fetchIrelandImportComparison,
  applyIrelandImportCSV,
  createTrigFromIrelandCSV,
  bulkCreateTrigsFromIrelandCSV,
} from "../../lib/api";

const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const ADMIN_SCOPE = "api:admin";
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };

// ============================================================================
// Category Configuration
// ============================================================================

const CATEGORY_CONFIG: Record<
  string,
  {
    icon: React.ComponentType<{ className?: string }>;
    colour: string;
    bgColour: string;
    borderColour: string;
    label: string;
    description: string;
  }
> = {
  ambiguous: {
    icon: AlertOctagon,
    colour: "text-red-600 dark:text-red-400",
    bgColour: "bg-red-50 dark:bg-red-900/20",
    borderColour: "border-red-200 dark:border-red-800",
    label: "Ambiguous",
    description: "Multiple DB records within 500m of this CSV row",
  },
  matched_different: {
    icon: AlertTriangle,
    colour: "text-amber-600 dark:text-amber-400",
    bgColour: "bg-amber-50 dark:bg-amber-900/20",
    borderColour: "border-amber-200 dark:border-amber-800",
    label: "Different",
    description: "Matched by proximity but with field differences",
  },
  new_in_csv: {
    icon: Plus,
    colour: "text-blue-600 dark:text-blue-400",
    bgColour: "bg-blue-50 dark:bg-blue-900/20",
    borderColour: "border-blue-200 dark:border-blue-800",
    label: "New in CSV",
    description: "CSV row with no DB match within 500m (can be created)",
  },
  orphan_in_db: {
    icon: HelpCircle,
    colour: "text-purple-600 dark:text-purple-400",
    bgColour: "bg-purple-50 dark:bg-purple-900/20",
    borderColour: "border-purple-200 dark:border-purple-800",
    label: "DB Only",
    description: "Irish DB trig with no CSV match within 500m",
  },
  matched_identical: {
    icon: CheckCircle2,
    colour: "text-green-600 dark:text-green-400",
    bgColour: "bg-green-50 dark:bg-green-900/20",
    borderColour: "border-green-200 dark:border-green-800",
    label: "Identical",
    description: "CSV and DB agree on all fields",
  },
};

// ============================================================================
// Field Difference Table Component
// ============================================================================

function FieldDifferenceTable({ differences }: { differences: IrelandFieldDifference[] }) {
  if (differences.length === 0) return null;

  return (
    <div className="mt-2">
      <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
        Field Differences
      </h4>
      <table className="w-full text-sm">
        <thead>
          <tr className="text-xs text-gray-500 dark:text-gray-400 uppercase">
            <th className="text-left py-1 pr-2">Field</th>
            <th className="text-left py-1 pr-2">CSV Value</th>
            <th className="text-left py-1">DB Value</th>
          </tr>
        </thead>
        <tbody className="font-mono">
          {differences.map((diff, idx) => (
            <tr
              key={idx}
              className="border-t border-gray-200 dark:border-gray-700"
            >
              <td className="py-1 pr-2 text-gray-700 dark:text-gray-300 font-sans font-medium">
                {diff.field_name}
              </td>
              <td className="py-1 pr-2 text-blue-700 dark:text-blue-300">
                {diff.csv_value ?? <span className="text-gray-400 italic">null</span>}
              </td>
              <td className="py-1 text-amber-700 dark:text-amber-300">
                {diff.db_value ?? <span className="text-gray-400 italic">null</span>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ============================================================================
// DB Trig Info Component
// ============================================================================

function DBTrigInfo({ trig }: { trig: IrelandDBTrigData }) {
  return (
    <div className="bg-white dark:bg-gray-900 rounded p-2 text-sm font-mono space-y-1">
      <div>
        <span className="text-gray-500">Trig:</span>{" "}
        <a
          href={`/trigs/${trig.trig_id}`}
          className="text-trig-green-600 hover:underline"
        >
          {trig.waypoint}
        </a>{" "}
        - {trig.name}
        {trig.has_non_irish_gridref && (
          <span className="ml-2 inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-300 dark:border-orange-700">
            <AlertTriangle className="w-3 h-3" />
            Non-Irish gridref
          </span>
        )}
      </div>
      {trig.area_name && (
        <div>
          <span className="text-gray-500">Area:</span> {trig.area_name}
        </div>
      )}
      <div>
        <span className="text-gray-500">Grid Ref:</span> {trig.osgb_gridref || "—"}
      </div>
      <div>
        <span className="text-gray-500">E/N:</span> {trig.osgb_eastings.toFixed(1)},{" "}
        {trig.osgb_northings.toFixed(1)}
      </div>
      {trig.osgb_height != null && (
        <div>
          <span className="text-gray-500">Height:</span> {trig.osgb_height}m
        </div>
      )}
      <div>
        <span className="text-gray-500">FB:</span> {trig.fb_number || "—"}{" "}
        <span className="text-gray-500 ml-2">Stn:</span> {trig.stn_number || "—"}
      </div>
      <div>
        <span className="text-gray-500">Condition:</span> {trig.condition}{" "}
        <span className="text-gray-500 ml-2">Historic use:</span> {trig.historic_use}
      </div>
    </div>
  );
}

// ============================================================================
// Comparison Card Component
// ============================================================================

interface ComparisonCardProps {
  item: IrelandComparisonItem;
  onApply?: (trigId: number, csvRowIndex: number) => void;
  onCreate?: (csvRowIndex: number) => void;
  applying: boolean;
}

function ComparisonCard({ item, onApply, onCreate, applying }: ComparisonCardProps) {
  const [expanded, setExpanded] = useState(false);
  const config = CATEGORY_CONFIG[item.category] ?? CATEGORY_CONFIG.matched_identical;
  const Icon = config.icon;

  const title =
    item.csv_data?.station_name ??
    item.db_data?.name ??
    "Unknown";

  const subtitle =
    item.csv_data?.grid_ref ??
    item.db_data?.osgb_gridref ??
    "";

  return (
    <div
      className={`rounded-lg border ${config.borderColour} ${config.bgColour} overflow-hidden`}
    >
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full px-4 py-3 flex items-center gap-3 text-left hover:bg-black/5 dark:hover:bg-white/5 transition-colors"
      >
        <Icon className={`w-5 h-5 flex-shrink-0 ${config.colour}`} />
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-900 dark:text-gray-100">
              {title}
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${config.bgColour} ${config.colour} border ${config.borderColour}`}
            >
              {config.label}
            </span>
            {item.db_data?.has_non_irish_gridref && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-orange-100 dark:bg-orange-900/30 text-orange-700 dark:text-orange-400 border border-orange-300 dark:border-orange-700">
                Non-Irish gridref
              </span>
            )}
            {item.distance_metres != null && (
              <span className="text-xs text-gray-500 dark:text-gray-400">
                {item.distance_metres.toFixed(1)}m
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
            {subtitle && <span className="font-mono mr-2">{subtitle}</span>}
            {item.description}
          </p>
        </div>
        {expanded ? (
          <ChevronUp className="w-4 h-4 text-gray-400" />
        ) : (
          <ChevronDown className="w-4 h-4 text-gray-400" />
        )}
      </button>

      {expanded && (
        <div className="px-4 pb-4 pt-2 border-t border-gray-200 dark:border-gray-700 space-y-3">
          {/* CSV Data */}
          {item.csv_data && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
                CSV Data (Ireland25)
              </h4>
              <div className="bg-white dark:bg-gray-900 rounded p-2 text-sm font-mono space-y-1">
                <div>
                  <span className="text-gray-500">Name:</span>{" "}
                  {item.csv_data.station_name}
                </div>
                <div>
                  <span className="text-gray-500">OSI/NI No:</span>{" "}
                  {item.csv_data.osi_ni_no || "—"}
                </div>
                <div>
                  <span className="text-gray-500">Grid Ref:</span>{" "}
                  {item.csv_data.grid_ref}
                </div>
                <div>
                  <span className="text-gray-500">E/N:</span>{" "}
                  {item.csv_data.eastings.toFixed(1)},{" "}
                  {item.csv_data.northings.toFixed(1)}
                </div>
                {item.csv_data.height != null && (
                  <div>
                    <span className="text-gray-500">Height:</span>{" "}
                    {item.csv_data.height}m
                  </div>
                )}
                <div>
                  <span className="text-gray-500">FB:</span>{" "}
                  {item.csv_data.fb_number || "—"}
                  <span className="text-gray-500 ml-2">Ord:</span>{" "}
                  {item.csv_data.order || "—"}
                  <span className="text-gray-500 ml-2">DR:</span>{" "}
                  {item.csv_data.dr || "—"}
                </div>
                {item.csv_data.date_built && (
                  <div>
                    <span className="text-gray-500">Date built:</span>{" "}
                    {item.csv_data.date_built}
                  </div>
                )}
                {item.csv_data.notes && (
                  <div>
                    <span className="text-gray-500">Notes:</span>{" "}
                    {item.csv_data.notes}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* DB Data */}
          {item.db_data && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
                Database Record
              </h4>
              <DBTrigInfo trig={item.db_data} />
            </div>
          )}

          {/* Additional matches (ambiguous) */}
          {item.additional_db_matches.length > 0 && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-red-500 dark:text-red-400 mb-1">
                Additional DB Matches ({item.additional_db_matches.length})
              </h4>
              <div className="space-y-2">
                {item.additional_db_matches.map((match) => (
                  <DBTrigInfo key={match.trig_id} trig={match} />
                ))}
              </div>
            </div>
          )}

          {/* Field differences */}
          {item.differences.length > 0 && (
            <FieldDifferenceTable differences={item.differences} />
          )}

          {/* Action Buttons */}
          <div className="flex gap-2 mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
            {/* Apply button: for matched_different and ambiguous with a primary match */}
            {item.csv_data &&
              item.db_data &&
              (item.category === "matched_different" ||
                item.category === "ambiguous") && (
                <Button
                  onClick={() =>
                    onApply?.(
                      item.db_data!.trig_id,
                      item.csv_data!.csv_row_index
                    )
                  }
                  disabled={applying}
                  className="text-sm"
                >
                  {applying ? (
                    <Spinner size="sm" />
                  ) : (
                    <>
                      <ArrowRightCircle className="w-4 h-4 mr-1" />
                      Apply CSV to {item.db_data.waypoint}
                    </>
                  )}
                </Button>
              )}

            {/* Create button: for new_in_csv */}
            {item.category === "new_in_csv" && item.csv_data && (
              <Button
                onClick={() => onCreate?.(item.csv_data!.csv_row_index)}
                disabled={applying}
                className="text-sm"
              >
                {applying ? (
                  <Spinner size="sm" />
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-1" />
                    Create Trig
                  </>
                )}
              </Button>
            )}

            {/* Link to trig detail */}
            {item.db_data && (
              <a
                href={`/admin/trigs/${item.db_data.trig_id}/edit`}
                className="inline-flex items-center gap-1 px-3 py-1.5 text-sm rounded-md border border-gray-300 dark:border-gray-600 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                Edit {item.db_data.waypoint}
              </a>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ============================================================================
// Summary Card Component
// ============================================================================

interface SummaryCardProps {
  title: string;
  count: number;
  icon: React.ComponentType<{ className?: string }>;
  colour: string;
  bgColour: string;
}

function SummaryCard({
  title,
  count,
  icon: Icon,
  colour,
  bgColour,
}: SummaryCardProps) {
  return (
    <div className={`rounded-lg p-4 ${bgColour}`}>
      <div className="flex items-center gap-3">
        <Icon className={`w-6 h-6 ${colour}`} />
        <div>
          <div className={`text-2xl font-bold ${colour}`}>{count}</div>
          <div className="text-sm text-gray-600 dark:text-gray-400">{title}</div>
        </div>
      </div>
    </div>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function IrelandImport() {
  const { getAccessTokenSilently, isAuthenticated, loginWithRedirect } =
    useAuth0();

  const [comparison, setComparison] =
    useState<IrelandImportComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [applying, setApplying] = useState(false);

  // Filter state - show actionable items by default
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(["ambiguous", "matched_different", "new_in_csv", "orphan_in_db"])
  );

  const fetchData = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      const data = await fetchIrelandImportComparison(token);
      setComparison(data);
    } catch (err) {
      console.error("Error fetching Ireland import comparison:", err);
      setError(
        err instanceof Error ? err.message : "Failed to load comparison"
      );
    } finally {
      setLoading(false);
    }
  }, [getAccessTokenSilently]);

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated, fetchData]);

  const handleApply = async (trigId: number, csvRowIndex: number) => {
    try {
      setApplying(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      await applyIrelandImportCSV(token, trigId, csvRowIndex);
      toast.success("CSV data applied successfully");
      // Refresh comparison data
      await fetchData();
    } catch (err) {
      console.error("Error applying CSV data:", err);
      toast.error(
        err instanceof Error ? err.message : "Failed to apply CSV data"
      );
    } finally {
      setApplying(false);
    }
  };

  const handleCreate = async (csvRowIndex: number) => {
    try {
      setApplying(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      const result = await createTrigFromIrelandCSV(token, csvRowIndex);
      toast.success(`Created trig ${result.waypoint}`);
      await fetchData();
    } catch (err) {
      console.error("Error creating trig:", err);
      toast.error(
        err instanceof Error ? err.message : "Failed to create trig"
      );
    } finally {
      setApplying(false);
    }
  };

  const handleBulkCreate = async () => {
    if (
      !comparison ||
      !window.confirm(
        `Create ${comparison.new_in_csv_count} new trigpoints from all unmatched CSV rows?`
      )
    )
      return;

    try {
      setApplying(true);
      const token = await getAccessTokenSilently({
        authorizationParams: ADMIN_AUTH_PARAMS,
      });
      const result = await bulkCreateTrigsFromIrelandCSV(token);
      if (result.failed_count > 0) {
        toast.error(
          `Created ${result.created_count}, failed ${result.failed_count} of ${result.total_new_in_csv}`
        );
      } else {
        toast.success(
          `Created ${result.created_count} new trigpoints`
        );
      }
      await fetchData();
    } catch (err) {
      console.error("Error bulk creating trigs:", err);
      toast.error(
        err instanceof Error ? err.message : "Failed to bulk create trigs"
      );
    } finally {
      setApplying(false);
    }
  };

  const toggleFilter = (filterType: string) => {
    setActiveFilters((prev) => {
      const next = new Set(prev);
      if (next.has(filterType)) {
        next.delete(filterType);
      } else {
        next.add(filterType);
      }
      return next;
    });
  };

  // Filter items
  const filteredItems =
    comparison?.items.filter((item) => activeFilters.has(item.category)) ?? [];

  // Render
  if (!isAuthenticated) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <Card className="p-8 text-center">
            <h2 className="text-xl font-semibold mb-4">
              Authentication Required
            </h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">
              You must be logged in as an administrator to access this page.
            </p>
            <Button onClick={() => loginWithRedirect()}>Log In</Button>
          </Card>
        </div>
      </Layout>
    );
  }

  if (loading) {
    return (
      <Layout>
        <title>Ireland Import | Admin | TrigpointingUK</title>
        <div className="max-w-6xl mx-auto py-8 px-4">
          <div className="flex items-center justify-center py-12">
            <Spinner size="lg" />
            <span className="ml-3 text-gray-600 dark:text-gray-400">
              Comparing Ireland25 CSV with database...
            </span>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <title>Ireland Import | Admin | TrigpointingUK</title>
        <div className="max-w-6xl mx-auto py-8 px-4">
          <Card className="p-8 text-center">
            <h2 className="text-xl font-semibold text-red-600 mb-4">Error</h2>
            <p className="text-gray-600 dark:text-gray-400 mb-4">{error}</p>
            <Button onClick={() => fetchData()}>Retry</Button>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <title>Ireland Import | Admin | TrigpointingUK</title>
      <div className="max-w-6xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3">
              <MapPin className="w-8 h-8 text-trig-green-600" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                Ireland Import
              </h1>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Compare Ireland25 CSV with Irish trigpoints in the database
            </p>
          </div>
          <div className="flex items-center gap-2">
            {comparison && comparison.new_in_csv_count > 0 && (
              <Button
                onClick={handleBulkCreate}
                disabled={loading || applying}
                className="bg-blue-600 hover:bg-blue-700 text-white"
              >
                {applying ? (
                  <Spinner size="sm" />
                ) : (
                  <>
                    <Plus className="w-4 h-4 mr-1" />
                    Create All {comparison.new_in_csv_count} New
                  </>
                )}
              </Button>
            )}
            <Button onClick={() => fetchData()} disabled={loading}>
              Refresh
            </Button>
          </div>
        </div>

        {comparison && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
              <SummaryCard
                title="CSV Rows"
                count={comparison.csv_count}
                icon={MapPin}
                colour="text-gray-700 dark:text-gray-300"
                bgColour="bg-gray-100 dark:bg-gray-800"
              />
              <SummaryCard
                title="Irish DB Trigs"
                count={comparison.db_irish_count}
                icon={MapPin}
                colour="text-gray-700 dark:text-gray-300"
                bgColour="bg-gray-100 dark:bg-gray-800"
              />
              <SummaryCard
                title="Matched"
                count={
                  comparison.matched_identical_count +
                  comparison.matched_different_count
                }
                icon={CheckCircle2}
                colour="text-green-700 dark:text-green-400"
                bgColour="bg-green-50 dark:bg-green-900/20"
              />
              <SummaryCard
                title="Differences"
                count={
                  comparison.matched_different_count +
                  comparison.ambiguous_count +
                  comparison.new_in_csv_count +
                  comparison.orphan_in_db_count
                }
                icon={AlertTriangle}
                colour="text-amber-700 dark:text-amber-400"
                bgColour="bg-amber-50 dark:bg-amber-900/20"
              />
            </div>

            {/* Non-Irish gridref warning banner */}
            {comparison.non_irish_gridref_count > 0 && (
              <Card className="p-4 mb-6 bg-orange-50 dark:bg-orange-900/20 border-orange-200 dark:border-orange-800">
                <div className="flex items-start gap-3">
                  <AlertTriangle className="w-5 h-5 text-orange-600 dark:text-orange-400 flex-shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm text-orange-800 dark:text-orange-200">
                      <strong>{comparison.non_irish_gridref_count}</strong> Irish
                      trig(s) in the database have grid references that are not in
                      Irish Grid format. These are flagged with an orange badge.
                    </p>
                  </div>
                </div>
              </Card>
            )}

            {/* Filter Buttons */}
            <div className="flex flex-wrap gap-2 mb-4">
              {Object.entries(CATEGORY_CONFIG).map(([type, config]) => {
                const countMap: Record<string, number> = {
                  ambiguous: comparison.ambiguous_count,
                  matched_different: comparison.matched_different_count,
                  new_in_csv: comparison.new_in_csv_count,
                  orphan_in_db: comparison.orphan_in_db_count,
                  matched_identical: comparison.matched_identical_count,
                };
                const count = countMap[type] ?? 0;
                const isActive = activeFilters.has(type);
                const FilterIcon = config.icon;

                return (
                  <button
                    key={type}
                    onClick={() => toggleFilter(type)}
                    className={`
                      flex items-center gap-2 px-3 py-1.5 rounded-full text-sm font-medium
                      transition-all border
                      ${
                        isActive
                          ? `${config.bgColour} ${config.colour} ${config.borderColour}`
                          : "bg-gray-100 dark:bg-gray-800 text-gray-500 border-gray-200 dark:border-gray-700 opacity-60"
                      }
                    `}
                  >
                    <FilterIcon className="w-4 h-4" />
                    {config.label}
                    <span
                      className={`
                        px-1.5 py-0.5 rounded text-xs
                        ${
                          isActive
                            ? "bg-black/10 dark:bg-white/10"
                            : "bg-gray-200 dark:bg-gray-700"
                        }
                      `}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Items List */}
            {filteredItems.length === 0 ? (
              <Card className="p-8 text-center">
                <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                  {comparison.items.length === 0
                    ? "All Records Match!"
                    : "No Items Match Filters"}
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  {comparison.items.length === 0
                    ? "All Ireland25 CSV records match the database."
                    : "Try enabling more filters to see items."}
                </p>
              </Card>
            ) : (
              <div className="space-y-3">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Showing {filteredItems.length} of {comparison.items.length}{" "}
                  items
                </div>
                {filteredItems.map((item, idx) => (
                  <ComparisonCard
                    key={`${item.category}-${item.csv_data?.csv_row_index ?? item.db_data?.trig_id ?? idx}`}
                    item={item}
                    onApply={handleApply}
                    onCreate={handleCreate}
                    applying={applying}
                  />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}

