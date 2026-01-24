import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  clampToPixelBBox,
  getBaseDimensions,
  loadMiniMapCalibration,
  lonLatToPixel,
  resetMiniMapCalibrationCache,
  latLonToPixel,
  latLonToScaledPixel,
  isWithinMapBounds,
  getLogColourHex,
  MAP_DIMENSIONS,
  MAP_BOUNDS,
  LOG_COLOURS,
  type CalibrationResult,
} from "../mapCalibration";

const sampleCalibration: CalibrationResult = {
  affine: [
    [5.945945945945946, 0, 83.24324324324324],
    [0, -9.91306601410864, 603.7057202592162],
  ],
  inverse: [
    [0.16818181818181818, 0, -14],
    [0, -0.10087696365350167, 60.9],
  ],
  pixel_bbox: [0, 0, 110, 110],
  bounds_geo: [-14, 49.8, 4.5, 60.9],
};

describe("mapCalibration helpers", () => {
  beforeEach(() => {
    resetMiniMapCalibrationCache();
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("projects lon/lat to pixels with expected accuracy", () => {
    const edinburgh = lonLatToPixel(sampleCalibration, -3.1883, 55.9533);
    expect(edinburgh.x).toBeCloseTo(64.28578, 4);
    expect(edinburgh.y).toBeCloseTo(49.03696, 4);

    const london = lonLatToPixel(sampleCalibration, -0.1276, 51.5072);
    expect(london.x).toBeCloseTo(82.48454, 4);
    expect(london.y).toBeCloseTo(93.11144, 4);
  });

  it("clamps coordinates to the calibration bounding box", () => {
    const clamped = clampToPixelBBox(sampleCalibration.pixel_bbox, 200, -10);
    expect(clamped.x).toBe(110);
    expect(clamped.y).toBe(0);
  });

  it("caches calibration fetches", async () => {
    const mockJson = vi.fn().mockResolvedValue(sampleCalibration);
    const mockResponse = { ok: true, json: mockJson } as unknown as Response;
    const mockFetch = vi.spyOn(globalThis, "fetch").mockResolvedValue(mockResponse);

    const first = await loadMiniMapCalibration();
    const second = await loadMiniMapCalibration();

    expect(first).toEqual(second);
    expect(mockFetch).toHaveBeenCalledTimes(1);
    expect(mockJson).toHaveBeenCalledTimes(1);

    mockFetch.mockRestore();
  });

  it("exposes base dimensions derived from the bbox", () => {
    const dims = getBaseDimensions(sampleCalibration);
    expect(dims).toEqual({ width: 110, height: 110 });
  });
});

// ============================================================================
// User map calibration tests (for animated profile map)
// ============================================================================

describe("latLonToPixel (user map)", () => {
  it("projects Edinburgh to expected pixel coordinates", () => {
    // Edinburgh: 55.9533°N, 3.1883°W
    const result = latLonToPixel(55.9533, -3.1883);
    // These are pre-computed expected values based on the affine matrix
    expect(result.x).toBeCloseTo(701.27, 0);
    expect(result.y).toBeCloseTo(533.17, 0);
  });

  it("projects London to expected pixel coordinates", () => {
    // London: 51.5072°N, 0.1276°W
    const result = latLonToPixel(51.5072, -0.1276);
    expect(result.x).toBeCloseTo(899.83, 0);
    expect(result.y).toBeCloseTo(1012.34, 0);
  });

  it("projects Land's End to expected pixel coordinates", () => {
    // Land's End: 50.0659°N, 5.7139°W
    const result = latLonToPixel(50.0659, -5.7139);
    expect(result.x).toBeCloseTo(537.43, 0);
    expect(result.y).toBeCloseTo(1167.72, 0);
  });

  it("projects John o' Groats to expected pixel coordinates", () => {
    // John o' Groats: 58.6439°N, 3.0700°W
    const result = latLonToPixel(58.6439, -3.07);
    expect(result.x).toBeCloseTo(708.94, 0);
    expect(result.y).toBeCloseTo(243.17, 0);
  });
});

describe("latLonToScaledPixel", () => {
  it("scales pixel coordinates to canvas dimensions", () => {
    // Use a simple scaling scenario: half the native dimensions
    const canvasWidth = MAP_DIMENSIONS.width / 2; // 600
    const canvasHeight = MAP_DIMENSIONS.height / 2; // 598

    // Edinburgh
    const native = latLonToPixel(55.9533, -3.1883);
    const scaled = latLonToScaledPixel(55.9533, -3.1883, canvasWidth, canvasHeight);

    expect(scaled.x).toBeCloseTo(native.x / 2, 1);
    expect(scaled.y).toBeCloseTo(native.y / 2, 1);
  });

  it("handles arbitrary canvas dimensions", () => {
    const canvasWidth = 400;
    const canvasHeight = 300;

    const result = latLonToScaledPixel(55.0, -2.0, canvasWidth, canvasHeight);

    // Verify the scaling factors are applied
    const native = latLonToPixel(55.0, -2.0);
    const scaleX = canvasWidth / MAP_DIMENSIONS.width;
    const scaleY = canvasHeight / MAP_DIMENSIONS.height;

    expect(result.x).toBeCloseTo(native.x * scaleX, 5);
    expect(result.y).toBeCloseTo(native.y * scaleY, 5);
  });

  it("produces coordinates within canvas bounds for UK coordinates", () => {
    const canvasWidth = 300;
    const canvasHeight = 400;

    // Test several UK locations
    const locations = [
      { lat: 51.5, lon: -0.1 }, // London
      { lat: 55.9, lon: -3.2 }, // Edinburgh
      { lat: 53.5, lon: -2.2 }, // Manchester
    ];

    for (const loc of locations) {
      const result = latLonToScaledPixel(loc.lat, loc.lon, canvasWidth, canvasHeight);
      expect(result.x).toBeGreaterThanOrEqual(0);
      expect(result.x).toBeLessThanOrEqual(canvasWidth);
      expect(result.y).toBeGreaterThanOrEqual(0);
      expect(result.y).toBeLessThanOrEqual(canvasHeight);
    }
  });
});

describe("isWithinMapBounds", () => {
  it("returns true for coordinates within UK bounds", () => {
    expect(isWithinMapBounds(51.5, -0.1)).toBe(true); // London
    expect(isWithinMapBounds(55.9, -3.2)).toBe(true); // Edinburgh
    expect(isWithinMapBounds(53.5, -2.2)).toBe(true); // Manchester
    expect(isWithinMapBounds(50.0, -5.0)).toBe(true); // Cornwall
    expect(isWithinMapBounds(58.5, -3.0)).toBe(true); // Northern Scotland
  });

  it("returns true for coordinates at the boundary edges", () => {
    expect(isWithinMapBounds(MAP_BOUNDS.minLat, 0)).toBe(true);
    expect(isWithinMapBounds(MAP_BOUNDS.maxLat, 0)).toBe(true);
    expect(isWithinMapBounds(55, MAP_BOUNDS.minLon)).toBe(true);
    expect(isWithinMapBounds(55, MAP_BOUNDS.maxLon)).toBe(true);
  });

  it("returns false for coordinates outside UK bounds", () => {
    expect(isWithinMapBounds(40.0, -0.1)).toBe(false); // Too far south (Spain)
    expect(isWithinMapBounds(65.0, -3.0)).toBe(false); // Too far north (Norway)
    expect(isWithinMapBounds(55.0, -20.0)).toBe(false); // Too far west (Atlantic)
    expect(isWithinMapBounds(55.0, 10.0)).toBe(false); // Too far east (North Sea)
  });

  it("returns false for coordinates just outside bounds", () => {
    expect(isWithinMapBounds(MAP_BOUNDS.minLat - 0.1, 0)).toBe(false);
    expect(isWithinMapBounds(MAP_BOUNDS.maxLat + 0.1, 0)).toBe(false);
    expect(isWithinMapBounds(55, MAP_BOUNDS.minLon - 0.1)).toBe(false);
    expect(isWithinMapBounds(55, MAP_BOUNDS.maxLon + 0.1)).toBe(false);
  });
});

describe("MAP_DIMENSIONS", () => {
  it("has expected native map dimensions", () => {
    expect(MAP_DIMENSIONS.width).toBe(1200);
    expect(MAP_DIMENSIONS.height).toBe(1196);
  });
});

describe("MAP_BOUNDS", () => {
  it("has expected geographic bounds", () => {
    expect(MAP_BOUNDS.minLon).toBe(-14.0);
    expect(MAP_BOUNDS.maxLon).toBe(4.5);
    expect(MAP_BOUNDS.minLat).toBe(49.8);
    expect(MAP_BOUNDS.maxLat).toBe(60.9);
  });
});

// ============================================================================
// Log colour utility tests
// ============================================================================

describe("getLogColourHex", () => {
  it("returns correct hex for green", () => {
    expect(getLogColourHex("green")).toBe(LOG_COLOURS.green);
    expect(getLogColourHex("green")).toBe("#22c55e");
  });

  it("returns correct hex for yellow", () => {
    expect(getLogColourHex("yellow")).toBe(LOG_COLOURS.yellow);
    expect(getLogColourHex("yellow")).toBe("#eab308");
  });

  it("returns correct hex for red", () => {
    expect(getLogColourHex("red")).toBe(LOG_COLOURS.red);
    expect(getLogColourHex("red")).toBe("#ef4444");
  });

  it("returns correct hex for grey", () => {
    expect(getLogColourHex("grey")).toBe(LOG_COLOURS.grey);
    expect(getLogColourHex("grey")).toBe("#9ca3af");
  });

  it("handles uppercase colour names", () => {
    expect(getLogColourHex("GREEN")).toBe(LOG_COLOURS.green);
    expect(getLogColourHex("YELLOW")).toBe(LOG_COLOURS.yellow);
    expect(getLogColourHex("RED")).toBe(LOG_COLOURS.red);
    expect(getLogColourHex("GREY")).toBe(LOG_COLOURS.grey);
  });

  it("handles mixed case colour names", () => {
    expect(getLogColourHex("Green")).toBe(LOG_COLOURS.green);
    expect(getLogColourHex("Yellow")).toBe(LOG_COLOURS.yellow);
    expect(getLogColourHex("Red")).toBe(LOG_COLOURS.red);
    expect(getLogColourHex("Grey")).toBe(LOG_COLOURS.grey);
  });

  it("returns grey for unknown colour names", () => {
    expect(getLogColourHex("purple")).toBe(LOG_COLOURS.grey);
    expect(getLogColourHex("blue")).toBe(LOG_COLOURS.grey);
    expect(getLogColourHex("orange")).toBe(LOG_COLOURS.grey);
    expect(getLogColourHex("")).toBe(LOG_COLOURS.grey);
    expect(getLogColourHex("invalid")).toBe(LOG_COLOURS.grey);
  });
});

describe("LOG_COLOURS", () => {
  it("has all expected colour keys", () => {
    expect(LOG_COLOURS).toHaveProperty("green");
    expect(LOG_COLOURS).toHaveProperty("yellow");
    expect(LOG_COLOURS).toHaveProperty("red");
    expect(LOG_COLOURS).toHaveProperty("grey");
  });

  it("has valid hex colour values", () => {
    const hexPattern = /^#[0-9a-f]{6}$/i;
    expect(LOG_COLOURS.green).toMatch(hexPattern);
    expect(LOG_COLOURS.yellow).toMatch(hexPattern);
    expect(LOG_COLOURS.red).toMatch(hexPattern);
    expect(LOG_COLOURS.grey).toMatch(hexPattern);
  });
});

