/**
 * Map link generation utilities for trigpoint detail pages.
 * 
 * Supports generating links to various mapping services:
 * - TrigpointingUK Map (internal /map page)
 * - Streetmap OS 1:25k (requires OSGB36 coordinates)
 * - Google satellite
 * - OpenStreetMap
 */

import { wgs84ToOSGB } from './coordinates';
import type { MapLinkOption } from '../hooks/useUserProfile';

export interface MapLinkConfig {
  id: MapLinkOption;
  name: string;
}

/**
 * Available map link options
 */
export const MAP_LINK_OPTIONS: MapLinkConfig[] = [
  { id: 'trigpointinguk', name: 'TrigpointingUK Map' },
  { id: 'streetmap', name: 'Streetmap OS 1:25k' },
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
  const { wgsLat, wgsLong } = location;

  switch (option) {
    case 'trigpointinguk':
      // Return null to indicate this should use React Router's Link component
      // The path will be: /map?lat=${wgsLat}&lon=${wgsLong}&trig=${trigId}
      return null;

    case 'streetmap': {
      // Streetmap requires OSGB36 coordinates (eastings/northings)
      // Use Helmert transformation from WGS84
      const osgb = wgs84ToOSGB(wgsLat, wgsLong);
      return `https://streetmap.co.uk/grid/${osgb.eastings}_${osgb.northings}_115`;
    }

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

