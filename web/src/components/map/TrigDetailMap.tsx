import { useState, useMemo, useCallback, useRef, useEffect } from "react";
import { Lock, LockOpen, Maximize2, Minimize2 } from "lucide-react";
import type { Map as LeafletMap } from "leaflet";
import BaseMap from "./BaseMap";
import TrigMarker from "./TrigMarker";
import TilesetSelector from "./TilesetSelector";
import { getTileLayer, MAP_CONFIG } from "../../lib/mapConfig";
import type { TrigDetailMapProps, IconColorMode } from "./types";

/**
 * Map component for trigpoint detail page
 * 
 * Shows a single trigpoint with its location, centered on the map.
 * Includes tile layer selector but uses condition color mode by default.
 * Map panning is locked by default to prevent interference when scrolling
 * the page, but can be unlocked via a toggle button.
 */
export default function TrigDetailMap({
  trig,
  height = MAP_CONFIG.detailMapHeight,
  className = "",
}: TrigDetailMapProps) {
  // Choose default tileset based on grid system:
  // - Irish Grid (ie): Use OpenTopoMap (OS Paper doesn't cover Ireland)
  // - GB Grid (gb): Use OS Paper (traditional OS maps)
  const defaultTileset = trig.grid_system === 'ie' ? 'openTopoMap' : 'osPaper';
  const [tileLayerId, setTileLayerId] = useState(defaultTileset);
  
  // Map interaction lock state - locked by default to avoid scroll interference
  const [isLocked, setIsLocked] = useState(true);
  
  // Map instance for resetting view when locking
  const [mapInstance, setMapInstance] = useState<LeafletMap | null>(null);
  
  // Fullscreen state
  const [isFullscreen, setIsFullscreen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  
  // Always use condition mode for detail maps (simpler UX)
  const colorMode: IconColorMode = 'condition';
  
  // Memoize center to avoid recreating array on every render
  const center = useMemo<[number, number]>(() => [
    typeof trig.wgs_lat === 'string' ? parseFloat(trig.wgs_lat) : trig.wgs_lat,
    typeof trig.wgs_long === 'string' ? parseFloat(trig.wgs_long) : trig.wgs_long,
  ], [trig.wgs_lat, trig.wgs_long]);
  
  // Adjust zoom level based on projection
  // EPSG:27700 has different zoom levels than EPSG:3857
  const currentTileLayer = getTileLayer(tileLayerId);
  const zoomLevel = useMemo(() => {
    if (currentTileLayer.crs === 'EPSG:27700') {
      return 8; // Good detail level for British National Grid
    }
    return MAP_CONFIG.detailMapZoom; // Default 14 for Web Mercator
  }, [currentTileLayer.crs]);
  
  // Handle lock toggle - reset view when locking
  const handleLockToggle = useCallback(() => {
    const newLocked = !isLocked;
    setIsLocked(newLocked);
    
    // Reset view to default when locking
    if (newLocked && mapInstance) {
      mapInstance.setView(center, zoomLevel);
    }
  }, [isLocked, mapInstance, center, zoomLevel]);
  
  // Handle fullscreen toggle
  const handleFullscreenToggle = useCallback(async () => {
    if (!containerRef.current) return;
    
    try {
      if (!document.fullscreenElement) {
        await containerRef.current.requestFullscreen();
        setIsFullscreen(true);
        // Unlock map interaction when entering fullscreen for better UX
        setIsLocked(false);
      } else {
        await document.exitFullscreen();
      }
    } catch (err) {
      console.error('Fullscreen toggle failed:', err);
    }
  }, []);
  
  // Listen for fullscreen changes (e.g., user pressing Escape)
  useEffect(() => {
    const handleFullscreenChange = () => {
      const isNowFullscreen = !!document.fullscreenElement;
      setIsFullscreen(isNowFullscreen);
      if (!isNowFullscreen) {
        // Lock map and reset view when exiting fullscreen
        setIsLocked(true);
        if (mapInstance) {
          setTimeout(() => {
            mapInstance.invalidateSize();
            mapInstance.setView(center, zoomLevel);
          }, 100);
        }
      } else {
        // Invalidate map size after entering fullscreen
        if (mapInstance) {
          setTimeout(() => mapInstance.invalidateSize(), 100);
        }
      }
    };
    
    document.addEventListener('fullscreenchange', handleFullscreenChange);
    return () => {
      document.removeEventListener('fullscreenchange', handleFullscreenChange);
    };
  }, [mapInstance, center, zoomLevel]);
  
  return (
    <div 
      ref={containerRef}
      className={`relative z-0 ${className} ${isFullscreen ? 'bg-black' : ''}`}
    >
      <BaseMap
        center={center}
        zoom={zoomLevel}
        height={isFullscreen ? "100dvh" : height}
        tileLayerId={tileLayerId}
        interactive={!isLocked}
        onMapReady={setMapInstance}
      >
        <TrigMarker
          trig={trig}
          colorMode={colorMode}
          highlighted={false}
          showPopup={false}
        />
      </BaseMap>
      
      {/* Tileset selector in top-right corner - z-[1001] to be above Leaflet controls */}
      <div className="absolute top-2 right-2 z-[1001]">
        <TilesetSelector
          value={tileLayerId}
          onChange={setTileLayerId}
          persistSelection={false}
        />
      </div>
      
      {/* Lock/unlock toggle below zoom controls - positioned to align with Leaflet's zoom buttons */}
      <div className="absolute top-[88px] left-[10px] z-[1001]">
        <button
          onClick={handleLockToggle}
          className={`w-[30px] h-[30px] flex items-center justify-center rounded-sm border-2 shadow-md transition-colors ${
            isLocked
              ? "bg-white border-gray-400 text-gray-600 hover:bg-gray-50"
              : "bg-trig-green-600 border-trig-green-700 text-white hover:bg-trig-green-700"
          }`}
          title={isLocked ? "Unlock map panning" : "Lock map panning"}
          aria-label={isLocked ? "Unlock map panning" : "Lock map panning"}
        >
          {isLocked ? (
            <Lock className="w-4 h-4" />
          ) : (
            <LockOpen className="w-4 h-4" />
          )}
        </button>
      </div>
      
      {/* Fullscreen toggle button */}
      <div className="absolute top-[124px] left-[10px] z-[1001]">
        <button
          onClick={handleFullscreenToggle}
          className="w-[30px] h-[30px] flex items-center justify-center rounded-sm border-2 shadow-md transition-colors bg-white border-gray-400 text-gray-600 hover:bg-gray-50"
          title={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
          aria-label={isFullscreen ? "Exit fullscreen" : "Enter fullscreen"}
        >
          {isFullscreen ? (
            <Minimize2 className="w-4 h-4" />
          ) : (
            <Maximize2 className="w-4 h-4" />
          )}
        </button>
      </div>
      
    </div>
  );
}

