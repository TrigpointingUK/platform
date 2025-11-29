import { Link, useNavigate } from "react-router-dom";
import Card from "../ui/Card";
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
  osgb_gridref?: string;
  location_distance_m?: number;
  photos?: Photo[];
}

interface LogCardProps {
  log: Log;
  // Deprecated: use log.trig_name and log.user_name instead
  userName?: string;
  trigName?: string;
  onPhotoUpdate?: () => void;
}

// Helper function to get condition icon and label
function getConditionInfo(code: string): { icon: string; label: string } {
  const conditions: Record<string, { icon: string; label: string }> = {
    Z: { icon: "c_unknown.png", label: "Not Logged" },
    N: { icon: "c_possiblymissing.png", label: "Couldn't Find" },
    G: { icon: "c_good.png", label: "Good" },
    S: { icon: "c_slightlydamaged.png", label: "Slightly Damaged" },
    C: { icon: "c_slightlydamaged.png", label: "Converted" },
    D: { icon: "c_damaged.png", label: "Damaged" },
    R: { icon: "c_toppled.png", label: "Remains" },
    T: { icon: "c_toppled.png", label: "Toppled" },
    M: { icon: "c_toppled.png", label: "Moved" },
    Q: { icon: "c_possiblymissing.png", label: "Possibly Missing" },
    X: { icon: "c_definitelymissing.png", label: "Destroyed" },
    V: { icon: "c_unreachablebutvisible.png", label: "Unreachable but Visible" },
    P: { icon: "c_unknown.png", label: "Inaccessible" },
    U: { icon: "c_unknown.png", label: "Unknown" },
    "-": { icon: "c_nolog.png", label: "Not Visited" },
  };
  return conditions[code] || { icon: "c_unknown.png", label: code };
}

export default function LogCard({ log, userName, trigName }: LogCardProps) {
  const navigate = useNavigate();
  const conditionInfo = getConditionInfo(log.condition);
  const formattedDate = new Date(log.date).toLocaleDateString("en-GB", {
    day: "numeric",
    month: "short",
    year: "numeric",
  });

  // Debug logging for location data
  if (log.osgb_gridref || log.location_distance_m !== undefined) {
    console.log('LogCard location data:', {
      id: log.id,
      gridref: log.osgb_gridref,
      distance: log.location_distance_m,
      showLocation: !!(log.osgb_gridref && log.location_distance_m !== undefined)
    });
  }

  // Use denormalized fields if available, otherwise fall back to props
  const displayTrigName = log.trig_name || trigName;
  const displayUserName = log.user_name || userName;

  // Format trig ID with minimum 4 digits (TP0023, TP1234, TP34567)
  const formattedTrigId = `TP${log.trig_id.toString().padStart(4, '0')}`;

  // Format distance based on threshold
  const formatDistance = (distance?: number) => {
    if (distance === undefined || distance === null) return null;
    
    const distanceText = distance < 1000 
      ? `${Math.round(distance)}m` 
      : `${(distance / 1000).toFixed(1)}km`;
    
    const colorClass = distance <= 25 ? 'text-gray-500' : 'text-red-700';
    
    return (
      <span className={colorClass}>
        {distanceText}
      </span>
    );
  };

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
              to={`/trigs/${log.trig_id}`}
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
              {/* Condition Icon */}
              <img 
                src={`/icons/conditions/${conditionInfo.icon}`}
                alt={conditionInfo.label}
                title={conditionInfo.label}
                className="w-4 h-4"
              />
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
              
              {/* Location and Distance */}
              {log.osgb_gridref && log.location_distance_m !== undefined && (
                <>
                  <span className="text-gray-400">·</span>
                  <span className="text-gray-600 text-xs font-mono">{log.osgb_gridref}</span>
                  <span className="text-gray-400">·</span>
                  {formatDistance(log.location_distance_m)}
                </>
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
