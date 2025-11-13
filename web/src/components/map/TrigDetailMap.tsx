import { useState, useMemo } from "react";
import BaseMap from "./BaseMap";
import TrigMarker from "./TrigMarker";
import TilesetSelector from "./TilesetSelector";
import { getPreferredTileLayer, getTileLayer, MAP_CONFIG } from "../../lib/mapConfig";
import type { TrigDetailMapProps, IconColorMode } from "./types";

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
  
  // Adjust zoom level based on projection
  // EPSG:27700 has different zoom levels than EPSG:3857
  const currentTileLayer = getTileLayer(tileLayerId);
  const zoomLevel = useMemo(() => {
    if (currentTileLayer.crs === 'EPSG:27700') {
      return 8; // Good detail level for British National Grid
    }
    return MAP_CONFIG.detailMapZoom; // Default 14 for Web Mercator
  }, [currentTileLayer.crs]);
  
  return (
    <div className={`relative ${className}`}>
      <BaseMap
        center={center}
        zoom={zoomLevel}
        height={height}
        tileLayerId={tileLayerId}
      >
        <TrigMarker
          trig={trig}
          colorMode={colorMode}
          highlighted={false}
          showPopup={false}
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

