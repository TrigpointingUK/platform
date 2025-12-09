import { useCallback, useEffect, useState } from "react";
import { useParams, useNavigate, useSearchParams } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import LogList from "../components/logs/LogList";
import { useUserLogs } from "../hooks/useUserLogs";
import { useUserProfile } from "../hooks/useUserProfile";
import { useDocumentTitle } from "../hooks/useDocumentTitle";
import { DateRangePicker, type DateRange } from "../components/ui/DateRangePicker";

export default function UserLogs() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const [isFilterCollapsed, setIsFilterCollapsed] = useState(true);

  // Date range filter state - parse from URL
  const [dateRange, setDateRange] = useState<DateRange | undefined>(() => {
    const fromDate = searchParams.get("fromDate");
    const toDate = searchParams.get("toDate");
    if (fromDate || toDate) {
      return {
        from: fromDate ? new Date(fromDate) : undefined,
        to: toDate ? new Date(toDate) : undefined,
      };
    }
    return undefined;
  });

  // Check if any filters are active
  const hasActiveFilters = dateRange !== undefined;

  // Update URL when filters change
  useEffect(() => {
    const params = new URLSearchParams();

    if (dateRange?.from) {
      params.set("fromDate", dateRange.from.toISOString().split("T")[0]);
    }
    if (dateRange?.to) {
      params.set("toDate", dateRange.to.toISOString().split("T")[0]);
    }

    setSearchParams(params, { replace: true });
  }, [dateRange, setSearchParams]);

  const handleClearFilters = useCallback(() => {
    setDateRange(undefined);
  }, []);

  const {
    data: logsData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useUserLogs(userId!, {
    fromDate: dateRange?.from,
    toDate: dateRange?.to,
  });

  const { data: user } = useUserProfile(userId!);
  
  // Get current user's preference for showing trig condition
  const { data: currentUserProfile } = useUserProfile("me");
  const showTrigCondition = currentUserProfile?.prefs?.ui_prefs?.show_trig_condition ?? false;

  // Update document title when user data loads
  useDocumentTitle(user?.name ? `${user.name}'s Logs` : null);

  // Intersection observer for infinite scroll
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
    rootMargin: "200px",
  });

  // Auto-fetch when scrolling into view
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Flatten all pages into a single array
  const allLogs = logsData?.pages.flatMap((page) => page.items) || [];
  const totalLogs = logsData?.pages[0]?.total || 0;

  if (error) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600">Failed to load user logs</p>
          </Card>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => navigate(-1)}
            className="text-trig-green-600 hover:underline mb-2 inline-block"
          >
            ← Back
          </button>
          <h1 className="text-3xl font-bold text-gray-800">
            {user?.name ? `${user.name}'s Logs` : "User Logs"}
          </h1>
        </div>

        {/* Filter Panel */}
        <div className="bg-white border-b border-gray-200 shadow-md rounded-lg p-4 mb-6">
          {/* Toggle button and results summary when collapsed */}
          <div
            className={`flex items-center gap-3 ${isFilterCollapsed ? "" : "mb-2"}`}
          >
            <button
              type="button"
              onClick={() => setIsFilterCollapsed(!isFilterCollapsed)}
              className="p-1.5 rounded-md hover:bg-gray-100 transition-colors text-gray-500 hover:text-gray-700"
              aria-label={
                isFilterCollapsed ? "Expand filters" : "Collapse filters"
              }
              title={isFilterCollapsed ? "Expand filters" : "Collapse filters"}
            >
              <svg
                className={`w-5 h-5 transition-transform ${isFilterCollapsed ? "" : "rotate-90"}`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
            {isFilterCollapsed ? (
              <span className="text-sm text-gray-600">
                {hasActiveFilters
                  ? `Filtered by date range`
                  : "Expand to filter logs by date"}
              </span>
            ) : (
              <span className="text-sm font-medium text-gray-700">
                Filter Logs
              </span>
            )}
          </div>

          {/* Collapsible filter content */}
          <div className={`space-y-4 ${isFilterCollapsed ? "hidden" : ""}`}>
            {/* Date range filter */}
            <div className="max-w-md">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Filter by date range
              </label>
              <DateRangePicker
                value={dateRange}
                onChange={setDateRange}
                placeholder="Select date range"
                maxValue={new Date()}
                presets={[
                  {
                    label: "Today",
                    dateRange: {
                      from: new Date(),
                      to: new Date(),
                    },
                  },
                  {
                    label: "Last 7 days",
                    dateRange: {
                      from: new Date(new Date().setDate(new Date().getDate() - 7)),
                      to: new Date(),
                    },
                  },
                  {
                    label: "Last 30 days",
                    dateRange: {
                      from: new Date(new Date().setDate(new Date().getDate() - 30)),
                      to: new Date(),
                    },
                  },
                  {
                    label: "Last 3 months",
                    dateRange: {
                      from: new Date(new Date().setMonth(new Date().getMonth() - 3)),
                      to: new Date(),
                    },
                  },
                  {
                    label: "Last 6 months",
                    dateRange: {
                      from: new Date(new Date().setMonth(new Date().getMonth() - 6)),
                      to: new Date(),
                    },
                  },
                  {
                    label: "This year",
                    dateRange: {
                      from: new Date(new Date().getFullYear(), 0, 1),
                      to: new Date(),
                    },
                  },
                  {
                    label: "Last year",
                    dateRange: {
                      from: new Date(new Date().getFullYear() - 1, 0, 1),
                      to: new Date(new Date().getFullYear() - 1, 11, 31),
                    },
                  },
                ]}
              />
            </div>

            {/* Results count and clear filters */}
            <div className="flex items-center justify-between">
              <div className="text-sm text-gray-600">
                {isLoading ? (
                  <span>Loading...</span>
                ) : (
                  <span>
                    Showing {allLogs.length} of {totalLogs.toLocaleString()}{" "}
                    log
                    {totalLogs !== 1 ? "s" : ""}
                  </span>
                )}
              </div>
              {hasActiveFilters && (
                <button
                  type="button"
                  onClick={handleClearFilters}
                  className="inline-flex items-center gap-1.5 px-3 py-1.5 text-sm text-gray-500 hover:text-gray-700 font-medium hover:bg-gray-100 rounded-lg transition-colors"
                >
                  <svg
                    className="w-4 h-4"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M6 18L18 6M6 6l12 12"
                    />
                  </svg>
                  Clear filters
                </button>
              )}
            </div>
          </div>
        </div>

        {/* Logs List */}
        <Card>
          {error && <p className="text-red-600">Failed to load logs</p>}

          {!error && (
            <>
              <LogList
                logs={allLogs}
                isLoading={isLoading}
                emptyMessage={
                  hasActiveFilters
                    ? "No logs found matching your filters"
                    : "No logs found"
                }
                showTrigCondition={showTrigCondition}
              />

              {/* Load More Trigger */}
              {allLogs.length > 0 && (
                <div ref={loadMoreRef} className="py-8 text-center">
                  {isFetchingNextPage && (
                    <>
                      <Spinner size="md" />
                      <p className="text-gray-600 mt-4">Loading more logs...</p>
                    </>
                  )}
                  {!hasNextPage && (
                    <p className="text-gray-500">
                      All {allLogs.length.toLocaleString()} log
                      {allLogs.length !== 1 ? "s" : ""} loaded
                    </p>
                  )}
                </div>
              )}
            </>
          )}
        </Card>
      </div>
    </Layout>
  );
}

