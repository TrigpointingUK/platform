import { useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import toast from "react-hot-toast";
import { authenticatedPost, Photo } from "../../lib/api";
import StarRating from "../ui/StarRating";

const API_BASE = import.meta.env.VITE_API_BASE as string;

interface PhotoThumbnailProps {
  photo: Photo;
  onClick?: () => void;
  onPhotoRotated?: (updatedPhoto: Photo) => void;
}

// Format trig ID as waypoint (TP0001, TP0123, TP12345)
function formatWaypoint(trigId: number): string {
  return `TP${trigId.toString().padStart(4, "0")}`;
}

// Format date as "1 Jan 2024"
function formatLogDate(dateString?: string): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

// Check if a value is empty or "none"
function isEmptyOrNone(value: string | undefined): boolean {
  if (!value) return true;
  const trimmed = value.trim().toLowerCase();
  return trimmed === "" || trimmed === "none";
}

export default function PhotoThumbnail({
  photo,
  onClick,
  onPhotoRotated,
}: PhotoThumbnailProps) {
  const [loaded, setLoaded] = useState(false);
  const [error, setError] = useState(false);
  const [rotating, setRotating] = useState(false);
  const [optimisticRotation, setOptimisticRotation] = useState(0);
  const { getAccessTokenSilently, isAuthenticated } = useAuth0();

  const handleRotate = async (angle: number, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    console.log('Rotate clicked for photo:', photo.id, 'angle:', angle);
    setRotating(true);
    
    // Apply optimistic rotation immediately
    // For left rotation (270°), we visually rotate -90° for smooth UX
    const visualAngle = angle === 270 ? -90 : angle;
    const newRotation = optimisticRotation + visualAngle;
    setOptimisticRotation(newRotation);

    try {
      console.log('Rotating photo:', photo.id, 'angle:', angle);
      
      // Use authenticatedPost which handles 401 retry automatically
      const response = await authenticatedPost<Photo>(
        `${API_BASE}/v1/photos/${photo.id}/rotate`,
        { angle },
        getAccessTokenSilently
      );
      console.log('Photo rotated successfully:', response);
      
      toast.success("Photo rotated successfully");
      
      // Call the callback with the updated photo data from the API response
      if (onPhotoRotated) {
        onPhotoRotated(response);
      }
      
      // Reset optimistic rotation after successful API call
      // The photo URL will be updated via the cache update
      setOptimisticRotation(0);
    } catch (error) {
      console.error("Failed to rotate photo:", error);
      console.error('Error details:', {
        message: error instanceof Error ? error.message : String(error),
        stack: error instanceof Error ? error.stack : undefined,
        errorType: typeof error,
        errorConstructor: error?.constructor?.name,
      });
      toast.error("Failed to rotate photo. Please try again.");
      
      // Revert optimistic rotation on error
      setOptimisticRotation(optimisticRotation);
    } finally {
      setRotating(false);
    }
  };

  // Check if photo is public domain (license = 'Y')
  const isPublicDomain = photo.license === "Y";

  return (
    <div
      className="relative group cursor-pointer overflow-hidden rounded-lg bg-gray-100 dark:bg-gray-800"
      onClick={onClick}
    >
      {/* Loading Placeholder */}
      {!loaded && !error && (
        <div className="aspect-square flex items-center justify-center">
          <div className="h-8 w-8 border-2 border-trig-green-600 border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Error State */}
      {error && (
        <div className="aspect-square flex items-center justify-center bg-gray-200 dark:bg-gray-700">
          <span className="text-gray-400 dark:text-gray-500 text-sm">Failed to load</span>
        </div>
      )}

      {/* Image */}
      {!error && (
        <img
          src={photo.photo_url}
          alt={photo.caption}
          loading="lazy"
          onLoad={() => setLoaded(true)}
          onError={() => setError(true)}
          style={{
            transform: `rotate(${optimisticRotation}deg)`,
            transition: "transform 0.3s ease-in-out",
          }}
          className={`w-full h-full object-cover ${
            loaded ? "opacity-100" : "opacity-0"
          } group-hover:scale-110 transition-opacity duration-300`}
        />
      )}

      {/* Rotation Controls - appear on hover (only if logged in) */}
      {loaded && !error && isAuthenticated && (
        <div className="absolute inset-0 flex items-start justify-between p-2 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <button
            onClick={(e) => handleRotate(270, e)}
            disabled={rotating}
            className="bg-black/40 hover:bg-black/60 text-white/90 rounded p-1.5 transition-colors disabled:opacity-50 shadow-md relative z-20"
            title="Rotate left 90°"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-4 w-4"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M3 10h10a8 8 0 018 8v2M3 10l6 6m-6-6l6-6"
              />
            </svg>
          </button>
          <button
            onClick={(e) => handleRotate(90, e)}
            disabled={rotating}
            className="bg-black/40 hover:bg-black/60 text-white/90 rounded p-1.5 transition-colors disabled:opacity-50 shadow-md relative z-20"
            title="Rotate right 90°"
          >
            <svg
              xmlns="http://www.w3.org/2000/svg"
              className="h-5 w-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M21 10H11a8 8 0 00-8 8v2m18-10l-6 6m6-6l-6-6"
              />
            </svg>
          </button>
        </div>
      )}

      {/* Enhanced Information Overlay */}
      {loaded && !error && (
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/60 to-transparent p-3 opacity-0 group-hover:opacity-100 transition-opacity duration-200">
          <div className="text-white text-sm space-y-1">
            {/* Trigpoint waypoint and name */}
            {photo.trig_id && photo.trig_name && (
              <div className="font-bold">
                {formatWaypoint(photo.trig_id)} : {photo.trig_name}
              </div>
            )}

            {/* Copyright and user info (if not public domain) */}
            {!isPublicDomain && photo.user_name && (
              <div className="text-xs text-white/90">
                © <span className="font-semibold">{photo.user_name}</span>
                {photo.log_date && (
                  <span className="ml-1">{formatLogDate(photo.log_date)}</span>
                )}
              </div>
            )}

            {/* Caption */}
            {!isEmptyOrNone(photo.caption) && (
              <div className="font-bold line-clamp-2">{photo.caption}</div>
            )}

            {/* Description */}
            {!isEmptyOrNone(photo.text_desc) && (
              <div className="text-xs text-white/90 line-clamp-2">
                {photo.text_desc}
              </div>
            )}

            {/* Aggregate rating (only shown when photo has votes) */}
            {photo.vote_count != null && photo.vote_count > 0 && photo.average_score != null && (
              <div className="flex items-center gap-1">
                <StarRating rating={photo.average_score / 2} size="sm" />
                <span className="text-xs text-white/70">
                  ({photo.vote_count})
                </span>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

