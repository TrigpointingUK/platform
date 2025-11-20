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

