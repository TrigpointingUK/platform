import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import LogList from "../components/logs/LogList";
import { useUserLogs } from "../hooks/useUserLogs";
import { useUserProfile } from "../hooks/useUserProfile";

export default function UserLogs() {
  const { userId } = useParams<{ userId: string }>();
  const navigate = useNavigate();

  const {
    data: logsData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useUserLogs(userId!);

  const { data: user } = useUserProfile(userId!);

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
          {!isLoading && (
            <p className="text-gray-600 mt-2">
              {totalLogs.toLocaleString()} total log
              {totalLogs !== 1 ? "s" : ""}
            </p>
          )}
        </div>

        {/* Logs List */}
        <Card>
          {error && <p className="text-red-600">Failed to load logs</p>}

          {!error && (
            <>
              <LogList
                logs={allLogs}
                isLoading={isLoading}
                emptyMessage="No logs found"
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

