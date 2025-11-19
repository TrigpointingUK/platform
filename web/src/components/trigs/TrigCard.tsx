import { Link } from "react-router-dom";
import type { UserLogStatus } from "../../lib/mapIcons";

interface Trig {
  id: number;
  waypoint: string;
  name: string;
  physical_type: string;
  condition: string;
  wgs_lat: string;
  wgs_long: string;
  osgb_gridref: string;
  status_name?: string;
  distance_km?: number;
}

interface TrigCardProps {
  trig: Trig;
  showDistance?: boolean;
  centerLat?: number;
  centerLon?: number;
  distanceUnit?: 'K' | 'M'; // K=km, M=miles
  logStatus?: UserLogStatus | null;
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

// Helper to get status badge info (abbreviation and color)
function getStatusInfo(statusName?: string): { abbrev: string; color: string } {
  const statusMap: Record<string, { abbrev: string; color: string }> = {
    Pillar: { abbrev: "P", color: "bg-blue-600" },
    "Major mark": { abbrev: "MM", color: "bg-green-600" },
    "Minor mark": { abbrev: "m", color: "bg-yellow-600" },
    Intersected: { abbrev: "I", color: "bg-orange-600" },
    "User Added": { abbrev: "UA", color: "bg-red-600" },
    Controversial: { abbrev: "C", color: "bg-gray-600" },
  };
  
  if (statusName && statusMap[statusName]) {
    return statusMap[statusName];
  }
  
  // Default fallback
  return { abbrev: "?", color: "bg-gray-400" };
}

// Calculate bearing from one point to another (in degrees, 0 = North)
function calculateBearing(lat1: number, lon1: number, lat2: number, lon2: number): number {
  const toRadians = (degrees: number) => degrees * Math.PI / 180;
  const toDegrees = (radians: number) => radians * 180 / Math.PI;
  
  const dLon = toRadians(lon2 - lon1);
  const lat1Rad = toRadians(lat1);
  const lat2Rad = toRadians(lat2);
  
  const y = Math.sin(dLon) * Math.cos(lat2Rad);
  const x = Math.cos(lat1Rad) * Math.sin(lat2Rad) -
            Math.sin(lat1Rad) * Math.cos(lat2Rad) * Math.cos(dLon);
  
  const bearing = toDegrees(Math.atan2(y, x));
  
  // Normalize to 0-360 degrees
  return (bearing + 360) % 360;
}

export function TrigCard({ 
  trig, 
  showDistance = true, 
  centerLat, 
  centerLon,
  distanceUnit = 'K',
  logStatus = null
}: TrigCardProps) {
  // Calculate bearing if we have center coordinates
  let bearing: number | null = null;
  if (centerLat !== undefined && centerLon !== undefined) {
    const trigLat = parseFloat(trig.wgs_lat);
    const trigLon = parseFloat(trig.wgs_long);
    if (!isNaN(trigLat) && !isNaN(trigLon)) {
      bearing = calculateBearing(centerLat, centerLon, trigLat, trigLon);
    }
  }
  
  // Convert distance based on unit preference
  const displayDistance = trig.distance_km !== undefined
    ? distanceUnit === 'M'
      ? trig.distance_km * 0.621371  // km to miles
      : trig.distance_km
    : undefined;
  
  const distanceLabel = distanceUnit === 'M' ? 'mi' : 'km';
  
  const conditionInfo = getConditionInfo(trig.condition);
  const statusInfo = getStatusInfo(trig.status_name);
  
  return (
    <Link
      to={`/trigs/${trig.id}`}
      className="block border-b border-gray-200 py-3 px-4 hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-center justify-between gap-3">
        {/* Left side: Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {/* Status badge */}
            <span 
              className={`inline-flex items-center justify-center min-w-6 h-6 px-1 text-xs font-bold text-white rounded ${statusInfo.color}`}
              title={trig.status_name || "Unknown status"}
            >
              {statusInfo.abbrev}
            </span>
            
            {/* Name */}
            <h3 className="font-medium text-gray-900 truncate">
              {trig.name}
            </h3>
            
            {/* Logged indicator - show checkmark if user has logged this trig */}
            {logStatus?.hasLogged && (
              <span 
                className="inline-flex items-center justify-center w-5 h-5 text-xs font-bold text-white bg-trig-green-600 rounded-full" 
                title="You have logged this trig"
              >
                ✓
              </span>
            )}
            
            {/* Condition indicator */}
            <img 
              src={`/icons/conditions/${conditionInfo.icon}`}
              alt={conditionInfo.label}
              title={conditionInfo.label}
              className="w-4 h-4"
            />
          </div>
          
          {/* Grid reference, waypoint & physical type */}
          <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
            <span className="font-mono">{trig.osgb_gridref}</span>
            <span className="text-gray-400">•</span>
            <span>{trig.waypoint}</span>
            {trig.physical_type && (
              <>
                <span className="text-gray-400">•</span>
                <span className="text-gray-500 text-xs">{trig.physical_type}</span>
              </>
            )}
          </div>
        </div>
        
        {/* Right side: Direction arrow and Distance */}
        {showDistance && displayDistance !== undefined && (
          <div className="flex items-center gap-2 flex-shrink-0">
            {/* Direction arrow */}
            {bearing !== null && (
              <div className="text-gray-600" title={`Bearing: ${bearing.toFixed(0)}°`}>
                <svg 
                  width="20" 
                  height="20" 
                  viewBox="0 0 24 24" 
                  fill="none" 
                  stroke="currentColor" 
                  strokeWidth="2.5"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  style={{ transform: `rotate(${bearing}deg)` }}
                >
                  <path d="M12 5l0 14M12 5l-4 4M12 5l4 4" />
                </svg>
              </div>
            )}
            
            {/* Distance */}
            <div className="text-right">
              <div className="text-lg font-semibold text-gray-900">
                {displayDistance.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500">{distanceLabel}</div>
            </div>
          </div>
        )}
      </div>
    </Link>
  );
}

