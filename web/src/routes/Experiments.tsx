import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import {
  fetchCoordinateDiscrepancies,
  CoordinateDiscrepancyItem,
  CoordinateDiscrepancySortField,
  MovedFilter,
} from "../lib/api";
import { ChevronUp, ChevronDown, ArrowUpDown } from "lucide-react";

const CONDITION_ICON_BASE = "/icons/conditions/";

type SortOrder = "asc" | "desc";

interface SortState {
  field: CoordinateDiscrepancySortField;
  order: SortOrder;
}

/**
 * Sortable column header component
 */
function SortableHeader({
  field,
  label,
  currentSort,
  onSort,
}: {
  field: CoordinateDiscrepancySortField;
  label: string;
  currentSort: SortState;
  onSort: (field: CoordinateDiscrepancySortField) => void;
}) {
  const isActive = currentSort.field === field;

  return (
    <button
      onClick={() => onSort(field)}
      className={`flex items-center gap-1 font-semibold hover:text-trig-green-600 dark:hover:text-trig-green-400 transition-colors ${
        isActive ? "text-trig-green-600 dark:text-trig-green-400" : ""
      }`}
    >
      {label}
      {isActive ? (
        currentSort.order === "asc" ? (
          <ChevronUp className="w-4 h-4" />
        ) : (
          <ChevronDown className="w-4 h-4" />
        )
      ) : (
        <ArrowUpDown className="w-4 h-4 opacity-50" />
      )}
    </button>
  );
}

/**
 * Format distance value for display
 */
function formatDistance(value: number | null): string {
  if (value === null || value === undefined) {
    return "—";
  }
  if (value < 0.1) {
    return `${(value * 1000).toFixed(1)} mm`;
  }
  if (value < 1) {
    return `${(value * 100).toFixed(1)} cm`;
  }
  if (value < 1000) {
    return `${value.toFixed(2)} m`;
  }
  return `${(value / 1000).toFixed(2)} km`;
}

/**
 * Get colour class based on distance value
 */
function getDistanceColourClass(value: number | null): string {
  if (value === null) return "text-gray-400 dark:text-gray-500";
  if (value < 0.1) return "text-green-600 dark:text-green-400";
  if (value < 1) return "text-yellow-600 dark:text-yellow-400";
  if (value < 10) return "text-orange-600 dark:text-orange-400";
  return "text-red-600 dark:text-red-400";
}

// Valid sort fields for validation
const VALID_SORT_FIELDS: CoordinateDiscrepancySortField[] = [
  "waypoint",
  "name",
  "dist_wgs_osgb",
  "dist_osgb_osgb",
  "dist_wgs_original",
];

// Valid moved filter values
const VALID_MOVED_FILTERS: MovedFilter[] = ["all", "exclude_moved", "only_moved"];

