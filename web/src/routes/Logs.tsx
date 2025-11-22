import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useInView } from "react-intersection-observer";
import Layout from "../components/layout/Layout";
import LogCard from "../components/logs/LogCard";
import MiniTrigMap from "../components/map/MiniTrigMap";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import { useInfiniteLogs } from "../hooks/useInfiniteLogs";
import type { Log } from "../hooks/useInfiniteLogs";

export default function Logs() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfiniteLogs();

  const MAP_SPACING = 24;
  const MAP_FALLBACK_WIDTH = 200;
  const [centerLogIndex, setCenterLogIndex] = useState<number | null>(null);
  const [featuredLog, setFeaturedLog] = useState<Log | null>(null);
  const logRefs = useRef<Map<number, HTMLDivElement>>(new Map());
  const mapOverlayRef = useRef<HTMLDivElement | null>(null);
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [mapRightOffset, setMapRightOffset] = useState<number>(8);
  const [mapLeftOffset, setMapLeftOffset] = useState<number | null>(null);
  const updateMapOffset = useCallback(() => {
    const container = containerRef.current;
    if (!container) {
      return;
    }
    const rect = container.getBoundingClientRect();
    const mapWidth = mapOverlayRef.current?.offsetWidth ?? MAP_FALLBACK_WIDTH;
    const candidateLeft = rect.right + MAP_SPACING;
    const fitsLeft =
      candidateLeft + mapWidth + MAP_SPACING <= window.innerWidth;

    if (fitsLeft) {
      setMapLeftOffset(candidateLeft);
    } else {
      const rightOffset = Math.max(
        MAP_SPACING,
        window.innerWidth - rect.right
      );
      setMapLeftOffset(null);
      setMapRightOffset(rightOffset);
    }
  }, [MAP_SPACING]);

  useEffect(() => {
    updateMapOffset();
    window.addEventListener("resize", updateMapOffset);

    return () => {
      window.removeEventListener("resize", updateMapOffset);
    };
  }, [updateMapOffset]);

  // Intersection observer to trigger loading more logs
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
    rootMargin: "600px", // Start loading 600px before reaching the trigger
  });

  // Flatten all pages into a single array (memoized to prevent re-creation on every render)
  const allLogs = useMemo<Log[]>(
    () => data?.pages.flatMap((page) => page.items) || [],
    [data?.pages]
  );

  useEffect(() => {
    updateMapOffset();
  }, [isLoading, allLogs.length, updateMapOffset]);

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

      const mapBottom =
        mapOverlayRef.current?.getBoundingClientRect().bottom ?? 0;

      let firstBelowIndex: number | null = null;
      for (let i = 0; i < allLogs.length; i += 1) {
        const element = logRefs.current.get(i);
        if (!element) {
          continue;
        }
        const rect = element.getBoundingClientRect();
        if (rect.top >= mapBottom) {
          firstBelowIndex = i;
          break;
        }
      }

      const targetIndex =
        firstBelowIndex !== null
          ? Math.max(0, firstBelowIndex - 1)
          : allLogs.length > 0
          ? allLogs.length - 1
          : null;

      if (targetIndex !== null) {
        if (targetIndex !== centerLogIndex) {
          setCenterLogIndex(targetIndex);
        }
        const candidate = allLogs[targetIndex];
        if (candidate && candidate.id !== featuredLog?.id) {
          setFeaturedLog(candidate);
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
  }, [allLogs.length, allLogs, centerLogIndex, featuredLog]);

  useEffect(() => {
    if (!featuredLog && allLogs.length > 0) {
      setFeaturedLog(allLogs[0]);
    }
  }, [allLogs, featuredLog]);

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

  return (
    <Layout>
      <div className="max-w-4xl mx-auto relative" ref={containerRef}>
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
              {allLogs.map((log, index) => {
                const isFeatured = centerLogIndex === index;
                const isAboveFeatured =
                  centerLogIndex !== null && index < centerLogIndex;

                return (
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
                      isFeatured
                        ? "border-2 border-trig-green-300 rounded-xl shadow-lg"
                        : "border-2 border-transparent"
                    } ${
                      isAboveFeatured
                        ? "opacity-50 blur-[1.5px]"
                        : "opacity-100 blur-0"
                    }`}
                  >
                    <LogCard log={log} />
                  </div>
                );
              })}
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
          <div
            className="fixed top-22 z-40"
            ref={mapOverlayRef}
            style={
              mapLeftOffset !== null && mapLeftOffset > 0
                ? { left: mapLeftOffset }
                : { right: mapRightOffset }
            }
          >
            <div className="bg-white rounded-lg border-2 border-gray-300 shadow-2xl overflow-hidden">
              <div className="relative">
                <MiniTrigMap
                  trigId={featuredLog?.trig_id ?? null}
                  trigName={featuredLog?.trig_name ?? ""}
                  lat={featuredLog?.trig_lat ?? null}
                  lon={featuredLog?.trig_lon ?? null}
                  className="w-[160px] h-[160px] lg:w-[190px] lg:h-[190px]"
                />
              </div>
            </div>
          </div>
        )}
      </div>
    </Layout>
  );
}

