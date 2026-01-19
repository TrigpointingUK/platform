import { Link, useNavigate } from "react-router-dom";
import Card from "../ui/Card";
import StarRating from "../ui/StarRating";
import DirectionArrow from "../ui/DirectionArrow";
import { Photo } from "../../lib/api";
import { osgbToWGS84 } from "../../lib/coordinates";

interface Log {
  id: number;
  trig_id: number;
  user_id: number;
  trig_name?: string;
  user_name?: string;
  trig_lat?: number | null;
  trig_lon?: number | null;
  trig_condition?: string | null;
  trig_status_name?: string | null;
  trig_physical_type?: string | null;
  date: string;
  time: string;
  condition: string;
  comment: string;
  score: number;
  osgb_gridref?: string;
  osgb_eastings?: number;
  osgb_northings?: number;
  location_distance_m?: number;
  distance_km?: number | null;
  photos?: Photo[];
}

interface LogCardProps {
  log: Log;
  // Deprecated: use log.trig_name and log.user_name instead
  userName?: string;
  trigName?: string;
  onPhotoUpdate?: () => void;
  isCurrentUserLog?: boolean;
  /** Show distance from filter center point (uses log.distance_km) */
  showDistance?: boolean;
  /** Show the curated trig condition icon before the TP number */
  showTrigCondition?: boolean;
  /** Show the trig header line (waypoint, name, type). Default: true */
  showTrigInfo?: boolean;
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

// Helper to get status icon info
function getStatusInfo(statusName?: string | null): { icon?: string; abbrev: string } {
  const statusMap: Record<string, { icon: string; abbrev: string }> = {
    Pillar: { icon: "/icons/t_pillar.png", abbrev: "P" },
    "Major mark": { icon: "/icons/t_fbm.png", abbrev: "MM" },
    "Minor mark": { icon: "/icons/t_passive.png", abbrev: "m" },
    Intersected: { icon: "/icons/t_intersected.png", abbrev: "I" },
    "User Added": { icon: "/icons/t_user_added.svg", abbrev: "UA" },
    Controversial: { icon: "/icons/t_controversial.svg", abbrev: "C" },
  };
  
  const normalizedStatusName = statusName?.trim();
  
  if (normalizedStatusName && statusMap[normalizedStatusName]) {
    return statusMap[normalizedStatusName];
  }
  
  // Fallback check for case-insensitive match
  if (normalizedStatusName) {
    const lowerName = normalizedStatusName.toLowerCase();
    const match = Object.keys(statusMap).find(key => key.toLowerCase() === lowerName);
    if (match) {
      return statusMap[match];
    }
  }
  
  return { abbrev: "?" };
}

export default function LogCard({ log, userName, trigName, isCurrentUserLog = false, showDistance = false, showTrigCondition = false, showTrigInfo = true }: LogCardProps) {
  const navigate = useNavigate();
  const conditionInfo = getConditionInfo(log.condition);
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

  // Calculate bearing from point A to point B (in degrees, 0 = North)
  const calculateBearing = (lat1: number, lon1: number, lat2: number, lon2: number): number => {
    const toRad = (deg: number) => deg * (Math.PI / 180);
    const toDeg = (rad: number) => rad * (180 / Math.PI);
    
    const φ1 = toRad(lat1);
    const φ2 = toRad(lat2);
    const Δλ = toRad(lon2 - lon1);
    
    const y = Math.sin(Δλ) * Math.cos(φ2);
    const x = Math.cos(φ1) * Math.sin(φ2) - Math.sin(φ1) * Math.cos(φ2) * Math.cos(Δλ);
    const θ = Math.atan2(y, x);
    
    return (toDeg(θ) + 360) % 360; // Normalize to 0-360
  };

  // Format distance with direction arrow
  const formatDistance = (distance?: number) => {
    if (distance === undefined || distance === null) return null;
    
    const distanceText = distance < 1000 
      ? `${Math.round(distance)}m` 
      : `${(distance / 1000).toFixed(1)}km`;
    
    const colorClass = distance <= 25 ? 'text-gray-500' : 'text-red-700';
    
    // Calculate bearing if we have coordinates
    let bearing: number | null = null;
    if (log.trig_lat != null && log.trig_lon != null && 
        log.osgb_eastings !== undefined && log.osgb_northings !== undefined) {
      // Convert log OSGB to WGS84
      const logWGS84 = osgbToWGS84(log.osgb_eastings, log.osgb_northings);
      bearing = calculateBearing(log.trig_lat, log.trig_lon, logWGS84.lat, logWGS84.lon);
    }
    
    return (
      <span className={`${colorClass} inline-flex items-center gap-1`}>
        {distanceText}
        {bearing !== null && <DirectionArrow bearing={bearing} size={14} />}
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

  // Apply light green background for current user's logs
  // Use !bg-green-50 to override Card's default bg-white
  const cardClassName = isCurrentUserLog
    ? "hover:shadow-lg transition-shadow cursor-pointer !bg-green-50 dark:!bg-green-900/30"
    : "hover:shadow-lg transition-shadow cursor-pointer";

  return (
    <Card 
      className={cardClassName}
      onClick={handleCardClick}
    >
      <div className="flex flex-col gap-3">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            {showTrigInfo && (
              <Link
                to={`/trigs/${log.trig_id}`}
                className="inline-flex items-center gap-1.5 text-lg font-semibold text-trig-green-600 hover:text-trig-green-700 hover:underline"
                onClick={(e) => e.stopPropagation()}
              >
                {/* Status icon (type) - always shown */}
                {log.trig_status_name && getStatusInfo(log.trig_status_name).icon && (
                  <img
                    src={getStatusInfo(log.trig_status_name).icon}
                    alt={getStatusInfo(log.trig_status_name).abbrev}
                    title={log.trig_status_name}
                    className="w-6 h-6 object-contain"
                  />
                )}
                {/* Trig condition icon (square) - only shown when enabled */}
                {showTrigCondition && log.trig_condition && (
                  <img
                    src={`/icons/conditions/${getConditionInfo(log.trig_condition).icon}`}
                    alt={getConditionInfo(log.trig_condition).label}
                    title={`Trig condition: ${getConditionInfo(log.trig_condition).label}`}
                    className="w-5 h-5"
                  />
                )}
                {formattedTrigId}
                {displayTrigName && (
                  <>
                    <span className="text-gray-400 dark:text-gray-500 mx-2">·</span>
                    <span className="font-normal text-gray-700 dark:text-gray-300">{displayTrigName}</span>
                  </>
                )}
                {log.trig_physical_type && (
                  <>
                    <span className="text-gray-400 dark:text-gray-500 mx-1">·</span>
                    <span className="font-normal text-gray-500 dark:text-gray-400 text-sm">{log.trig_physical_type}</span>
                  </>
                )}
              </Link>
            )}
            <div className="flex flex-wrap items-center gap-2 text-base text-gray-600 dark:text-gray-400">
              <span>
                {displayUserName ? (
                  <Link
                    to={`/profile/${log.user_id}`}
                    className="text-trig-green-600 hover:underline font-semibold text-lg"
                    onClick={(e) => e.stopPropagation()}
                  >
                    {displayUserName}
                  </Link>
                ) : (
                  <Link
                    to={`/profile/${log.user_id}`}
                    className="text-trig-green-600 hover:underline font-semibold text-lg"
                    onClick={(e) => e.stopPropagation()}
                  >
                    User #{log.user_id}
                  </Link>
                )}
              </span>
              <span className="text-gray-400 dark:text-gray-500">·</span>
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
              <span className="text-gray-400 dark:text-gray-500">·</span>
              <span className="text-gray-700 dark:text-gray-300">{formattedDate}</span>
              {log.time && log.time !== "12:00:00" && (
                <span className="text-gray-500 dark:text-gray-400">{log.time}</span>
              )}
              
              {/* Distance from filter center point */}
              {showDistance && log.distance_km != null && (
                <>
                  <span className="text-gray-400 dark:text-gray-500">·</span>
                  <span className="text-sm text-blue-600 font-medium">
                    {log.distance_km < 1 
                      ? `${Math.round(log.distance_km * 1000)}m away`
                      : `${log.distance_km.toFixed(1)}km away`}
                  </span>
                </>
              )}
              
              {/* Location and Distance from log point */}
              {log.osgb_gridref && log.location_distance_m !== undefined && (
                <>
                  <span className="text-gray-400 dark:text-gray-500">·</span>
                  <span className="text-gray-600 dark:text-gray-400 font-mono">{log.osgb_gridref}</span>
                  <span className="text-gray-400 dark:text-gray-500">·</span>
                  <span className="text-sm">{formatDistance(log.location_distance_m)}</span>
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
                <p className="text-gray-700 dark:text-gray-300 text-sm leading-relaxed">{log.comment}</p>
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
                      className="h-full w-full object-cover rounded border border-gray-200 dark:border-gray-600 transition-all duration-200 group-hover:scale-110 group-hover:shadow-lg"
                      title={photo.caption}
                    />
                  </div>
                ))}
                {log.photos.length > 20 && (
                  <div className="h-20 w-20 flex items-center justify-center bg-gray-100 dark:bg-gray-700 rounded border border-gray-200 dark:border-gray-600 flex-shrink-0 text-sm text-gray-600 dark:text-gray-400">
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
