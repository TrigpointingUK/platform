/**
 * Map tile layer configuration
 * 
 * Defines available tilesets with URLs, attribution, and settings.
 * Tile server URLs can be configured via environment variables.
 */

export interface TileLayer {
  id: string;
  name: string;
  urlTemplate: string;
  attribution: string;
  maxZoom: number;
  maxNativeZoom?: number; // Highest zoom with actual tiles (scales beyond this)
  minZoom?: number;
  subdomains?: string[];
  tileSize?: number;
  crs?: string; // Coordinate Reference System (e.g., 'EPSG:3857', 'EPSG:27700')
}

// Get tile server URLs from environment variables with fallbacks
const getTileServerUrl = (envKey: string, fallback: string): string => {
  return (import.meta.env[envKey] as string) || fallback;
};

/**
 * Available tile layers
 * 
 * Note: OS Landranger tiles require a tile server with appropriate licensing.
 * Configure the URL via VITE_TILE_OS_LANDRANGER environment variable.
 */
export const TILE_LAYERS: Record<string, TileLayer> = {

  osDigital: {
    id: 'osDigital',
    name: 'OS Digital',
    urlTemplate: getTileServerUrl(
      'VITE_TILE_OS_DIGITAL',
      'https://api.os.uk/maps/raster/v1/zxy/Outdoor_3857/{z}/{x}/{y}.png?key=gkJqb8OXGfEt6ANhLN3yC6DEk3Ur97Dj'
    ),
    attribution: '© Ordnance Survey',
    minZoom: 7,
    maxZoom: 20,
    maxNativeZoom: 20,
    crs: 'EPSG:3857',
  },
  
  // osDigitalLight: {
  //   id: 'osDigitalLight',
  //   name: 'OS Digital Light',
  //   urlTemplate: getTileServerUrl(
  //     'VITE_TILE_OS_DIGITAL_LIGHT',
  //     'https://api.os.uk/maps/raster/v1/zxy/Light_3857/{z}/{x}/{y}.png?key=gkJqb8OXGfEt6ANhLN3yC6DEk3Ur97Dj'
  //   ),
  //   attribution: '© Ordnance Survey',
  //   minZoom: 7,
  //   maxZoom: 20,
  //   maxNativeZoom: 20, // Tiles available up to zoom 16, scale beyond
  // },
  


  osPaper: {
    id: 'osPaper',
    name: 'OS Paper',
    urlTemplate: getTileServerUrl(
      'VITE_TILE_OS_PAPER',
      'https://api.os.uk/maps/raster/v1/zxy/Leisure_27700/{z}/{x}/{y}.png?key=gkJqb8OXGfEt6ANhLN3yC6DEk3Ur97Dj'
    ),
    attribution: '© Ordnance Survey',
    minZoom: 7,
    maxZoom: 13, // EPSG:27700 has different zoom levels
    maxNativeZoom: 13,
    crs: 'EPSG:27700', // British National Grid
    tileSize: 256,
  },


  osm: {
    id: 'osm',
    name: 'OpenStreetMap',
    urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
    attribution: '© OpenStreetMap contributors',
    minZoom: 0,
    maxZoom: 20,
    maxNativeZoom: 19,
    crs: 'EPSG:3857',
    subdomains: ['a', 'b', 'c'],
  },
  

  openTopoMap: {
    id: 'openTopoMap',
    name: 'OpenTopoMap',
    urlTemplate: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
    attribution: '© OpenTopoMap contributors',
    minZoom: 0,
    maxZoom: 20,
    maxNativeZoom: 17,
    crs: 'EPSG:3857',
    subdomains: ['a', 'b', 'c'],
  },
  // osmMapnik: {
  //   id: 'osmMapnik',
  //   name: 'Mapnik (OSM)',
  //   urlTemplate: 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',
  //   attribution: '© OpenStreetMap contributors',
  //   maxZoom: 20,
  //   maxNativeZoom: 19,
  //   subdomains: ['a', 'b', 'c'],
  // },
  
  esriSatellite: {
    id: 'esriSatellite',
    name: 'Satellite',
    urlTemplate: getTileServerUrl(
      'VITE_TILE_ESRI_SATELLITE',
      'https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}'
    ),
    attribution: '© Esri, Maxar, Earthstar Geographics',
    minZoom: 0,
    maxZoom: 20,
    maxNativeZoom: 19,
    crs: 'EPSG:3857',
  },
  

};

/**
 * Default tile layer to use on initial load
 */
export const DEFAULT_TILE_LAYER = 'osm';

/**
 * Get a tile layer by ID
 */
export const getTileLayer = (id: string): TileLayer => {
  return TILE_LAYERS[id] || TILE_LAYERS[DEFAULT_TILE_LAYER];
};

/**
 * Get array of all available tile layers
 */
export const getAvailableTileLayers = (): TileLayer[] => {
  return Object.values(TILE_LAYERS);
};

/**
 * Storage key for persisting user's preferred tile layer
 */
export const TILE_LAYER_STORAGE_KEY = 'trigpointing_map_tile_layer';

/**
 * Get the user's preferred tile layer from localStorage
 */
export const getPreferredTileLayer = (): string => {
  try {
    return localStorage.getItem(TILE_LAYER_STORAGE_KEY) || DEFAULT_TILE_LAYER;
  } catch {
    return DEFAULT_TILE_LAYER;
  }
};

/**
 * Save the user's preferred tile layer to localStorage
 */
export const setPreferredTileLayer = (layerId: string): void => {
  try {
    localStorage.setItem(TILE_LAYER_STORAGE_KEY, layerId);
  } catch (error) {
    console.error('Failed to save tile layer preference:', error);
  }
};

/**
 * Map view configuration
 */
export const MAP_CONFIG = {
  // Default center (UK center)
  defaultCenter: { lat: 54.5, lng: -2.0 } as const,
  defaultZoom: 7,
  
  // Zoom levels
  minZoom: 4,
  maxZoom: 20,
  
  // Detail map settings
  detailMapZoom: 14,
  detailMapHeight: 350,
  
  // Marker clustering threshold
  markerThreshold: 500,
  
  // Viewport data fetching
  viewportPadding: 0.1, // 10% padding around viewport
  debounceMs: 500, // Debounce viewport changes
  
  // Tile caching
  tileCache: {
    maxAge: 7 * 24 * 60 * 60, // 7 days in seconds
    crossOrigin: 'anonymous' as const,
  },
};

