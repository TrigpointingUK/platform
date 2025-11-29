import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import {
  clampToPixelBBox,
  getBaseDimensions,
  loadMiniMapCalibration,
  lonLatToPixel,
  resetMiniMapCalibrationCache,
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

