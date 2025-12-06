import { useMemo, useState } from 'react';
import { useParams, useNavigate, useLocation } from 'react-router-dom';
import { useQueryClient, useQuery } from '@tanstack/react-query';
import Layout from '../components/layout/Layout';
import Spinner from '../components/ui/Spinner';
import { usePhotoSwipe } from '../hooks/usePhotoSwipe';
import { Photo } from '../lib/api';
import 'photoswipe/style.css';
import '../components/photos/photoswipe-custom.css';

interface PhotosResponse {
  items: Photo[];
  total: number;
  pagination: {
    has_more: boolean;
    next_offset: number | null;
  };
}

export default function PhotoDetail() {
  const { photo_id } = useParams<{ photo_id: string }>();
  const navigate = useNavigate();
  const location = useLocation();
  const queryClient = useQueryClient();
  const photoIdNum = photo_id ? parseInt(photo_id, 10) : null;

  // Check if photo was passed via router state (from log cards)
  const photoFromState = location.state?.photo as Photo | undefined;
  const allPhotosFromState = location.state?.allPhotos as Photo[] | undefined;
  const contextFromState = location.state?.context as string | undefined;

  // Try to get photo from the photos grid cache
  const photoData = queryClient.getQueryData<{
    pages: PhotosResponse[];
    pageParams: number[];
  }>(['photos', 'infinite', 'unseen']) || queryClient.getQueryData<{
    pages: PhotosResponse[];
    pageParams: number[];
  }>(['photos', 'infinite', 'all']);

  const allPhotos = photoData?.pages.flatMap((page) => page.items) || [];
  const cachedPhoto = allPhotos.find((p) => p.id === photoIdNum);

  // Only fetch if we don't have the photo from state or cache
  const shouldFetch = !photoFromState && !cachedPhoto && photoIdNum !== null;

  // Fetch single photo by ID if not in cache or state
  const { data: fetchedPhoto, isLoading, error } = useQuery<Photo>({
    queryKey: ['photo', photoIdNum],
    queryFn: async () => {
      const apiBase = import.meta.env.VITE_API_BASE as string;
      const response = await fetch(`${apiBase}/v1/photos/${photoIdNum}`);
      if (!response.ok) {
        throw new Error('Failed to fetch photo');
      }
      return response.json();
    },
    enabled: shouldFetch,
    staleTime: 5 * 60 * 1000, // 5 minutes
  });

  // Track rotated photos state (for when user rotates a photo)
  const [rotatedPhotos, setRotatedPhotos] = useState<Map<number, Photo>>(new Map());

  // Derive photo for viewer from sources (no effect needed)
  const { photoForViewer, allPhotosForViewer, initialPhotoIndex } = useMemo(() => {
    // Priority: photoFromState > cachedPhoto > fetchedPhoto
    const basePhoto = photoFromState ?? cachedPhoto ?? fetchedPhoto ?? null;
    
    // Apply any rotation updates
    const photo = basePhoto && rotatedPhotos.has(basePhoto.id) 
      ? rotatedPhotos.get(basePhoto.id)! 
      : basePhoto;
    
    if (!photo) {
      return { photoForViewer: null, allPhotosForViewer: [], initialPhotoIndex: 0 };
    }
    
    // If we have all photos from a log context, use them for navigation
    if (photoFromState && allPhotosFromState && allPhotosFromState.length > 0 && contextFromState === 'log') {
      // Apply rotation updates to all photos
      const updatedPhotos = allPhotosFromState.map(p => 
        rotatedPhotos.has(p.id) ? rotatedPhotos.get(p.id)! : p
      );
      const index = updatedPhotos.findIndex(p => p.id === photo.id);
      return {
        photoForViewer: photo,
        allPhotosForViewer: updatedPhotos,
        initialPhotoIndex: index >= 0 ? index : 0,
      };
    }
    
    // Single photo mode
    return {
      photoForViewer: photo,
      allPhotosForViewer: [photo],
      initialPhotoIndex: 0,
    };
  }, [photoFromState, cachedPhoto, fetchedPhoto, allPhotosFromState, contextFromState, rotatedPhotos]);

  // Navigate back to previous page on close
  const handleClose = () => {
    navigate(-1); // Go back in browser history
  };

  // Handle photo rotation
  const handlePhotoRotated = (updatedPhoto: Photo) => {
    // Track rotated photo in local state
    setRotatedPhotos(prev => new Map(prev).set(updatedPhoto.id, updatedPhoto));
    
    // Update the cache if this photo came from the photo grid
    queryClient.setQueryData(['photos', 'infinite', 'unseen'], (oldData: { pages: PhotosResponse[]; pageParams: number[] } | undefined) => {
      if (!oldData?.pages) return oldData;
      return {
        ...oldData,
        pages: oldData.pages.map((page: PhotosResponse) => ({
          ...page,
          items: page.items.map((photo: Photo) =>
            photo.id === updatedPhoto.id ? updatedPhoto : photo
          ),
        })),
      };
    });
    
    queryClient.setQueryData(['photos', 'infinite', 'all'], (oldData: { pages: PhotosResponse[]; pageParams: number[] } | undefined) => {
      if (!oldData?.pages) return oldData;
      return {
        ...oldData,
        pages: oldData.pages.map((page: PhotosResponse) => ({
          ...page,
          items: page.items.map((photo: Photo) =>
            photo.id === updatedPhoto.id ? updatedPhoto : photo
          ),
        })),
      };
    });
  };

  // Open PhotoSwipe when we have a photo
  usePhotoSwipe({
    photos: allPhotosForViewer,
    initialIndex: initialPhotoIndex,
    onClose: handleClose,
    onPhotoRotated: handlePhotoRotated,
  });

  // Show loading state while fetching
  if (isLoading && !cachedPhoto && !photoFromState) {
    return (
      <Layout>
        <div className="flex items-center justify-center min-h-screen">
          <div className="text-center">
            <Spinner size="lg" />
            <p className="mt-4 text-gray-600">Loading photo...</p>
          </div>
        </div>
      </Layout>
    );
  }

  // Show error state or photo not found
  if ((error || (!photoForViewer && !isLoading)) && !cachedPhoto && !photoFromState) {
    return (
      <Layout>
        <div className="max-w-7xl mx-auto">
          <div className="bg-red-50 border border-red-200 rounded-lg p-6 text-center">
            <p className="text-red-600 mb-4">
              {error ? 'Failed to load photo.' : 'Photo not found.'}
            </p>
            <button
              onClick={() => navigate('/photos')}
              className="px-4 py-2 bg-trig-green-600 text-white rounded hover:bg-trig-green-700"
            >
              Back to Photos
            </button>
          </div>
        </div>
      </Layout>
    );
  }

  // Render empty layout as background (PhotoSwipe will overlay)
  return (
    <Layout>
      <div className="max-w-7xl mx-auto" />
    </Layout>
  );
}

