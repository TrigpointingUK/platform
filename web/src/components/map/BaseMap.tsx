import { useEffect, useRef, useCallback } from "react";
import { MapContainer, TileLayer, useMap, ScaleControl } from "react-leaflet";
import { getTileLayer, MAP_CONFIG, type TileLayer as TileLayerType } from "../../lib/mapConfig";
import { getCRS } from "../../lib/projections";
import type { BaseMapProps } from "./types";

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
 * Component to dynamically enable/disable map interaction
 * 
 * MapContainer only reads interactive props on mount, so this component
 * allows toggling interaction after the map is created.
 */
function InteractionController({ 
  interactive, 
  scrollWheelZoom = true 
}: { 
  interactive: boolean; 
  scrollWheelZoom?: boolean;
}) {
  const map = useMap();
  
  useEffect(() => {
    if (interactive) {
      map.dragging.enable();
      map.touchZoom.enable();
      map.doubleClickZoom.enable();
      map.boxZoom.enable();
      map.keyboard.enable();
      if (scrollWheelZoom) {
        map.scrollWheelZoom.enable();
      }
    } else {
      map.dragging.disable();
      map.touchZoom.disable();
      map.doubleClickZoom.disable();
      map.boxZoom.disable();
      map.keyboard.disable();
      map.scrollWheelZoom.disable();
    }
  }, [map, interactive, scrollWheelZoom]);
  
  return null;
}

/**
 * Component to pre-fetch tiles in a buffer zone around the current viewport.
 * 
 * This loads tiles into the browser cache before they're needed, reducing
 * whitespace during panning. Works by creating Image objects that fetch
 * tile URLs - the browser caches them automatically.
 */
function TilePreloader({ tileLayer, bufferTiles = 3 }: { tileLayer: TileLayerType; bufferTiles?: number }) {
  const map = useMap();
  const preloadedTilesRef = useRef<Set<string>>(new Set());
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Convert lat/lng to tile coordinates
  const latLngToTile = useCallback((lat: number, lng: number, zoom: number) => {
    const n = Math.pow(2, zoom);
    const x = Math.floor((lng + 180) / 360 * n);
    const y = Math.floor((1 - Math.log(Math.tan(lat * Math.PI / 180) + 1 / Math.cos(lat * Math.PI / 180)) / Math.PI) / 2 * n);
    return { x, y };
  }, []);

  // Build tile URL from template
  const getTileUrl = useCallback((x: number, y: number, z: number) => {
    let url = tileLayer.urlTemplate
      .replace('{x}', String(x))
      .replace('{y}', String(y))
      .replace('{z}', String(z));
    
    // Handle subdomains
    if (tileLayer.subdomains && tileLayer.subdomains.length > 0) {
      const subdomain = tileLayer.subdomains[(x + y) % tileLayer.subdomains.length];
      url = url.replace('{s}', subdomain);
    }
    
    return url;
  }, [tileLayer.urlTemplate, tileLayer.subdomains]);

  // Pre-fetch tiles around the current viewport
  const preloadTiles = useCallback(() => {
    const bounds = map.getBounds();
    const zoom = Math.floor(map.getZoom());
    
    // Skip if using non-standard CRS (tile calculations differ)
    if (tileLayer.crs && tileLayer.crs !== 'EPSG:3857') {
      return;
    }
    
    // Get tile coordinates for viewport corners
    const nw = latLngToTile(bounds.getNorth(), bounds.getWest(), zoom);
    const se = latLngToTile(bounds.getSouth(), bounds.getEast(), zoom);
    
    // Calculate tile range with buffer
    const minX = nw.x - bufferTiles;
    const maxX = se.x + bufferTiles;
    const minY = nw.y - bufferTiles;
    const maxY = se.y + bufferTiles;
    
    // Pre-fetch tiles
    for (let x = minX; x <= maxX; x++) {
      for (let y = minY; y <= maxY; y++) {
        const tileKey = `${zoom}/${x}/${y}`;
        
        // Skip if already preloaded
        if (preloadedTilesRef.current.has(tileKey)) {
          continue;
        }
        
        // Mark as preloaded
        preloadedTilesRef.current.add(tileKey);
        
        // Create an image to fetch the tile into browser cache
        const img = new Image();
        img.crossOrigin = 'anonymous';
        img.src = getTileUrl(x, y, zoom);
      }
    }
    
    // Limit cache size to prevent memory bloat (keep last ~1000 tiles)
    if (preloadedTilesRef.current.size > 1000) {
      const entries = Array.from(preloadedTilesRef.current);
      preloadedTilesRef.current = new Set(entries.slice(-500));
    }
  }, [map, tileLayer.crs, latLngToTile, bufferTiles, getTileUrl]);

  // Debounced preload on map movement
  useEffect(() => {
    const debouncedPreload = () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      debounceTimerRef.current = setTimeout(preloadTiles, 200);
    };

    // Initial preload
    preloadTiles();

    // Preload on movement
    map.on('moveend', debouncedPreload);
    map.on('zoomend', () => {
      // Clear cache on zoom change since tile coordinates change
      preloadedTilesRef.current.clear();
      preloadTiles();
    });

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
      map.off('moveend', debouncedPreload);
      map.off('zoomend');
    };
  }, [map, preloadTiles]);

  return null;
}

