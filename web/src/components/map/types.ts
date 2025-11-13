/**
 * Centralized type definitions for map components
 * 
 * @stable - These types form the stable API contract for map components.
 * Changes to these interfaces should be considered breaking changes.
 */

import type { LatLngExpression } from "leaflet";
import type { IconColorMode, UserLogStatus } from "../../lib/mapIcons";

/**
 * @stable
 * Trigpoint data structure used across map components
 * 
 * This interface represents the core trigpoint data model.
 * All map components that display trigpoint information should use this interface.
 */
export interface TrigData {
  id: number;
  waypoint: string;
  name: string;
  physical_type: string;
  condition: string;
  wgs_lat: string | number;
  wgs_long: string | number;
  osgb_gridref: string;
  status_name?: string;
  distance_km?: number;
}

/**
 * @stable
 * Geographic bounds for map viewport
 * 
 * Used for fetching trigpoints within a visible area.
 */
export interface MapBounds {
  north: number;
  south: number;
  east: number;
  west: number;
}

/**
 * @stable
 * Props for the BaseMap component
 * 
 * Core map component that should remain stable across refactoring.
 */
export interface BaseMapProps {
  /** Center coordinates of the map [lat, lng] */
  center: LatLngExpression;
  /** Initial zoom level */
  zoom: number;
  /** Height of the map container (number in px or CSS string) */
  height?: number | string;
  /** ID of the tile layer to use */
  tileLayerId: string;
  /** Child components to render within the map */
  children?: React.ReactNode;
  /** Callback when map instance is ready */
  onMapReady?: (map: L.Map) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * @stable
 * Props for the TrigMarker component
 * 
 * Individual marker component used by both map pages.
 */
export interface TrigMarkerProps {
  /** Trigpoint data to display */
  trig: TrigData;
  /** Color mode for the icon (condition or user log status) */
  colorMode: IconColorMode;
  /** User's log status for this trigpoint (optional) */
  logStatus?: UserLogStatus | null;
  /** Whether this marker should be highlighted */
  highlighted?: boolean;
  /** Click handler for the marker */
  onClick?: (trig: TrigData) => void;
  /** Whether to show the popup (default: true) */
  showPopup?: boolean;
}

/**
 * @stable
 * Props for the TrigDetailMap component
 * 
 * Specialized map component for trigpoint detail pages.
 */
export interface TrigDetailMapProps {
  /** Trigpoint to display */
  trig: TrigData;
  /** Height of the map (default from MAP_CONFIG) */
  height?: number;
  /** Additional CSS classes */
  className?: string;
}

/**
 * @stable
 * Props for the TilesetSelector component
 */
export interface TilesetSelectorProps {
  /** Currently selected tile layer ID */
  value: string;
  /** Callback when selection changes */
  onChange: (tileLayerId: string) => void;
  /** Additional CSS classes */
  className?: string;
}

/**
 * Re-export commonly used types from map libraries
 */
export type { IconColorMode, UserLogStatus } from "../../lib/mapIcons";
export type { LatLngExpression } from "leaflet";

