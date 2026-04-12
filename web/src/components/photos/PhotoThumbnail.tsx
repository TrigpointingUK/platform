import { useState } from "react";
import { useAuth0 } from "@auth0/auth0-react";
import toast from "react-hot-toast";
import { authenticatedPost, Photo } from "../../lib/api";
import StarRating from "../ui/StarRating";
import InteractiveStarRating from "../ui/InteractiveStarRating";
import { usePhotoRating } from "../../hooks/usePhotoRating";

const API_BASE = import.meta.env.VITE_API_BASE as string;

interface PhotoThumbnailProps {
  photo: Photo;
  onClick?: () => void;
  onPhotoRotated?: (updatedPhoto: Photo) => void;
}

function formatWaypoint(trigId: number): string {
  return `TP${trigId.toString().padStart(4, "0")}`;
}

function formatLogDate(dateString?: string): string {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });
}

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
  const { rating, rate } = usePhotoRating(loaded ? photo.id : null);

  const handleRotate = async (angle: number, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();

    setRotating(true);

    const visualAngle = angle === 270 ? -90 : angle;
    const newRotation = optimisticRotation + visualAngle;
    setOptimisticRotation(newRotation);

    try {
      const response = await authenticatedPost<Photo>(
        `${API_BASE}/v1/photos/${photo.id}/rotate`,
        { angle },
        getAccessTokenSilently
      );

      toast.success("Photo rotated successfully");

      if (onPhotoRotated) {
        onPhotoRotated(response);
      }

      setOptimisticRotation(0);
    } catch (err) {
      console.error("Failed to rotate photo:", err);
      toast.error("Failed to rotate photo. Please try again.");
      setOptimisticRotation(optimisticRotation);
    } finally {
      setRotating(false);
    }
  };

  const handleRate = (score: number) => {
    rate(score);
  };

  const isPublicDomain = photo.license === "Y";

  const userScore = rating?.user_score ?? 0;
  const avgScore = rating?.average_score ?? photo.average_score ?? null;
  const voteCount = rating?.vote_count ?? photo.vote_count ?? 0;

  const hasRating = voteCount > 0 && avgScore != null;
  const displayScore = userScore > 0 ? userScore : (avgScore ? Math.round(avgScore) : 0);

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
          } can-hover:group-hover:scale-110 transition-opacity duration-300`}
        />
      )}

      {/* Top Controls: Rotate + Rating -- always visible on mobile, hover-reveal on desktop */}
      {loaded && !error && (
        <div className="absolute inset-x-0 top-0 flex items-start justify-between p-2 can-hover:opacity-0 can-hover:group-hover:opacity-100 transition-opacity duration-200 z-10">
          {/* Rotate left */}
          {isAuthenticated ? (
            <button
              onClick={(e) => handleRotate(270, e)}
              disabled={rotating}
              className="bg-black/40 hover:bg-black/60 text-white/90 rounded p-1.5 transition-colors disabled:opacity-50 shadow-md"
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
          ) : (
            <div />
          )}

          {/* Star rating (centre) */}
          <div
            className="bg-black/40 rounded px-1.5 py-1 shadow-md flex items-center gap-1"
            onClick={(e) => { e.stopPropagation(); e.preventDefault(); }}
            onTouchEnd={(e) => e.stopPropagation()}
          >
            {isAuthenticated ? (
              <InteractiveStarRating
                rating={displayScore}
                onRate={handleRate}
                size="sm"
                colour="amber"
              />
            ) : (
              <StarRating
                rating={(avgScore ?? 0) / 2}
                size="sm"
                title={hasRating ? `${avgScore}/10 (${voteCount} vote${voteCount !== 1 ? "s" : ""})` : "Not yet rated"}
              />
            )}
            {hasRating && (
              <span className="text-[10px] text-white/70 leading-none">
                ({voteCount})
              </span>
            )}
          </div>

          {/* Rotate right */}
          {isAuthenticated ? (
            <button
              onClick={(e) => handleRotate(90, e)}
              disabled={rotating}
              className="bg-black/40 hover:bg-black/60 text-white/90 rounded p-1.5 transition-colors disabled:opacity-50 shadow-md"
              title="Rotate right 90°"
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
                  d="M21 10H11a8 8 0 00-8 8v2m18-10l-6 6m6-6l-6-6"
                />
              </svg>
            </button>
          ) : (
            <div />
          )}
        </div>
      )}

      {/* Bottom Information Overlay -- always visible on mobile, hover-reveal on desktop */}
      {loaded && !error && (
        <div className="absolute inset-x-0 bottom-0 bg-gradient-to-t from-black/80 via-black/60 to-transparent p-3 can-hover:opacity-0 can-hover:group-hover:opacity-100 transition-opacity duration-200">
          <div className="text-white text-sm space-y-1">
            {photo.trig_id && photo.trig_name && (
              <div className="font-bold">
                {formatWaypoint(photo.trig_id)} : {photo.trig_name}
              </div>
            )}

            {photo.user_name && (
              <div className="text-xs text-white/90">
                {!isPublicDomain && "© "}
                <span className="font-semibold">{photo.user_name}</span>
                {photo.log_date && (
                  <span className="ml-1">{formatLogDate(photo.log_date)}</span>
                )}
              </div>
            )}

            {!isEmptyOrNone(photo.caption) && (
              <div className="font-bold line-clamp-2">{photo.caption}</div>
            )}

            {!isEmptyOrNone(photo.text_desc) && (
              <div className="text-xs text-white/90 line-clamp-2">
                {photo.text_desc}
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