/**
 * Base map component using Leaflet
 * 
 * @stable - This component provides the foundation for all map displays.
 * Its props interface (BaseMapProps) should remain stable to prevent breaking changes
 * in dependent components like TrigDetailMap.
 * 
 * Provides a reusable map with configurable tile layers and markers.
 * Handles different coordinate reference systems (CRS) and automatically adjusts
 * zoom limits based on the selected tile layer.
 * 
 * @remarks
 * Breaking changes to consider:
 * - Changing prop types or removing props
 * - Changing default behavior of zoom limits
 * - Modifying CRS handling logic
 * - Changing how children are rendered
 * 
 * Non-breaking changes:
 * - Adding optional props
 * - Internal rendering optimizations
 * - Performance improvements
 */
export default function BaseMap({
  center,
  zoom,
  height = 400,
  tileLayerId,
  children,
  onMapReady,
  className = "",
  scrollWheelZoom = true,
  interactive = true,
  enableTilePreloader = false,
}: BaseMapProps) {
  const tileLayer = getTileLayer(tileLayerId);
  
  const heightStyle = typeof height === 'number' ? `${height}px` : height;
  
  // Use the most restrictive zoom limits from both global config and tileset
  const minZoom = Math.max(tileLayer.minZoom ?? 0, MAP_CONFIG.minZoom);
  const maxZoom = Math.min(tileLayer.maxZoom ?? 20, MAP_CONFIG.maxZoom);
  
  // Get CRS for this tileset (defaults to EPSG:3857)
  const crs = getCRS(tileLayer.crs || 'EPSG:3857');
  
  // Use only CRS as key to force remount when projection changes (not on every tileset change)
  const mapKey = tileLayer.crs || 'EPSG:3857';
  
  return (
    <div className={`relative select-none ${className}`} style={{ height: heightStyle }}>
      <MapContainer
        key={mapKey}
        center={center}
        zoom={zoom}
        crs={crs}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom={interactive && scrollWheelZoom}
        dragging={interactive}
        doubleClickZoom={interactive}
        touchZoom={interactive}
        boxZoom={interactive}
        keyboard={interactive}
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
          keepBuffer={10}
          updateWhenIdle={false}
          updateInterval={50}
        />
        
        <TileLayerUpdater tileLayerId={tileLayerId} minZoom={minZoom} maxZoom={maxZoom} />
        <InteractionController interactive={interactive} scrollWheelZoom={scrollWheelZoom} />
        {enableTilePreloader && <TilePreloader tileLayer={tileLayer} bufferTiles={3} />}
        {onMapReady && <MapReadyNotifier onMapReady={onMapReady} />}
        
        {/* Scale bar at bottom left */}
        <ScaleControl position="bottomleft" imperial={false} />
        
        {children}
      </MapContainer>
    </div>
  );
}

