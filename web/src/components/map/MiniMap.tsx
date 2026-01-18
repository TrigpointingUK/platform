import { useEffect, useRef } from 'react';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import { TILE_LAYERS } from '../../lib/mapConfig';
import { getCRS } from '../../lib/projections';

interface MiniMapProps {
  lat: number;
  lng: number;
  /** Grid system: 'gb' for British National Grid, 'ie' for Irish Grid */
  gridSystem?: 'gb' | 'ie';
}

/**
 * Mini-map component for display within popups
 * 
 * Shows a small, highly-zoomed map view with a blue circle marker.
 * Uses vanilla Leaflet API (not React-Leaflet) for lifecycle management within popups.
 * 
 * @remarks
 * - GB trigs use OS Paper tileset (EPSG:27700) at zoom 8
 * - Irish trigs use OpenTopoMap (EPSG:3857) at zoom 14
 * - Blue circle marker indicates exact location without obscuring map features
 * - Event propagation is blocked to prevent interference with main map
 * - Map is initialized after DOM mount and cleaned up on unmount
 */
export default function MiniMap({ lat, lng, gridSystem = 'gb' }: MiniMapProps) {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapInstanceRef = useRef<L.Map | null>(null);
  
  useEffect(() => {
    // Don't initialize if container isn't ready
    if (!mapContainerRef.current) return;
    
    // Don't initialize twice
    if (mapInstanceRef.current) return;
    
    // Choose tileset and CRS based on grid system
    // Irish Grid: Use OpenTopoMap (EPSG:3857) - OS Paper doesn't cover Ireland
    // GB Grid: Use OS Paper (EPSG:27700) - traditional OS maps
    const isIrish = gridSystem === 'ie';
    const tileLayer = isIrish ? TILE_LAYERS.openTopoMap : TILE_LAYERS.osPaper;
    const crs = isIrish ? L.CRS.EPSG3857 : getCRS('EPSG:27700');
    
    // Zoom levels differ between projections:
    // - EPSG:27700 zoom 8 shows ~1000m width
    // - EPSG:3857 zoom 14 shows similar detail level
    const miniMapZoom = isIrish ? 14 : 8;
    
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
      
      // Add tile layer
      L.tileLayer(tileLayer.urlTemplate, {
        attribution: tileLayer.attribution,
        maxZoom: tileLayer.maxZoom,
        maxNativeZoom: tileLayer.maxNativeZoom,
        minZoom: tileLayer.minZoom,
        tileSize: tileLayer.tileSize || 256,
        subdomains: tileLayer.subdomains || [],
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
  }, [lat, lng, gridSystem]);
  
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

