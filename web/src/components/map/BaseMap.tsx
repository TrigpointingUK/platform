import { useEffect } from "react";
import { MapContainer, TileLayer, useMap, ScaleControl } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import { getTileLayer, MAP_CONFIG } from "../../lib/mapConfig";

interface BaseMapProps {
  center: LatLngExpression;
  zoom: number;
  height?: number | string;
  tileLayerId: string;
  children?: React.ReactNode;
  onMapReady?: (map: L.Map) => void;
  className?: string;
}

/**
 * Component to handle tile layer updates
 */
function TileLayerUpdater({ tileLayerId, minZoom, maxZoom }: { tileLayerId: string; minZoom: number; maxZoom: number }) {
  const map = useMap();
  
  useEffect(() => {
    // When tile layer changes, update zoom limits and invalidate size
    map.setMinZoom(minZoom);
    map.setMaxZoom(maxZoom);
    map.invalidateSize();
    
    // If current zoom is outside new limits, adjust it
    const currentZoom = map.getZoom();
    if (currentZoom < minZoom) {
      map.setZoom(minZoom);
    } else if (currentZoom > maxZoom) {
      map.setZoom(maxZoom);
    }
  }, [tileLayerId, minZoom, maxZoom, map]);
  
  return null;
}

/**
 * Component to notify parent when map is ready
 */
function MapReadyNotifier({ onMapReady }: { onMapReady?: (map: L.Map) => void }) {
  const map = useMap();
  
  useEffect(() => {
    if (onMapReady) {
      onMapReady(map);
    }
  }, [map, onMapReady]);
  
  return null;
}

/**
 * Base map component using Leaflet
 * 
 * Provides a reusable map with configurable tile layers and markers.
 */
export default function BaseMap({
  center,
  zoom,
  height = 400,
  tileLayerId,
  children,
  onMapReady,
  className = "",
}: BaseMapProps) {
  const tileLayer = getTileLayer(tileLayerId);
  
  const heightStyle = typeof height === 'number' ? `${height}px` : height;
  
  // Use the most restrictive zoom limits from both global config and tileset
  const minZoom = Math.max(tileLayer.minZoom ?? 0, MAP_CONFIG.minZoom);
  const maxZoom = Math.min(tileLayer.maxZoom ?? 20, MAP_CONFIG.maxZoom);
  
  return (
    <div className={`relative ${className}`} style={{ height: heightStyle }}>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        className="rounded-lg"
        minZoom={minZoom}
        maxZoom={maxZoom}
      >
        <TileLayer
          key={tileLayer.id}
          url={tileLayer.urlTemplate}
          attribution={tileLayer.attribution}
          maxZoom={tileLayer.maxZoom || 19}
          maxNativeZoom={tileLayer.maxNativeZoom}
          minZoom={tileLayer.minZoom || 0}
          {...(tileLayer.subdomains ? { subdomains: tileLayer.subdomains } : {})}
          tileSize={tileLayer.tileSize || 256}
          crossOrigin="anonymous"
        />
        
        <TileLayerUpdater tileLayerId={tileLayerId} minZoom={minZoom} maxZoom={maxZoom} />
        {onMapReady && <MapReadyNotifier onMapReady={onMapReady} />}
        
        {/* Scale bar at bottom left */}
        <ScaleControl position="bottomleft" imperial={false} />
        
        {children}
      </MapContainer>
    </div>
  );
}

