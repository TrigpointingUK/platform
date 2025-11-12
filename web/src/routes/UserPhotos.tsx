import { useEffect } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { useInView } from "react-intersection-observer";
import { InfiniteData, useQueryClient } from "@tanstack/react-query";
import Layout from "../components/layout/Layout";
import Card from "../components/ui/Card";
import Spinner from "../components/ui/Spinner";
import PhotoGrid from "../components/photos/PhotoGrid";
import { useUserPhotos } from "../hooks/useUserPhotos";
import { useUserProfile } from "../hooks/useUserProfile";
import { Photo } from "../lib/api";

interface PhotosResponse {
  items: Photo[];
  total: number;
  pagination: {
    has_more: boolean;
    next_offset: number | null;
  };
}

export default function UserPhotos() {
  const { userId } = useParams<{ userId: string }>();
  const queryClient = useQueryClient();
  const navigate = useNavigate();

  const {
    data: photosData,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
    isLoading,
    error,
  } = useUserPhotos(userId!);

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
  const allPhotos = photosData?.pages.flatMap((page) => page.items) || [];
  const totalPhotos = photosData?.pages[0]?.total || 0;

  // Handle photo rotation by updating the specific photo in the cache
  const handlePhotoRotated = (updatedPhoto: Photo) => {
    queryClient.setQueryData(
      ["user", userId, "photos"],
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
        <div className="max-w-7xl mx-auto">
          <Card>
            <p className="text-red-600">Failed to load user photos</p>
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
            {user?.name ? `${user.name}'s Photos` : "User Photos"}
          </h1>
          {!isLoading && (
            <p className="text-gray-600 mt-2">
              {totalPhotos.toLocaleString()} total photo
              {totalPhotos !== 1 ? "s" : ""}
            </p>
          )}
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
            <PhotoGrid photos={allPhotos} onPhotoRotated={handlePhotoRotated} />

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
                  All {allPhotos.length.toLocaleString()} photo
                  {allPhotos.length !== 1 ? "s" : ""} loaded
                </p>
              )}
            </div>
          </>
        )}

        {/* Empty State */}
        {!isLoading && allPhotos.length === 0 && (
          <Card>
            <div className="text-center py-12">
              <div className="text-6xl mb-4">📷</div>
              <p className="text-gray-600 text-lg">No photos found</p>
            </div>
          </Card>
        )}
      </div>
    </Layout>
  );
}

