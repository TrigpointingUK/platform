import { useState } from "react";
import BaseMap from "./BaseMap";
import TrigMarker from "./TrigMarker";
import TilesetSelector from "./TilesetSelector";
import { getPreferredTileLayer, MAP_CONFIG } from "../../lib/mapConfig";
import type { IconColorMode } from "../../lib/mapIcons";

interface TrigData {
  id: number;
  waypoint: string;
  name: string;
  physical_type: string;
  condition: string;
  wgs_lat: string | number;
  wgs_long: string | number;
  osgb_gridref: string;
}

interface TrigDetailMapProps {
  trig: TrigData;
  height?: number;
  className?: string;
}

/**
 * Map component for trigpoint detail page
 * 
 * Shows a single trigpoint with its location, centered on the map.
 * Includes tile layer selector but uses condition color mode by default.
 */
export default function TrigDetailMap({
  trig,
  height = MAP_CONFIG.detailMapHeight,
  className = "",
}: TrigDetailMapProps) {
  const [tileLayerId, setTileLayerId] = useState(getPreferredTileLayer());
  
  // Always use condition mode for detail maps (simpler UX)
  const colorMode: IconColorMode = 'condition';
  
  const center: [number, number] = [
    typeof trig.wgs_lat === 'string' ? parseFloat(trig.wgs_lat) : trig.wgs_lat,
    typeof trig.wgs_long === 'string' ? parseFloat(trig.wgs_long) : trig.wgs_long,
  ];
  
  return (
    <div className={`relative ${className}`}>
      <BaseMap
        center={center}
        zoom={MAP_CONFIG.detailMapZoom}
        height={height}
        tileLayerId={tileLayerId}
      >
        <TrigMarker
          trig={trig}
          colorMode={colorMode}
          highlighted={false}
        />
      </BaseMap>
      
      {/* Tileset selector in top-right corner */}
      <div className="absolute top-2 right-2 z-[1000]">
        <TilesetSelector
          value={tileLayerId}
          onChange={setTileLayerId}
        />
      </div>
    </div>
  );
}

