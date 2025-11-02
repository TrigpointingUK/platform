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
}

// Helper function to get condition label
function getConditionLabel(code: string): string {
  const conditions: Record<string, string> = {
    G: "Good",
    S: "Slightly damaged",
    D: "Damaged",
    T: "Toppled",
    M: "Missing",
    P: "Possibly missing",
    U: "Unknown",
  };
  return conditions[code] || code;
}

// Helper function to get condition color
function getConditionColor(code: string): string {
  const colors: Record<string, string> = {
    G: "text-green-600",
    S: "text-yellow-600",
    D: "text-orange-600",
    T: "text-red-600",
    M: "text-red-700",
    P: "text-red-500",
    U: "text-gray-500",
  };
  return colors[code] || "text-gray-500";
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

export function TrigCard({ trig, showDistance = true }: TrigCardProps) {
  return (
    <Link
      to={`/trigs/${trig.id}`}
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
            <span className={`text-sm ${getConditionColor(trig.condition)}`} title={getConditionLabel(trig.condition)}>
              ●
            </span>
          </div>
          
          {/* Grid reference & waypoint */}
          <div className="flex items-center gap-3 mt-1 text-sm text-gray-600">
            <span className="font-mono">{trig.osgb_gridref}</span>
            <span className="text-gray-400">•</span>
            <span>{trig.waypoint}</span>
          </div>
        </div>
        
        {/* Right side: Distance */}
        {showDistance && trig.distance_km !== undefined && (
          <div className="flex-shrink-0 text-right">
            <div className="text-lg font-semibold text-gray-900">
              {trig.distance_km.toFixed(1)}
            </div>
            <div className="text-xs text-gray-500">km</div>
          </div>
        )}
      </div>
    </Link>
  );
}

