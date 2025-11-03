import { useEffect, useMemo, useRef, useState } from "react";
import { useInView } from "react-intersection-observer";
import Layout from "../components/layout/Layout";
import LogCard from "../components/logs/LogCard";
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

  const [centerLogIndex, setCenterLogIndex] = useState<number | null>(null);
  const [featuredTrigId, setFeaturedTrigId] = useState<number>(24266);
  const [featuredTrigName, setFeaturedTrigName] = useState<string>("");
  const logRefs = useRef<Map<number, HTMLDivElement>>(new Map());

  // Intersection observer to trigger loading more logs
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
    rootMargin: "600px", // Start loading 600px before reaching the trigger
  });

  // Flatten all pages into a single array (memoized to prevent re-creation on every render)
  const allLogs = useMemo(
    () => data?.pages.flatMap((page) => page.items) || [],
    [data?.pages]
  );

  // Auto-fetch when scrolling into view
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Track which log is the first fully visible in viewport
  useEffect(() => {
    const handleScroll = () => {
      if (allLogs.length === 0) return;

      const viewportTop = 0;
      const viewportBottom = window.innerHeight;
      let firstFullyVisibleIndex: number | null = null;

      // Iterate through logs in order to find the first fully visible one
      for (const [index, element] of logRefs.current.entries()) {
        const rect = element.getBoundingClientRect();
        
        // Check if the element is fully visible in the viewport
        const isFullyVisible = rect.top >= viewportTop && rect.bottom <= viewportBottom;
        
        if (isFullyVisible) {
          firstFullyVisibleIndex = index;
          break; // Found the first one, no need to continue
        }
      }

      // If no card is fully visible, fall back to the first partially visible card
      if (firstFullyVisibleIndex === null) {
        for (const [index, element] of logRefs.current.entries()) {
          const rect = element.getBoundingClientRect();
          
          // Check if at least part of the element is visible
          const isPartiallyVisible = rect.bottom > viewportTop && rect.top < viewportBottom;
          
          if (isPartiallyVisible) {
            firstFullyVisibleIndex = index;
            break;
          }
        }
      }

      if (firstFullyVisibleIndex !== null && firstFullyVisibleIndex !== centerLogIndex) {
        setCenterLogIndex(firstFullyVisibleIndex);
        // Update the featured trig based on the visible log
        if (allLogs[firstFullyVisibleIndex]) {
          setFeaturedTrigId(allLogs[firstFullyVisibleIndex].trig_id);
          setFeaturedTrigName(allLogs[firstFullyVisibleIndex].trig_name || "");
        }
      }
    };

    // Initial check
    handleScroll();

    // Listen for scroll events with throttling
    let timeoutId: number;
    const throttledScroll = () => {
      if (timeoutId) {
        window.cancelAnimationFrame(timeoutId);
      }
      timeoutId = window.requestAnimationFrame(handleScroll);
    };

    window.addEventListener("scroll", throttledScroll, { passive: true });
    window.addEventListener("resize", throttledScroll);

    return () => {
      window.removeEventListener("scroll", throttledScroll);
      window.removeEventListener("resize", throttledScroll);
      if (timeoutId) {
        window.cancelAnimationFrame(timeoutId);
      }
    };
  }, [allLogs.length, allLogs, centerLogIndex]);

  if (error) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
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

  const apiBase = import.meta.env.VITE_API_BASE as string;

  return (
    <Layout>
      <div className="max-w-4xl mx-auto relative">
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
            <div className="space-y-4">
              {allLogs.map((log, index) => (
                <div
                  key={log.id}
                  ref={(el) => {
                    if (el) {
                      logRefs.current.set(index, el);
                    } else {
                      logRefs.current.delete(index);
                    }
                  }}
                  className={`transition-all duration-300 ${
                    centerLogIndex === index
                      ? "border-2 border-trig-green-300 rounded-xl shadow-lg"
                      : "border-2 border-transparent"
                  }`}
                >
                  <LogCard log={log} />
                </div>
              ))}
            </div>

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

        {/* Floating Map Overlay - Fixed position on desktop */}
        {!isLoading && allLogs.length > 0 && (
          <div className="fixed top-22 right-2 lg:right-8 z-40">
            <div className="bg-white rounded-lg border-2 border-gray-300 shadow-2xl overflow-hidden">
              <div className="relative">
                <img
                  key={featuredTrigId}
                  src={`${apiBase}/v1/trigs/${featuredTrigId}/map`}
                  alt={`Trigpoint ${featuredTrigId} map`}
                  className="w-[160px] h-[160px] lg:w-[190px] lg:h-[190px]"
                />
                <div className="absolute top-2 left-2 bg-white/90 px-2 py-1 rounded text-xs font-mono text-gray-700 max-w-[calc(100%-1rem)] truncate shadow-sm">
                  {featuredTrigName && `${featuredTrigName}`}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

