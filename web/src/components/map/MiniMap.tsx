import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { TILE_LAYERS } from '../../lib/mapConfig';
import { getCRS } from '../../lib/projections';

interface MiniMapProps {
  lat: number;
  lng: number;
}

/**
 * Mini-map component for display within popups
 * 
 * Shows a small, highly-zoomed OS Paper (EPSG:27700) map view with a blue circle marker.
 * Uses vanilla Leaflet API (not React-Leaflet) for lifecycle management within popups.
 * 
 * @remarks
 * - Always uses OS Paper tileset regardless of main map tileset
 * - Zoom level 8 for EPSG:27700 shows approximately 1000m width (896m at zoom 8)
 * - Blue circle marker indicates exact location without obscuring map features
 * - Event propagation is blocked to prevent interference with main map
 * - Map is initialized after DOM mount and cleaned up on unmount
 */
export default function MiniMap({ lat, lng }: MiniMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  
  useEffect(() => {
    // Don't initialize if container isn't ready
    if (!mapContainerRef.current) return;
    
    // Don't initialize twice
    if (mapInstanceRef.current) return;
    
    // Get OS Paper tile layer configuration
    const osPaperLayer = TILE_LAYERS.osPaper;
    const crs = getCRS('EPSG:27700');
    
    // For EPSG:27700 with resolutions [896.0, 448.0, 224.0, 112.0, 56.0, 28.0, 14.0, 7.0, 3.5, 1.75...]
    // Zoom 9 (resolution 3.5) gives us ~150px * 3.5 = 525m actual width
    // But with the bounds and visible area, zoom 8 (resolution 7.0) is closer to 1000m
    // Let's use zoom 8 for approximately 1000m width
    const miniMapZoom = 8;
    
    try {
      // Initialize the map
      const map = L.map(mapContainerRef.current, {
        center: [lat, lng],
        zoom: miniMapZoom,
        zoomControl: false,
        attributionControl: false,
        dragging: true,
        scrollWheelZoom: false,
        doubleClickZoom: false,
        boxZoom: false,
        keyboard: false,
        crs: crs,
      });
      
      // Add OS Paper tile layer
      L.tileLayer(osPaperLayer.urlTemplate, {
        attribution: osPaperLayer.attribution,
        maxZoom: osPaperLayer.maxZoom,
        maxNativeZoom: osPaperLayer.maxNativeZoom,
        minZoom: osPaperLayer.minZoom,
        tileSize: osPaperLayer.tileSize || 256,
      }).addTo(map);
      
      // Add a thin blue circle marker to indicate the exact location
      L.circleMarker([lat, lng], {
        radius: 24, // 3x the original diameter (8 * 3)
        color: '#2563eb', // Blue
        weight: 2,
        fillColor: '#3b82f6',
        fillOpacity: 0.3,
      }).addTo(map);
      
      // Prevent events from propagating to parent map
      const container = mapContainerRef.current;
      L.DomEvent.disableClickPropagation(container);
      L.DomEvent.disableScrollPropagation(container);
      
      // Store map instance for cleanup
      mapInstanceRef.current = map;
      
    } catch (error) {
      console.error('Failed to initialize mini-map:', error);
    }
    
    // Cleanup on unmount
    return () => {
      if (mapInstanceRef.current) {
        mapInstanceRef.current.remove();
        mapInstanceRef.current = null;
      }
    };
  }, [lat, lng]);
  
  return (
    <div 
      ref={mapContainerRef} 
      className="mini-map-container"
      style={{ 
        width: '150px', 
        height: '150px',
        border: '1px solid #ddd',
        borderRadius: '4px',
        marginBottom: '12px',
      }}
    />
  );
}

