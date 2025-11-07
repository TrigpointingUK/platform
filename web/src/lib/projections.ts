/**
 * Custom map projections for Leaflet
 * 
 * Defines CRS (Coordinate Reference Systems) for non-standard projections.
 */

import L from 'leaflet';
import 'proj4leaflet';

/**
 * EPSG:27700 - British National Grid (OSGB36)
 * 
 * Used by some OS mapping products, particularly paper maps.
 * Coordinates are in meters (eastings, northings) rather than lat/lon.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export const EPSG27700 = new (L as any).Proj.CRS('EPSG:27700', 
  '+proj=tmerc +lat_0=49 +lon_0=-2 +k=0.9996012717 +x_0=400000 +y_0=-100000 +ellps=airy +towgs84=446.448,-125.157,542.06,0.15,0.247,0.842,-20.489 +units=m +no_defs',
  {
    resolutions: [
      896.0, 448.0, 224.0, 112.0, 56.0, 28.0, 14.0, 7.0, 3.5, 1.75, 0.875, 0.4375, 0.21875, 0.109375
    ],
    origin: [-238375.0, 1376256.0],
    bounds: L.bounds(
      [-238375.0, 0.0],
      [900000.0, 1376256.0]
    ),
  }
);

/**
 * EPSG:3857 - Web Mercator (default for most web maps)
 * 
 * Standard projection used by OSM, Google Maps, etc.
 */
export const EPSG3857 = L.CRS.EPSG3857;

/**
 * Get CRS by identifier
 */
export const getCRS = (identifier: string): L.CRS => {
  switch (identifier) {
    case 'EPSG:27700':
      return EPSG27700;
    case 'EPSG:3857':
    default:
      return EPSG3857;
  }
};

