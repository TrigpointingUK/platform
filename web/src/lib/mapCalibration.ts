/**
 * Map calibration utilities for converting lat/lon coordinates to pixel positions.
 *
 * Supports both the mini-map (for trig detail pages) and the animated user map.
 */

// ============================================================================
// Types
// ============================================================================

export type Matrix2x3 = [[number, number, number], [number, number, number]];

export interface CalibrationResult {
  affine: Matrix2x3;
  inverse: Matrix2x3;
  pixel_bbox: [number, number, number, number];
  bounds_geo: [number, number, number, number];
}

export interface PixelPoint {
  x: number;
  y: number;
}

// ============================================================================
// Mini-map calibration (for trig detail pages)
// ============================================================================

const MINI_MAP_STYLE = "stretched53_default";
const MINI_MAP_BASE_URL = "/maps/mini-map";
export const MINI_MAP_IMAGE_URL = `${MINI_MAP_BASE_URL}/${MINI_MAP_STYLE}.png`;

const calibrationCache = new Map<string, Promise<CalibrationResult>>();

function normaliseCalibration(payload: CalibrationResult): CalibrationResult {
  return {
    affine: payload.affine,
    inverse: payload.inverse,
    pixel_bbox: payload.pixel_bbox,
    bounds_geo: payload.bounds_geo,
  };
}

export function lonLatToPixel(
  calibration: CalibrationResult,
  lon: number,
  lat: number
): PixelPoint {
  const [[a, b, tx], [c, d, ty]] = calibration.affine;
  return {
    x: a * lon + b * lat + tx,
    y: c * lon + d * lat + ty,
  };
}

export function clampToPixelBBox(
  bbox: [number, number, number, number],
  x: number,
  y: number
): PixelPoint {
  const [left, top, right, bottom] = bbox;
  return {
    x: Math.min(Math.max(x, left), right),
    y: Math.min(Math.max(y, top), bottom),
  };
}

export function getBaseDimensions(calibration: CalibrationResult): {
  width: number;
  height: number;
} {
  const [left, top, right, bottom] = calibration.pixel_bbox;
  return {
    width: Math.max(1, right - left),
    height: Math.max(1, bottom - top),
  };
}

export async function loadMiniMapCalibration(
  style: string = MINI_MAP_STYLE
): Promise<CalibrationResult> {
  if (!calibrationCache.has(style)) {
    const promise = fetch(`${MINI_MAP_BASE_URL}/${style}.json`, {
      cache: "force-cache",
    })
      .then((response) => {
        if (!response.ok) {
          throw new Error(
            `Failed to load calibration for style "${style}": ${response.status}`
          );
        }
        return response.json();
      })
      .then((payload) => normaliseCalibration(payload));
    calibrationCache.set(style, promise);
  }
  return calibrationCache.get(style)!;
}

export function resetMiniMapCalibrationCache() {
  calibrationCache.clear();
}

// ============================================================================
// Animated user map calibration (for profile page)
// ============================================================================

/**
 * Affine transformation matrix for lon/lat to pixel conversion.
 * Pre-computed from uk_map_calibration_wgs84_stretched53.json.
 * Format: x_pixel = a * lon + b * lat + c, y_pixel = d * lon + e * lat + f
 */
const USER_MAP_AFFINE = {
  a: 64.86486486486487,
  b: 0.0,
  c: 908.1081081081081,
  d: 0.0,
  e: -107.78206320794486,
  f: 6563.927649363842,
};

/**
 * Map image dimensions (native resolution) for ukmap_wgs84_stretched53.png
 */
export const MAP_DIMENSIONS = {
  width: 1200,
  height: 1196,
};

/**
 * Geographic bounds of the user map
 */
export const MAP_BOUNDS = {
  minLon: -14.0,
  minLat: 49.8,
  maxLon: 4.5,
  maxLat: 60.9,
};

/**
 * Convert WGS84 latitude/longitude to pixel coordinates on the user map.
 *
 * @param lat - Latitude in decimal degrees (WGS84)
 * @param lon - Longitude in decimal degrees (WGS84)
 * @returns Pixel coordinates {x, y} on the native resolution map
 */
export function latLonToPixel(
  lat: number,
  lon: number
): { x: number; y: number } {
  const x = USER_MAP_AFFINE.a * lon + USER_MAP_AFFINE.b * lat + USER_MAP_AFFINE.c;
  const y = USER_MAP_AFFINE.d * lon + USER_MAP_AFFINE.e * lat + USER_MAP_AFFINE.f;
  return { x, y };
}

/**
 * Convert WGS84 latitude/longitude to pixel coordinates on a scaled map.
 *
 * @param lat - Latitude in decimal degrees (WGS84)
 * @param lon - Longitude in decimal degrees (WGS84)
 * @param canvasWidth - Width of the canvas/container
 * @param canvasHeight - Height of the canvas/container
 * @returns Pixel coordinates {x, y} scaled to the canvas dimensions
 */
export function latLonToScaledPixel(
  lat: number,
  lon: number,
  canvasWidth: number,
  canvasHeight: number
): { x: number; y: number } {
  const native = latLonToPixel(lat, lon);
  const scaleX = canvasWidth / MAP_DIMENSIONS.width;
  const scaleY = canvasHeight / MAP_DIMENSIONS.height;
  return {
    x: native.x * scaleX,
    y: native.y * scaleY,
  };
}

/**
 * Check if a lat/lon coordinate is within the map bounds.
 *
 * @param lat - Latitude in decimal degrees
 * @param lon - Longitude in decimal degrees
 * @returns true if the coordinate is within the map bounds
 */
export function isWithinMapBounds(lat: number, lon: number): boolean {
  return (
    lat >= MAP_BOUNDS.minLat &&
    lat <= MAP_BOUNDS.maxLat &&
    lon >= MAP_BOUNDS.minLon &&
    lon <= MAP_BOUNDS.maxLon
  );
}

// ============================================================================
// Log colour utilities
// ============================================================================

/**
 * Colour definitions for log conditions.
 * These match the log_colour values from the condition table.
 */
export const LOG_COLOURS = {
  green: "#22c55e", // Tailwind green-500
  yellow: "#eab308", // Tailwind yellow-500
  red: "#ef4444", // Tailwind red-500
  grey: "#9ca3af", // Tailwind gray-400
} as const;

export type LogColour = keyof typeof LOG_COLOURS;

/**
 * Get the hex colour for a log condition colour name.
 *
 * @param colour - Colour name from the API (green, yellow, red, grey)
 * @returns Hex colour string
 */
export function getLogColourHex(colour: string): string {
  const normalised = colour.toLowerCase() as LogColour;
  return LOG_COLOURS[normalised] ?? LOG_COLOURS.grey;
}
