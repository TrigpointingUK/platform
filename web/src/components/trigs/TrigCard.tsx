import { Link } from "react-router-dom";

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

// Helper to get physical type abbreviation
function getPhysicalTypeAbbrev(type: string): string {
  const abbrevs: Record<string, string> = {
    Pillar: "P",
    Bolt: "B",
    FBM: "F",
    "Passive Station": "PS",
    "Active Station": "AS",
    Intersection: "I",
    Other: "O",
  };
  return abbrevs[type] || type.charAt(0).toUpperCase();
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

export function TrigCard({ trig, showDistance = true, centerLat, centerLon }: TrigCardProps) {
  // Calculate bearing if we have center coordinates
  let bearing: number | null = null;
  if (centerLat !== undefined && centerLon !== undefined) {
    const trigLat = parseFloat(trig.wgs_lat);
    const trigLon = parseFloat(trig.wgs_long);
    if (!isNaN(trigLat) && !isNaN(trigLon)) {
      bearing = calculateBearing(centerLat, centerLon, trigLat, trigLon);
    }
  }
  
  const conditionInfo = getConditionInfo(trig.condition);
  
  return (
    <Link
      to={`/trig/${trig.id}`}
      className="block border-b border-gray-200 py-3 px-4 hover:bg-gray-50 transition-colors"
    >
      <div className="flex items-center justify-between gap-3">
        {/* Left side: Main info */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            {/* Physical type badge */}
            <span className="inline-flex items-center justify-center w-6 h-6 text-xs font-bold text-white bg-blue-600 rounded">
              {getPhysicalTypeAbbrev(trig.physical_type)}
            </span>
            
            {/* Name */}
            <h3 className="font-medium text-gray-900 truncate">
              {trig.name}
            </h3>
            
            {/* Condition indicator */}
            <img 
              src={`/icons/conditions/${conditionInfo.icon}`}
              alt={conditionInfo.label}
              title={conditionInfo.label}
              className="w-4 h-4"
            />
          </div>
          
          {/* Grid reference & waypoint */}
          <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
            <span className="font-mono">{trig.osgb_gridref}</span>
            <span className="text-gray-400">•</span>
            <span>{trig.waypoint}</span>
          </div>
        </div>
        
        {/* Right side: Direction arrow and Distance */}
        {showDistance && trig.distance_km !== undefined && (
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
                {trig.distance_km.toFixed(1)}
              </div>
              <div className="text-xs text-gray-500">km</div>
            </div>
          </div>
        )}
      </div>
    </Link>
  );
}

