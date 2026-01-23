import { useState, useEffect, useCallback } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import {
  RefreshCw,
  CheckCircle2,
  AlertTriangle,
  XCircle,
  HelpCircle,
  ExternalLink,
  ChevronDown,
  ChevronUp,
  Satellite,
} from "lucide-react";
import toast from "react-hot-toast";

import Layout from "../../components/layout/Layout";
import Card from "../../components/ui/Card";
import Button from "../../components/ui/Button";
import Spinner from "../../components/ui/Spinner";
import {
  OSNetComparisonResponse,
  StationDifference,
  fetchOSNetComparison,
} from "../../lib/api";

const AUTH0_AUDIENCE = import.meta.env.VITE_AUTH0_AUDIENCE as string | undefined;
const ADMIN_SCOPE = "api:admin";
const BASE_SCOPES = "openid profile email api:write api:read-pii offline_access";
const ADMIN_AUTH_PARAMS: { scope: string; audience?: string } = AUTH0_AUDIENCE
  ? { audience: AUTH0_AUDIENCE, scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` }
  : { scope: `${BASE_SCOPES} ${ADMIN_SCOPE}` };

// ============================================================================
// Difference Type Icons and Colours
// ============================================================================

const DIFFERENCE_TYPE_CONFIG: Record<string, {
  icon: React.ElementType;
  colour: string;
  bgColour: string;
  borderColour: string;
  label: string;
  description: string;
}> = {
  new_in_osnet: {
    icon: AlertTriangle,
    colour: "text-amber-600 dark:text-amber-400",
    bgColour: "bg-amber-50 dark:bg-amber-900/20",
    borderColour: "border-amber-200 dark:border-amber-800",
    label: "New in OS Net",
    description: "Current station in OS Net not in the database (action needed)",
  },
  missing_from_osnet: {
    icon: XCircle,
    colour: "text-red-600 dark:text-red-400",
    bgColour: "bg-red-50 dark:bg-red-900/20",
    borderColour: "border-red-200 dark:border-red-800",
    label: "Missing from OS Net",
    description: "Station in database but not found anywhere in OS Net file",
  },
  coordinate_mismatch: {
    icon: HelpCircle,
    colour: "text-blue-600 dark:text-blue-400",
    bgColour: "bg-blue-50 dark:bg-blue-900/20",
    borderColour: "border-blue-200 dark:border-blue-800",
    label: "Coordinate Mismatch",
    description: "Coordinates differ by more than 5 metres",
  },
  unmatched_db: {
    icon: HelpCircle,
    colour: "text-gray-600 dark:text-gray-400",
    bgColour: "bg-gray-50 dark:bg-gray-800",
    borderColour: "border-gray-200 dark:border-gray-700",
    label: "Unmatched (No Station Code)",
    description: "Database active station without stn_number_active set",
  },
  destroyed_not_in_db: {
    icon: XCircle,
    colour: "text-purple-600 dark:text-purple-400",
    bgColour: "bg-purple-50 dark:bg-purple-900/20",
    borderColour: "border-purple-200 dark:border-purple-800",
    label: "Destroyed (Not in DB)",
    description: "Station marked destroyed in OS Net, not in database (informational)",
  },
  legacy_not_in_db: {
    icon: HelpCircle,
    colour: "text-slate-600 dark:text-slate-400",
    bgColour: "bg-slate-50 dark:bg-slate-900/20",
    borderColour: "border-slate-200 dark:border-slate-700",
    label: "Legacy (Not in DB)",
    description: "Legacy v2001 station not in database (informational)",
  },
};

// ============================================================================
// Difference Card Component
// ============================================================================

interface DifferenceCardProps {
  difference: StationDifference;
}

function DifferenceCard({ difference }: DifferenceCardProps) {
  const [expanded, setExpanded] = useState(false);
  const config = DIFFERENCE_TYPE_CONFIG[difference.difference_type];
  const Icon = config.icon;

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
            <span className="font-mono font-semibold text-gray-900 dark:text-gray-100">
              {difference.station_code || "—"}
            </span>
            <span
              className={`text-xs px-2 py-0.5 rounded-full ${config.bgColour} ${config.colour} border ${config.borderColour}`}
            >
              {config.label}
            </span>
            {difference.osnet_section_name && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-400">
                {difference.osnet_section_name}
              </span>
            )}
          </div>
          <p className="text-sm text-gray-600 dark:text-gray-400 truncate">
            {difference.description}
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
          {difference.distance_metres != null && (
            <div className="text-sm">
              <span className="font-medium text-gray-700 dark:text-gray-300">
                Distance:
              </span>{" "}
              <span className="text-gray-600 dark:text-gray-400">
                {difference.distance_metres.toFixed(1)} metres
              </span>
            </div>
          )}

          {difference.osnet_data && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
                OS Net Data
              </h4>
              <div className="bg-white dark:bg-gray-900 rounded p-2 text-sm font-mono space-y-1">
                {difference.osnet_data.code && (
                  <div>
                    <span className="text-gray-500">Code:</span>{" "}
                    {difference.osnet_data.code}
                  </div>
                )}
                {difference.osnet_data.easting != null && (
                  <div>
                    <span className="text-gray-500">Easting:</span>{" "}
                    {difference.osnet_data.easting.toFixed(3)}
                  </div>
                )}
                {difference.osnet_data.northing != null && (
                  <div>
                    <span className="text-gray-500">Northing:</span>{" "}
                    {difference.osnet_data.northing.toFixed(3)}
                  </div>
                )}
                {difference.osnet_data.gridref && (
                  <div>
                    <span className="text-gray-500">Grid Ref:</span>{" "}
                    {difference.osnet_data.gridref}
                  </div>
                )}
                {difference.osnet_data.height != null && (
                  <div>
                    <span className="text-gray-500">Height:</span>{" "}
                    {difference.osnet_data.height.toFixed(3)}m
                  </div>
                )}
                {difference.osnet_data.lat_dms && (
                  <div>
                    <span className="text-gray-500">Lat:</span>{" "}
                    {difference.osnet_data.lat_dms}
                  </div>
                )}
                {difference.osnet_data.lon_dms && (
                  <div>
                    <span className="text-gray-500">Lon:</span>{" "}
                    {difference.osnet_data.lon_dms}
                  </div>
                )}
              </div>
            </div>
          )}

          {difference.db_data && (
            <div>
              <h4 className="text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400 mb-1">
                Database Data
              </h4>
              <div className="bg-white dark:bg-gray-900 rounded p-2 text-sm font-mono space-y-1">
                {difference.db_data.trig_id && (
                  <div>
                    <span className="text-gray-500">Trig ID:</span>{" "}
                    <a
                      href={`/trigs/${difference.db_data.trig_id}`}
                      className="text-trig-green-600 hover:underline"
                    >
                      {difference.db_data.trig_id}
                    </a>
                  </div>
                )}
                {difference.db_data.waypoint && (
                  <div>
                    <span className="text-gray-500">Waypoint:</span>{" "}
                    {difference.db_data.waypoint}
                  </div>
                )}
                {difference.db_data.name && (
                  <div>
                    <span className="text-gray-500">Name:</span>{" "}
                    {difference.db_data.name}
                  </div>
                )}
                {difference.db_data.stn_number_active && (
                  <div>
                    <span className="text-gray-500">Station Code:</span>{" "}
                    {difference.db_data.stn_number_active}
                  </div>
                )}
                {difference.db_data.easting !== undefined && (
                  <div>
                    <span className="text-gray-500">Easting:</span>{" "}
                    {difference.db_data.easting}
                  </div>
                )}
                {difference.db_data.northing !== undefined && (
                  <div>
                    <span className="text-gray-500">Northing:</span>{" "}
                    {difference.db_data.northing}
                  </div>
                )}
                {difference.db_data.gridref && (
                  <div>
                    <span className="text-gray-500">Grid Ref:</span>{" "}
                    {difference.db_data.gridref}
                  </div>
                )}
              </div>
            </div>
          )}
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
  icon: React.ElementType;
  colour: string;
  bgColour: string;
}

function SummaryCard({ title, count, icon: Icon, colour, bgColour }: SummaryCardProps) {
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
// Changelog Section Component
// ============================================================================

interface ChangelogSectionProps {
  entries: string[];
}

function ChangelogSection({ entries }: ChangelogSectionProps) {
  const [expanded, setExpanded] = useState(false);

  if (entries.length === 0) {
    return null;
  }

  const displayEntries = expanded ? entries : entries.slice(0, 5);

  return (
    <Card className="p-4">
      <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-3">
        Recent OS Net Changes
      </h3>
      <div className="space-y-2">
        {displayEntries.map((entry, idx) => (
          <div
            key={idx}
            className="text-sm text-gray-600 dark:text-gray-400 pl-3 border-l-2 border-gray-300 dark:border-gray-600"
          >
            {entry}
          </div>
        ))}
      </div>
      {entries.length > 5 && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="mt-3 text-sm text-trig-green-600 hover:text-trig-green-700 dark:text-trig-green-400"
        >
          {expanded ? "Show less" : `Show ${entries.length - 5} more`}
        </button>
      )}
    </Card>
  );
}

// ============================================================================
// Main Component
// ============================================================================

export default function OSNetComparison() {
  const { getAccessTokenSilently, isAuthenticated, loginWithRedirect } = useAuth0();

  const [comparison, setComparison] = useState<OSNetComparisonResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [refreshing, setRefreshing] = useState(false);

  // Filter state - by default show actionable items, hide informational (destroyed/legacy)
  const [activeFilters, setActiveFilters] = useState<Set<string>>(
    new Set(["new_in_osnet", "missing_from_osnet", "coordinate_mismatch", "unmatched_db"])
  );

  const fetchData = useCallback(
    async (forceRefresh: boolean = false) => {
      try {
        if (forceRefresh) {
          setRefreshing(true);
        } else {
          setLoading(true);
        }
        setError(null);

        const token = await getAccessTokenSilently({
          authorizationParams: ADMIN_AUTH_PARAMS,
        });
        const data = await fetchOSNetComparison(token, forceRefresh);
        setComparison(data);
      } catch (err) {
        console.error("Error fetching OS Net comparison:", err);
        setError(err instanceof Error ? err.message : "Failed to load comparison");
      } finally {
        setLoading(false);
        setRefreshing(false);
      }
    },
    [getAccessTokenSilently]
  );

  useEffect(() => {
    if (isAuthenticated) {
      fetchData();
    }
  }, [isAuthenticated, fetchData]);

  const handleRefresh = async () => {
    await fetchData(true);
    toast.success("OS Net data refreshed");
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

  // Filter differences
  const filteredDifferences =
    comparison?.differences.filter((d) => activeFilters.has(d.difference_type)) ?? [];

  // Render
  if (!isAuthenticated) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto py-8 px-4">
          <Card className="p-8 text-center">
            <h2 className="text-xl font-semibold mb-4">Authentication Required</h2>
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
        <title>OS Net Comparison | Admin | TrigpointingUK</title>
        <div className="max-w-6xl mx-auto py-8 px-4">
          <div className="flex items-center justify-center py-12">
            <Spinner size="lg" />
            <span className="ml-3 text-gray-600 dark:text-gray-400">
              Comparing OS Net data with database...
            </span>
          </div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <title>OS Net Comparison | Admin | TrigpointingUK</title>
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
      <title>OS Net Comparison | Admin | TrigpointingUK</title>
      <div className="max-w-6xl mx-auto py-8 px-4">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <div className="flex items-center gap-3">
              <Satellite className="w-8 h-8 text-trig-green-600" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
                OS Net Comparison
              </h1>
            </div>
            <p className="text-gray-600 dark:text-gray-400 mt-1">
              Compare OS Net active GPS stations with database records
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button onClick={handleRefresh} disabled={refreshing}>
              {refreshing ? (
                <>
                  <span className="mr-2"><Spinner size="sm" /></span>
                  Refreshing...
                </>
              ) : (
                <>
                  <RefreshCw className="w-4 h-4 mr-2" />
                  Refresh
                </>
              )}
            </Button>
          </div>
        </div>

        {comparison && (
          <>
            {/* Summary Cards */}
            <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-6">
              <SummaryCard
                title="OS Net Current"
                count={comparison.osnet_current_count}
                icon={Satellite}
                colour="text-gray-700 dark:text-gray-300"
                bgColour="bg-gray-100 dark:bg-gray-800"
              />
              <SummaryCard
                title="OS Net Destroyed"
                count={comparison.osnet_destroyed_count}
                icon={XCircle}
                colour="text-purple-700 dark:text-purple-400"
                bgColour="bg-purple-50 dark:bg-purple-900/20"
              />
              <SummaryCard
                title="DB Active Stations"
                count={comparison.db_count}
                icon={CheckCircle2}
                colour="text-gray-700 dark:text-gray-300"
                bgColour="bg-gray-100 dark:bg-gray-800"
              />
              <SummaryCard
                title="Matched"
                count={comparison.matched_count}
                icon={CheckCircle2}
                colour="text-green-700 dark:text-green-400"
                bgColour="bg-green-50 dark:bg-green-900/20"
              />
              <SummaryCard
                title="Differences"
                count={comparison.differences.length}
                icon={AlertTriangle}
                colour="text-amber-700 dark:text-amber-400"
                bgColour="bg-amber-50 dark:bg-amber-900/20"
              />
            </div>

            {/* Info Banner */}
            <Card className="p-4 mb-6 bg-blue-50 dark:bg-blue-900/20 border-blue-200 dark:border-blue-800">
              <div className="flex items-start gap-3">
                <ExternalLink className="w-5 h-5 text-blue-600 dark:text-blue-400 flex-shrink-0 mt-0.5" />
                <div>
                  <p className="text-sm text-blue-800 dark:text-blue-200">
                    Data fetched from{" "}
                    <a
                      href="https://www.ordnancesurvey.co.uk/documents/resources/osnet-coordinates-file.txt"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="underline hover:no-underline"
                    >
                      OS Net coordinates file
                    </a>{" "}
                    at{" "}
                    {new Date(comparison.osnet_fetch_time).toLocaleString("en-GB", {
                      dateStyle: "medium",
                      timeStyle: "short",
                    })}
                    . Data is cached for 1 hour.
                  </p>
                </div>
              </div>
            </Card>

            {/* Changelog */}
            {comparison.changelog_entries.length > 0 && (
              <div className="mb-6">
                <ChangelogSection entries={comparison.changelog_entries} />
              </div>
            )}

            {/* Filter Buttons */}
            <div className="flex flex-wrap gap-2 mb-4">
              {Object.entries(DIFFERENCE_TYPE_CONFIG).map(([type, config]) => {
                const countMap: Record<string, number> = {
                  new_in_osnet: comparison.new_in_osnet_count,
                  missing_from_osnet: comparison.missing_from_osnet_count,
                  coordinate_mismatch: comparison.coordinate_mismatch_count,
                  unmatched_db: comparison.unmatched_db_count,
                  destroyed_not_in_db: comparison.destroyed_not_in_db_count,
                  legacy_not_in_db: comparison.legacy_not_in_db_count,
                };
                const count = countMap[type] ?? 0;

                const isActive = activeFilters.has(type);
                const Icon = config.icon;

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
                    <Icon className="w-4 h-4" />
                    {config.label}
                    <span
                      className={`
                      px-1.5 py-0.5 rounded text-xs
                      ${isActive ? "bg-black/10 dark:bg-white/10" : "bg-gray-200 dark:bg-gray-700"}
                    `}
                    >
                      {count}
                    </span>
                  </button>
                );
              })}
            </div>

            {/* Differences List */}
            {filteredDifferences.length === 0 ? (
              <Card className="p-8 text-center">
                <CheckCircle2 className="w-12 h-12 text-green-500 mx-auto mb-4" />
                <h3 className="text-lg font-semibold text-gray-800 dark:text-gray-100 mb-2">
                  {comparison.differences.length === 0
                    ? "All Stations Match!"
                    : "No Differences Match Filters"}
                </h3>
                <p className="text-gray-600 dark:text-gray-400">
                  {comparison.differences.length === 0
                    ? "All OS Net stations are correctly represented in the database."
                    : "Try enabling more filters to see differences."}
                </p>
              </Card>
            ) : (
              <div className="space-y-3">
                <div className="text-sm text-gray-500 dark:text-gray-400">
                  Showing {filteredDifferences.length} of {comparison.differences.length}{" "}
                  differences
                </div>
                {filteredDifferences.map((diff, idx) => (
                  <DifferenceCard key={`${diff.difference_type}-${diff.station_code}-${idx}`} difference={diff} />
                ))}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}

