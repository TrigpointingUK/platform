import { useEffect, useRef, ReactNode } from "react";
import Spinner from "../ui/Spinner";

interface SearchTileProps<T> {
  title: string;
  icon: string;
  totalResults: number;
  items: T[];
  isLoading: boolean;
  isFetchingMore?: boolean;
  hasMore: boolean;
  onLoadMore: () => void;
  renderItem: (item: T, index: number) => ReactNode;
  categoryKey: string;
  isCollapsed?: boolean;
  onToggleCollapse?: () => void;
  onHide?: () => void;
  useCardLayout?: boolean; // If true, use spacing for cards instead of list items
}

export function SearchTile<T>({
  title,
  icon,
  totalResults,
  items,
  isLoading,
  isFetchingMore = false,
  hasMore,
  onLoadMore,
  renderItem,
  categoryKey,
  isCollapsed = false,
  onToggleCollapse,
  onHide,
  useCardLayout = false,
}: SearchTileProps<T>) {
  const loadMoreRef = useRef<HTMLDivElement>(null);

  // Intersection Observer for infinite scroll
  useEffect(() => {
    if (!loadMoreRef.current || !hasMore || isLoading || isFetchingMore) {
      return;
    }

    const observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting) {
          onLoadMore();
        }
      },
      { threshold: 0.1 }
    );

    observer.observe(loadMoreRef.current);

    return () => observer.disconnect();
  }, [hasMore, isLoading, isFetchingMore, onLoadMore]);

  return (
    <div className="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
      {/* Tile Header */}
      <div className="w-full px-4 py-3 bg-trig-green-50 border-b border-gray-200 flex items-center justify-between">
        <button
          onClick={onToggleCollapse}
          className="flex items-center gap-2 flex-1 hover:opacity-80 transition-opacity"
        >
          <span className="text-2xl">{icon}</span>
          <h3 className="font-semibold text-gray-900">{title}</h3>
          <span className="text-sm text-gray-600">({totalResults})</span>
        </button>
        <div className="flex items-center gap-2">
          {onHide && (
            <button
              onClick={(e) => {
                e.stopPropagation();
                onHide();
              }}
              className="text-red-600 hover:text-red-700 hover:bg-red-50 p-1 rounded transition-colors"
              title="Hide this tile"
              aria-label="Hide tile"
            >
              <svg
                className="w-4 h-4"
                fill="none"
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth="2"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          )}
          {onToggleCollapse && (
            <button
              onClick={onToggleCollapse}
              className="text-gray-500 hover:text-gray-700 p-1"
              aria-label={isCollapsed ? "Expand tile" : "Collapse tile"}
            >
              <span className="text-sm">
                {isCollapsed ? "▼" : "▲"}
              </span>
            </button>
          )}
        </div>
      </div>

      {/* Tile Content */}
      {!isCollapsed && (
        <div className="max-h-[600px] overflow-y-auto">
          {isLoading && items.length === 0 ? (
            <div className="p-8 text-center">
              <Spinner size="md" />
              <p className="mt-2 text-gray-500">Searching...</p>
            </div>
          ) : items.length === 0 ? (
            <div className="p-8 text-center text-gray-500">
              <p>No results found</p>
            </div>
          ) : (
            <>
              <div className={useCardLayout ? "p-3 space-y-3" : "divide-y divide-gray-100"}>
                {items.map((item, index) => (
                  <div key={`${categoryKey}-${index}`}>
                    {renderItem(item, index)}
                  </div>
                ))}
              </div>

              {/* Load More Trigger */}
              {hasMore && (
                <div ref={loadMoreRef} className="p-4 text-center">
                  {isFetchingMore ? (
                    <div className="flex items-center justify-center gap-2">
                      <Spinner size="sm" />
                      <span className="text-sm text-gray-500">
                        Loading more...
                      </span>
                    </div>
                  ) : (
                    <span className="text-sm text-gray-500">
                      Scroll for more results
                    </span>
                  )}
                </div>
              )}

              {/* No More Results */}
              {!hasMore && items.length > 0 && (
                <div className="p-4 text-center text-sm text-gray-400">
                  All results loaded
                </div>
              )}
            </>
          )}
        </div>
      )}
    </div>
  );
}

