/**
 * Map link generation utilities for trigpoint detail pages.
 * 
 * Supports generating links to various mapping services:
 * - TrigpointingUK Map (internal /map page)
 * - Streetmap OS 1:25k (requires OSGB36 coordinates - GB only)
 * - OSI Map (Ordnance Survey Ireland - Ireland only)
 * - Google satellite
 * - OpenStreetMap
 */

import { wgs84ToOSGB } from './coordinates';
import type { MapLinkOption } from '../hooks/useUserProfile';

export type GridSystem = 'gb' | 'ie' | null;

export interface MapLinkConfig {
  id: MapLinkOption;
  name: string;
  /** If set, only available for this grid system */
  gridSystem?: GridSystem;
}

/**
 * Available map link options
 */
export const MAP_LINK_OPTIONS: MapLinkConfig[] = [
  { id: 'trigpointinguk', name: 'TrigpointingUK Map' },
  { id: 'streetmap', name: 'Streetmap OS 1:25k', gridSystem: 'gb' },
  { id: 'osi_map', name: 'OSI Map (Ireland)', gridSystem: 'ie' },
  { id: 'google_satellite', name: 'Google satellite' },
  { id: 'openstreetmap', name: 'OpenStreetMap' },
];

/**
 * Default map link preferences
 */
export const MAP_LINK_DEFAULTS = {
  gridref: 'streetmap' as MapLinkOption,
  wgs: 'google_satellite' as MapLinkOption,
  thumbnail: 'trigpointinguk' as MapLinkOption,
};

export interface TrigLocation {
  trigId: number;
  wgsLat: number;
  wgsLong: number;
  /** Grid system: 'gb' for British National Grid, 'ie' for Irish Grid */
  gridSystem?: GridSystem;
}

/**
 * Check if a map option is available for the given grid system.
 */
export function isMapOptionAvailable(option: MapLinkOption, gridSystem: GridSystem): boolean {
  const config = MAP_LINK_OPTIONS.find(o => o.id === option);
  if (!config) return false;
  
  // If no grid system restriction, always available
  if (!config.gridSystem) return true;
  
  // Must match the required grid system
  return config.gridSystem === gridSystem;
}

/**
 * Get an alternative map option when the preferred one isn't available.
 * Falls back to TrigpointingUK map (always available).
 */
export function getFallbackMapOption(preferredOption: MapLinkOption, gridSystem: GridSystem): MapLinkOption {
  if (isMapOptionAvailable(preferredOption, gridSystem)) {
    return preferredOption;
  }
  
  // For Irish Grid, fall back to OSI map for gridref links, otherwise Google
  if (gridSystem === 'ie') {
    if (preferredOption === 'streetmap') {
      return 'osi_map';
    }
  }
  
  // For GB, fall back to streetmap for gridref links
  if (gridSystem === 'gb' && preferredOption === 'osi_map') {
    return 'streetmap';
  }
  
  // Default fallback is TrigpointingUK map (always works)
  return 'trigpointinguk';
}

/**
 * Generate a map URL for the given map service and location.
 * 
 * @param option - The map service to link to
 * @param location - The trigpoint location data
 * @returns The URL string, or null for TrigpointingUK (which uses React Router)
 */
export function generateMapUrl(
  option: MapLinkOption,
  location: TrigLocation
): string | null {
  const { wgsLat, wgsLong, gridSystem } = location;

  // Check if the option is available for this grid system
  // If not, use a fallback
  const effectiveOption = getFallbackMapOption(option, gridSystem ?? null);

  switch (effectiveOption) {
    case 'trigpointinguk':
      // Return null to indicate this should use React Router's Link component
      // The path will be: /map?lat=${wgsLat}&lon=${wgsLong}&trig=${trigId}
      return null;

    case 'streetmap': {
      // Streetmap requires OSGB36 coordinates (eastings/northings)
      // Only available for GB grid system
      if (gridSystem === 'ie') {
        // Fallback to OSI map for Ireland
        return `https://maps.osi.ie/publicviewer/#V2,${wgsLat},${wgsLong},7`;
      }
      // Use Helmert transformation from WGS84
      const osgb = wgs84ToOSGB(wgsLat, wgsLong);
      return `https://streetmap.co.uk/grid/${osgb.eastings}_${osgb.northings}_115`;
    }

    case 'osi_map':
      // Ordnance Survey Ireland map viewer
      // Uses WGS84 coordinates
      return `https://maps.osi.ie/publicviewer/#V2,${wgsLat},${wgsLong},7`;

    case 'google_satellite':
      return `https://www.google.com/maps?q=${wgsLat},${wgsLong}&t=k&z=18`;

    case 'openstreetmap':
      return `https://www.openstreetmap.org/?mlat=${wgsLat}&mlon=${wgsLong}#map=16/${wgsLat}/${wgsLong}`;

    default:
      // Fallback to Google satellite
      return `https://www.google.com/maps?q=${wgsLat},${wgsLong}&t=k&z=18`;
  }
}

/**
 * Get the internal path for TrigpointingUK map
 */
export function getTrigpointingUKMapPath(location: TrigLocation): string {
  const { trigId, wgsLat, wgsLong } = location;
  return `/map?lat=${wgsLat}&lon=${wgsLong}&trig=${trigId}`;
}

/**
 * Check if a map option uses internal routing (React Router)
 */
export function isInternalMapLink(option: MapLinkOption): boolean {
  return option === 'trigpointinguk';
}

