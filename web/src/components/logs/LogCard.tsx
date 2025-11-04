import { Link, useNavigate } from "react-router-dom";
import Card from "../ui/Card";
import Badge from "../ui/Badge";
import StarRating from "../ui/StarRating";
import { Photo } from "../../lib/api";

interface Log {
  id: number;
  trig_id: number;
  user_id: number;
  trig_name?: string;
  user_name?: string;
  date: string;
  time: string;
  condition: string;
  comment: string;
  score: number;
  photos?: Photo[];
}

interface LogCardProps {
  log: Log;
  // Deprecated: use log.trig_name and log.user_name instead
  userName?: string;
  trigName?: string;
  onPhotoUpdate?: () => void;
}

const conditionMap: Record<string, { label: string; variant: "good" | "damaged" | "missing" | "unknown" }> = {
  G: { label: "Good", variant: "good" },
  D: { label: "Damaged", variant: "damaged" },
  M: { label: "Missing", variant: "missing" },
  P: { label: "Possibly Missing", variant: "damaged" },
  U: { label: "Unknown", variant: "unknown" },
};

export default function LogCard({ log, userName, trigName }: LogCardProps) {
  const navigate = useNavigate();
  const condition = conditionMap[log.condition] || conditionMap.U;
  const formattedDate = new Date(log.date).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  // Use denormalized fields if available, otherwise fall back to props
  const displayTrigName = log.trig_name || trigName;
  const displayUserName = log.user_name || userName;

  // Format trig ID with minimum 4 digits (TP0023, TP1234, TP34567)
  const formattedTrigId = `TP${log.trig_id.toString().padStart(4, '0')}`;

  const handlePhotoClick = (photo: Photo, e: React.MouseEvent) => {
    e.stopPropagation(); // Prevent card click when clicking a photo
    // Navigate with the photo data and all photos from the log in state
    // This enables forward/back navigation in the photo viewer
    navigate(`/photos/${photo.id}`, { 
      state: { 
        photo,
        allPhotos: log.photos,
        context: 'log' // Flag to indicate this came from a log
      } 
    });
  };

  const handleCardClick = () => {
    navigate(`/logs/${log.id}`);
  };

  return (
    <Card 
      className="hover:shadow-lg transition-shadow cursor-pointer" 
      onClick={handleCardClick}
    >
      <div className="flex flex-col gap-3">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <Link
              to={`/trig/${log.trig_id}`}
              className="text-lg font-semibold text-trig-green-600 hover:text-trig-green-700 hover:underline"
              onClick={(e) => e.stopPropagation()}
            >
              {formattedTrigId}
              {displayTrigName && (
                <>
                  <span className="text-gray-400 mx-2">·</span>
                  <span className="font-normal text-gray-700">{displayTrigName}</span>
                </>
              )}
            </Link>
            <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
              <span>
                by{" "}
                {displayUserName ? (
                  <Link
                    to={`/profile/${log.user_id}`}
                    className="text-trig-green-600 hover:underline font-semibold text-base"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {displayUserName}
                  </Link>
                ) : (
                  <Link
                    to={`/profile/${log.user_id}`}
                    className="text-trig-green-600 hover:underline font-semibold text-base"
                    onClick={(e) => e.stopPropagation()}
                  >
                    User #{log.user_id}
                  </Link>
                )}
              </span>
              <span className="text-gray-400">·</span>
              <Badge variant={condition.variant}>{condition.label}</Badge>
              <StarRating 
                rating={log.score / 2} 
                size="sm" 
                title={`${log.score}/10`}
              />
              <span className="text-gray-400">·</span>
              <span className="text-gray-700">{formattedDate}</span>
              {log.time && log.time !== "12:00:00" && (
                <span className="text-gray-500 text-xs">{log.time}</span>
              )}
            </div>
          </div>
        </div>

        {/* Comment and Photos - Side by Side */}
        {(log.comment || (log.photos && log.photos.length > 0)) && (
          <div className="flex gap-4">
            {/* Comment - Left 33% */}
            <div className="flex-[2] min-w-0">
              {log.comment && (
                <p className="text-gray-700 text-sm leading-relaxed">{log.comment}</p>
              )}
            </div>

            {/* Photos - Right 66% */}
            {log.photos && log.photos.length > 0 && (
              <div className="flex-[1] flex gap-2 overflow-x-auto pb-2">
                {log.photos.slice(0, 20).map((photo) => (
                  <div
                    key={photo.id}
                    className="relative h-20 w-20 flex-shrink-0 cursor-pointer group"
                    onClick={(e) => handlePhotoClick(photo, e)}
                  >
                    <img
                      src={photo.icon_url}
                      alt={photo.caption}
                      className="h-full w-full object-cover rounded border border-gray-200 transition-all duration-200 group-hover:scale-110 group-hover:shadow-lg"
                      title={photo.caption}
                    />
                  </div>
                ))}
                {log.photos.length > 20 && (
                  <div className="h-20 w-20 flex items-center justify-center bg-gray-100 rounded border border-gray-200 flex-shrink-0 text-sm text-gray-600">
                    +{log.photos.length - 20}
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>
    </Card>
  );
}
