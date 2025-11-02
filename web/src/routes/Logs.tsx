import { useEffect } from "react";
import { useInView } from "react-intersection-observer";
import Layout from "../components/layout/Layout";
import LogList from "../components/logs/LogList";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import { useInfiniteLogs } from "../hooks/useInfiniteLogs";

export default function Logs() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteLogs();

  // Intersection observer to trigger loading more logs
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
    rootMargin: "600px", // Start loading 600px before reaching the trigger
  });

  // Flatten all pages into a single array
  const allLogs = data?.pages.flatMap((page) => page.items) || [];

  // Auto-fetch when scrolling into view
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  if (error) {
    return (
      <Layout>
        <div className="max-w-4xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Visit Logs</h1>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-600 mb-4">
              Failed to load logs. Please try again later.
            </p>
            <Button onClick={() => window.location.reload()}>Reload Page</Button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <h1 className="text-3xl font-bold text-gray-800 mb-2">Visit Logs</h1>
          <p className="text-gray-600">
            {isLoading
              ? "Loading logs..."
              : `${allLogs.length.toLocaleString()} log${
                  allLogs.length !== 1 ? "s" : ""
                } loaded`}
          </p>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="py-12">
            <Spinner size="lg" />
            <p className="text-center text-gray-600 mt-4">Loading logs...</p>
          </div>
        )}

        {/* Log List */}
        {!isLoading && allLogs.length > 0 && (
          <>
            <LogList logs={allLogs} />

            {/* Load More Trigger */}
            <div ref={loadMoreRef} className="py-8 text-center">
              {isFetchingNextPage && (
                <>
                  <Spinner size="md" />
                  <p className="text-gray-600 mt-4">Loading more logs...</p>
                </>
              )}
              {!hasNextPage && allLogs.length > 0 && (
                <p className="text-gray-500">
                  You've reached the end! {allLogs.length.toLocaleString()} log
                  {allLogs.length !== 1 ? "s" : ""} loaded.
                </p>
              )}
            </div>
          </>
        )}

        {/* Empty State */}
        {!isLoading && allLogs.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📝</div>
            <p className="text-gray-600 text-lg">No logs found</p>
          </div>
        )}
      </div>
    </Layout>
  );
}

