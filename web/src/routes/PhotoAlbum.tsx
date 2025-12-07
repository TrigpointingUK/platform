import { useEffect, useState } from "react";
import { useInView } from "react-intersection-observer";
import { useQueryClient, InfiniteData } from "@tanstack/react-query";
import Layout from "../components/layout/Layout";
import PhotoGrid from "../components/photos/PhotoGrid";
import Spinner from "../components/ui/Spinner";
import Button from "../components/ui/Button";
import { useInfinitePhotos, PhotoViewMode } from "../hooks/useInfinitePhotos";
import { clearHistory, getHistoryStats } from "../lib/photoHistory";
import { Photo } from "../lib/api";

interface PhotosResponse {
  items: Photo[];
  total: number;
  pagination: {
    has_more: boolean;
    next_offset: number | null;
  };
}

export default function PhotoAlbum() {
  const [viewMode, setViewMode] = useState<PhotoViewMode>('unseen');
  const [historyStats, setHistoryStats] = useState(getHistoryStats());
  const queryClient = useQueryClient();

  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useInfinitePhotos({ mode: viewMode });

  // Intersection observer to trigger loading more photos
  const { ref: loadMoreRef, inView } = useInView({
    threshold: 0,
    rootMargin: "200px", // Start loading 200px before reaching the trigger
  });

  // Flatten all pages into a single array
  const allPhotos = data?.pages.flatMap((page) => page.items) || [];

  // Auto-fetch when scrolling into view
  useEffect(() => {
    if (inView && hasNextPage && !isFetchingNextPage) {
      fetchNextPage();
    }
  }, [inView, hasNextPage, isFetchingNextPage, fetchNextPage]);

  // Auto-fetch more pages if we have no photos but there are more pages available
  // This handles the case where all photos in current pages are filtered out
  useEffect(() => {
    if (!isLoading && !isFetchingNextPage && hasNextPage && allPhotos.length === 0 && viewMode === 'unseen') {
      fetchNextPage();
    }
  }, [isLoading, isFetchingNextPage, hasNextPage, allPhotos.length, viewMode, fetchNextPage]);
  
  // Derive isSearching from conditions (no state needed)
  const isSearching = !isLoading && isFetchingNextPage && allPhotos.length === 0 && viewMode === 'unseen';

  // Update history stats periodically
  useEffect(() => {
    const interval = setInterval(() => {
      setHistoryStats(getHistoryStats());
    }, 3000);
    return () => clearInterval(interval);
  }, []);

  const handleClearHistory = () => {
    clearHistory();
    setHistoryStats(getHistoryStats());
    // Invalidate queries to force refetch with cleared history
    queryClient.invalidateQueries({ queryKey: ["photos", "infinite"] });
  };

  // Handle photo rotation by updating the specific photo in the cache
  const handlePhotoRotated = (updatedPhoto: Photo) => {
    queryClient.setQueryData(
      ["photos", "infinite", viewMode],
      (oldData: InfiniteData<PhotosResponse> | undefined) => {
        if (!oldData?.pages) return oldData;

        return {
          ...oldData,
          pages: oldData.pages.map((page: PhotosResponse) => ({
            ...page,
            items: page.items.map((photo: Photo) =>
              photo.id === updatedPhoto.id
                ? {
                    ...photo,
                    photo_url: updatedPhoto.photo_url,
                    icon_url: updatedPhoto.icon_url,
                    width: updatedPhoto.width,
                    height: updatedPhoto.height,
                    icon_width: updatedPhoto.icon_width,
                    icon_height: updatedPhoto.icon_height,
                  }
                : photo
            ),
          })),
        };
      }
    );
  };

  if (error) {
    return (
      <Layout>
        <title>Photo Album | TrigpointingUK</title>
        <div className="max-w-7xl mx-auto">
          <h1 className="text-3xl font-bold text-gray-800 mb-6">Photo Gallery</h1>
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-600 mb-4">
              Failed to load photos. Please try again later.
            </p>
            <Button onClick={() => window.location.reload()}>Reload Page</Button>
          </div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout>
      <title>Photo Album | TrigpointingUK</title>
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
            <div>
              <h1 className="text-3xl font-bold text-gray-800 mb-2">Photo Gallery</h1>
              <p className="text-gray-600">
                {isLoading ? (
                  "Loading photos..."
                ) : (
                  <>
                    {allPhotos.length.toLocaleString()} {viewMode === 'unseen' ? 'unseen ' : ''}photo{allPhotos.length !== 1 ? 's' : ''} loaded
                    {viewMode === 'unseen' && historyStats.totalPhotosViewed > 0 && (
                      <span className="text-sm text-gray-500 ml-2">
                        ({historyStats.totalPhotosViewed.toLocaleString()} previously viewed)
                      </span>
                    )}
                  </>
                )}
              </p>
            </div>
            
            {/* View Mode Controls */}
            <div className="flex flex-wrap gap-2">
              <div className="flex gap-1 bg-gray-100 rounded-lg p-1">
                <button
                  onClick={() => setViewMode('unseen')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    viewMode === 'unseen'
                      ? 'bg-white text-trig-green-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  Unseen Photos
                </button>
                <button
                  onClick={() => setViewMode('all')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                    viewMode === 'all'
                      ? 'bg-white text-trig-green-600 shadow-sm'
                      : 'text-gray-600 hover:text-gray-900'
                  }`}
                >
                  All Photos
                </button>
              </div>
              
              {historyStats.totalPhotosViewed > 0 && (
                <Button
                  onClick={handleClearHistory}
                  variant="secondary"
                  className="text-sm"
                >
                  Reset History
                </Button>
              )}
            </div>
          </div>
        </div>

        {/* Loading State */}
        {isLoading && (
          <div className="py-12">
            <Spinner size="lg" />
            <p className="text-center text-gray-600 mt-4">Loading photos...</p>
          </div>
        )}

        {/* Photo Grid */}
        {!isLoading && allPhotos.length > 0 && (
          <>
            <PhotoGrid
              photos={allPhotos}
              onPhotoRotated={handlePhotoRotated}
            />

            {/* Load More Trigger */}
            <div ref={loadMoreRef} className="py-8 text-center">
              {isFetchingNextPage && (
                <>
                  <Spinner size="md" />
                  <p className="text-gray-600 mt-4">Loading more photos...</p>
                </>
              )}
              {!hasNextPage && allPhotos.length > 0 && (
                <p className="text-gray-500">
                  You've reached the end! {allPhotos.length.toLocaleString()}{" "}
                  {viewMode === 'unseen' ? 'unseen ' : ''}photo{allPhotos.length !== 1 ? 's' : ''} loaded.
                </p>
              )}
            </div>
          </>
        )}

        {/* Empty State / Searching State */}
        {!isLoading && !isSearching && allPhotos.length === 0 && (
          <div className="text-center py-12">
            <div className="text-6xl mb-4">📷</div>
            {viewMode === 'unseen' ? (
              <>
                <p className="text-gray-600 text-lg mb-4">
                  You've seen all the photos!
                </p>
                <Button onClick={handleClearHistory}>Reset History</Button>
              </>
            ) : (
              <p className="text-gray-600 text-lg">No photos found</p>
            )}
          </div>
        )}

        {/* Searching State */}
        {!isLoading && isSearching && allPhotos.length === 0 && (
          <div className="text-center py-12">
            <Spinner size="lg" />
            <p className="text-gray-600 text-lg mt-4">
              {viewMode === 'unseen' 
                ? "Finding photos you haven't seen..." 
                : "Loading photos..."}
            </p>
          </div>
        )}
      </div>
    </Layout>
  );
}

