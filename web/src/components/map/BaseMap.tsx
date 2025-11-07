import { useEffect } from "react";
import { MapContainer, TileLayer, useMap } from "react-leaflet";
import type { LatLngExpression } from "leaflet";
import { getTileLayer } from "../../lib/mapConfig";

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
function TileLayerUpdater({ tileLayerId }: { tileLayerId: string }) {
  const map = useMap();
  
  useEffect(() => {
    // When tile layer changes, invalidate size to ensure proper rendering
    map.invalidateSize();
  }, [tileLayerId, map]);
  
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
  
  return (
    <div className={`relative ${className}`} style={{ height: heightStyle }}>
      <MapContainer
        center={center}
        zoom={zoom}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={true}
        className="rounded-lg"
        minZoom={5}
        maxZoom={18}
      >
        <TileLayer
          key={tileLayer.id}
          url={tileLayer.urlTemplate}
          attribution={tileLayer.attribution}
          maxZoom={tileLayer.maxZoom || 19}
          minZoom={tileLayer.minZoom || 0}
          {...(tileLayer.subdomains ? { subdomains: tileLayer.subdomains } : {})}
          tileSize={tileLayer.tileSize || 256}
          crossOrigin="anonymous"
        />
        
        <TileLayerUpdater tileLayerId={tileLayerId} />
        {onMapReady && <MapReadyNotifier onMapReady={onMapReady} />}
        
        {children}
      </MapContainer>
    </div>
  );
}