export default function Experiments() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [items, setItems] = useState<CoordinateDiscrepancyItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [totalPages, setTotalPages] = useState(1);
  const [total, setTotal] = useState(0);
  const perPage = 50;

  // Parse URL parameters with defaults
  const page = Math.max(1, parseInt(searchParams.get("page") || "1", 10) || 1);
  const sortField = useMemo((): CoordinateDiscrepancySortField => {
    const param = searchParams.get("sort");
    return VALID_SORT_FIELDS.includes(param as CoordinateDiscrepancySortField)
      ? (param as CoordinateDiscrepancySortField)
      : "dist_wgs_osgb";
  }, [searchParams]);
  const sortOrder: SortOrder = searchParams.get("order") === "asc" ? "asc" : "desc";
  const sort: SortState = useMemo(
    () => ({ field: sortField, order: sortOrder }),
    [sortField, sortOrder]
  );
  const excludeIrish = searchParams.get("excludeIrish") === "true";
  const movedFilter: MovedFilter = useMemo((): MovedFilter => {
    const param = searchParams.get("moved");
    return VALID_MOVED_FILTERS.includes(param as MovedFilter)
      ? (param as MovedFilter)
      : "all";
  }, [searchParams]);

  // Helper to update URL params while preserving other params
  const updateParams = useCallback(
    (updates: Record<string, string | null>) => {
      setSearchParams((prev) => {
        const newParams = new URLSearchParams(prev);
        for (const [key, value] of Object.entries(updates)) {
          if (value === null) {
            newParams.delete(key);
          } else {
            newParams.set(key, value);
          }
        }
        return newParams;
      });
    },
    [setSearchParams]
  );

  const setPage = useCallback(
    (newPage: number | ((prev: number) => number)) => {
      const resolvedPage = typeof newPage === "function" ? newPage(page) : newPage;
      updateParams({ page: resolvedPage === 1 ? null : String(resolvedPage) });
    },
    [page, updateParams]
  );

  const setSort = useCallback(
    (newSort: SortState | ((prev: SortState) => SortState)) => {
      const resolvedSort = typeof newSort === "function" ? newSort(sort) : newSort;
      updateParams({
        sort: resolvedSort.field === "dist_wgs_osgb" ? null : resolvedSort.field,
        order: resolvedSort.order === "desc" ? null : resolvedSort.order,
        page: null, // Reset page when sorting changes
      });
    },
    [sort, updateParams]
  );

  const setExcludeIrish = useCallback(
    (value: boolean) => {
      updateParams({
        excludeIrish: value ? "true" : null,
        page: null, // Reset page when filter changes
      });
    },
    [updateParams]
  );

  const setMovedFilter = useCallback(
    (value: MovedFilter) => {
      updateParams({
        moved: value === "all" ? null : value,
        page: null, // Reset page when filter changes
      });
    },
    [updateParams]
  );

  const fetchData = useCallback(async () => {
    setIsLoading(true);
    setError(null);

    try {
      const response = await fetchCoordinateDiscrepancies({
        page,
        per_page: perPage,
        sort_by: sort.field,
        sort_order: sort.order,
        exclude_irish: excludeIrish,
        moved_filter: movedFilter,
      });

      setItems(response.items);
      setTotalPages(response.total_pages);
      setTotal(response.total);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
    } finally {
      setIsLoading(false);
    }
  }, [page, sort, excludeIrish, movedFilter]);

  useEffect(() => {
    // eslint-disable-next-line react-hooks/set-state-in-effect -- one-shot state sync on data load; re-render cost negligible (won't fix)
    fetchData();
  }, [fetchData]);

  const handleSort = (field: CoordinateDiscrepancySortField) => {
    setSort((prev) => ({
      field,
      order: prev.field === field && prev.order === "desc" ? "asc" : "desc",
    }));
    // Note: page reset is handled in setSort
  };

  return (
    <>
      <title>Experiments | TrigpointingUK</title>
      <div className="max-w-6xl mx-auto">
        <Card>
          <div className="p-6">
            <h1 className="text-2xl font-bold text-gray-800 dark:text-gray-100 mb-2">
              Coordinate Discrepancy Monitor
            </h1>
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Monitoring coordinate consistency between WGS84, OSGB36, and attrval
              sources. Click column headers to sort.
            </p>

            {/* Legend */}
            <div className="flex flex-wrap gap-4 mb-6 text-sm">
              <div className="flex items-center gap-2">
                <span className="font-medium">dist_wgs_osgb:</span>
                <span className="text-gray-600 dark:text-gray-400">
                  WGS84→OSTN15 vs trig.osgb*
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">dist_osgb_osgb:</span>
                <span className="text-gray-600 dark:text-gray-400">
                  trig.osgb* vs attrval coords
                </span>
              </div>
              <div className="flex items-center gap-2">
                <span className="font-medium">dist_wgs_original:</span>
                <span className="text-gray-600 dark:text-gray-400">
                  current vs original WGS84
                </span>
              </div>
            </div>

            {/* Colour scale legend */}
            <div className="flex flex-wrap gap-4 mb-6 text-sm">
              <span className="font-medium">Distance scale:</span>
              <span className="text-green-600 dark:text-green-400">&lt;10cm</span>
              <span className="text-yellow-600 dark:text-yellow-400">10cm–1m</span>
              <span className="text-orange-600 dark:text-orange-400">1–10m</span>
              <span className="text-red-600 dark:text-red-400">&gt;10m</span>
            </div>

            {/* Filters */}
            <div className="flex flex-wrap items-center gap-6 mb-6 p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
              {/* Exclude Irish toggle */}
              <label className="flex items-center gap-3 cursor-pointer">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Exclude Irish
                </span>
                <button
                  type="button"
                  role="switch"
                  aria-checked={excludeIrish}
                  onClick={() => setExcludeIrish(!excludeIrish)}
                  className={`relative inline-flex h-6 w-11 flex-shrink-0 cursor-pointer rounded-full border-2 border-transparent transition-colors duration-200 ease-in-out focus:outline-none focus:ring-2 focus:ring-trig-green-500 focus:ring-offset-2 ${
                    excludeIrish
                      ? "bg-trig-green-600"
                      : "bg-gray-200 dark:bg-gray-600"
                  }`}
                >
                  <span
                    className={`pointer-events-none inline-block h-5 w-5 transform rounded-full bg-white shadow ring-0 transition duration-200 ease-in-out ${
                      excludeIrish ? "translate-x-5" : "translate-x-0"
                    }`}
                  />
                </button>
              </label>

              {/* Moved filter toggle (3-state) */}
              <div className="flex items-center gap-3">
                <span className="text-sm font-medium text-gray-700 dark:text-gray-300">
                  Moved trigs:
                </span>
                <div className="flex rounded-lg overflow-hidden border border-gray-300 dark:border-gray-600">
                  <button
                    type="button"
                    onClick={() => setMovedFilter("exclude_moved")}
                    className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                      movedFilter === "exclude_moved"
                        ? "bg-trig-green-600 text-white"
                        : "bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                    }`}
                  >
                    Hide
                  </button>
                  <button
                    type="button"
                    onClick={() => setMovedFilter("all")}
                    className={`px-3 py-1.5 text-sm font-medium border-x border-gray-300 dark:border-gray-600 transition-colors ${
                      movedFilter === "all"
                        ? "bg-trig-green-600 text-white"
                        : "bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                    }`}
                  >
                    All
                  </button>
                  <button
                    type="button"
                    onClick={() => setMovedFilter("only_moved")}
                    className={`px-3 py-1.5 text-sm font-medium transition-colors ${
                      movedFilter === "only_moved"
                        ? "bg-trig-green-600 text-white"
                        : "bg-white dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-600"
                    }`}
                  >
                    Only
                  </button>
                </div>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
                <p className="text-red-600 dark:text-red-400">{error}</p>
                <Button onClick={fetchData} className="mt-2">
                  Retry
                </Button>
              </div>
            )}

            {isLoading ? (
              <div className="flex items-center justify-center py-12">
                <Spinner size="lg" />
              </div>
            ) : (
              <>
                {/* Results count */}
                <p className="text-sm text-gray-600 dark:text-gray-400 mb-4">
                  Showing {items.length} of {total.toLocaleString()} trigpoints
                </p>

                {/* Table */}
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="border-b border-gray-200 dark:border-gray-700">
                        <th className="text-left py-3 px-2">
                          <SortableHeader
                            field="waypoint"
                            label="Waypoint"
                            currentSort={sort}
                            onSort={handleSort}
                          />
                        </th>
                        <th className="text-left py-3 px-2">
                          <SortableHeader
                            field="name"
                            label="Name"
                            currentSort={sort}
                            onSort={handleSort}
                          />
                        </th>
                        <th className="text-center py-3 px-2">Cond</th>
                        <th className="text-right py-3 px-2">
                          <SortableHeader
                            field="dist_wgs_osgb"
                            label="dist_wgs_osgb"
                            currentSort={sort}
                            onSort={handleSort}
                          />
                        </th>
                        <th className="text-right py-3 px-2">
                          <SortableHeader
                            field="dist_osgb_osgb"
                            label="dist_osgb_osgb"
                            currentSort={sort}
                            onSort={handleSort}
                          />
                        </th>
                        <th className="text-right py-3 px-2">
                          <SortableHeader
                            field="dist_wgs_original"
                            label="dist_wgs_original"
                            currentSort={sort}
                            onSort={handleSort}
                          />
                        </th>
                      </tr>
                    </thead>
                    <tbody>
                      {items.map((item) => (
                        <tr
                          key={item.trig_id}
                          className="border-b border-gray-100 dark:border-gray-800 hover:bg-gray-50 dark:hover:bg-gray-800/50"
                        >
                          <td className="py-2 px-2">
                            <Link
                              to={`/trigs/${item.trig_id}`}
                              className="text-trig-green-600 dark:text-trig-green-400 hover:underline font-mono"
                            >
                              {item.waypoint}
                            </Link>
                          </td>
                          <td className="py-2 px-2 text-gray-700 dark:text-gray-300">
                            {item.name}
                          </td>
                          <td className="py-2 px-2 text-center">
                            <img
                              src={`${CONDITION_ICON_BASE}${item.condition_icon}`}
                              alt={item.condition_name}
                              title={item.condition_name}
                              className="w-5 h-5 inline-block"
                            />
                          </td>
                          <td
                            className={`py-2 px-2 text-right font-mono ${getDistanceColourClass(
                              item.dist_wgs_osgb
                            )}`}
                          >
                            {formatDistance(item.dist_wgs_osgb)}
                          </td>
                          <td
                            className={`py-2 px-2 text-right font-mono ${getDistanceColourClass(
                              item.dist_osgb_osgb
                            )}`}
                          >
                            {formatDistance(item.dist_osgb_osgb)}
                          </td>
                          <td
                            className={`py-2 px-2 text-right font-mono ${getDistanceColourClass(
                              item.dist_wgs_original
                            )}`}
                          >
                            {formatDistance(item.dist_wgs_original)}
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>

                {/* Pagination */}
                <div className="flex items-center justify-between mt-6">
                  <div className="flex items-center gap-2">
                    <Button
                      onClick={() => setPage(1)}
                      disabled={page === 1}
                      variant="secondary"
                      size="sm"
                    >
                      First
                    </Button>
                    <Button
                      onClick={() => setPage((p) => Math.max(1, p - 1))}
                      disabled={page === 1}
                      variant="secondary"
                      size="sm"
                    >
                      Previous
                    </Button>
                  </div>

                  <span className="text-sm text-gray-600 dark:text-gray-400">
                    Page {page} of {totalPages}
                  </span>

                  <div className="flex items-center gap-2">
                    <Button
                      onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                      disabled={page === totalPages}
                      variant="secondary"
                      size="sm"
                    >
                      Next
                    </Button>
                    <Button
                      onClick={() => setPage(totalPages)}
                      disabled={page === totalPages}
                      variant="secondary"
                      size="sm"
                    >
                      Last
                    </Button>
                  </div>
                </div>
              </>
            )}
          </div>
        </Card>
      </div>
    </>
  );
}

