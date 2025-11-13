import { Marker, Popup } from "react-leaflet";
import { Icon, type LatLngExpression } from "leaflet";
import { Link } from "react-router-dom";
import { getIconUrlForTrig } from "../../lib/mapIcons";
import type { TrigMarkerProps } from "./types";

/**
 * Individual trigpoint marker component
 * 
 * @stable - This component is used by both the main map and trig detail pages.
 * Its props interface (TrigMarkerProps) should remain stable to prevent breaking changes.
 * 
 * Renders a custom icon based on physical type and color mode,
 * with a popup showing basic trig information.
 * 
 * @remarks
 * Breaking changes to consider:
 * - Changing icon sizing or positioning
 * - Modifying popup structure or content
 * - Changing how coordinates are parsed
 * - Altering color mode behavior
 * 
 * Non-breaking changes:
 * - Styling improvements to popup content
 * - Adding optional props
 * - Performance optimizations
 */
export default function TrigMarker({
  trig,
  colorMode,
  logStatus = null,
  highlighted = false,
  onClick,
}: TrigMarkerProps) {
  const position: LatLngExpression = [
    typeof trig.wgs_lat === 'string' ? parseFloat(trig.wgs_lat) : trig.wgs_lat,
    typeof trig.wgs_long === 'string' ? parseFloat(trig.wgs_long) : trig.wgs_long,
  ];
  
  // Get the appropriate icon URL based on color mode
  const iconUrl = getIconUrlForTrig(
    trig.physical_type,
    trig.condition,
    colorMode,
    logStatus,
    highlighted
  );
  
  // Create Leaflet icon
  const icon = new Icon({
    iconUrl,
    iconSize: [32, 37], // Size of the icon
    iconAnchor: [16, 37], // Point of the icon which corresponds to marker's location
    popupAnchor: [0, -37], // Point from which the popup should open relative to iconAnchor
  });
  
  const handleClick = () => {
    if (onClick) {
      onClick(trig);
    }
  };
  
  return (
    <Marker
      position={position}
      icon={icon}
      eventHandlers={{
        click: handleClick,
      }}
    >
      <Popup>
        <div className="min-w-[200px]">
          <h3 className="font-bold text-trig-green-600 mb-2">
            {trig.waypoint} - {trig.name}
          </h3>
          
          <div className="space-y-1 text-sm mb-3">
            <div>
              <span className="font-semibold">Type:</span> {trig.physical_type}
            </div>
            <div>
              <span className="font-semibold">Grid ref:</span> {trig.osgb_gridref}
            </div>
            <div>
              <span className="font-semibold">Coordinates:</span>{" "}
              {typeof trig.wgs_lat === 'string' ? parseFloat(trig.wgs_lat).toFixed(5) : trig.wgs_lat.toFixed(5)},{" "}
              {typeof trig.wgs_long === 'string' ? parseFloat(trig.wgs_long).toFixed(5) : trig.wgs_long.toFixed(5)}
            </div>
          </div>
          
          <Link
            to={`/trig/${trig.id}`}
            className="inline-block bg-trig-green-600 hover:bg-trig-green-700 text-white px-3 py-1 rounded text-sm font-medium transition-colors"
          >
            View Details
          </Link>
        </div>
      </Popup>
    </Marker>
  );
}

