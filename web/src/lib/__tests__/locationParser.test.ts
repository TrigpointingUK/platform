import { describe, it, expect } from "vitest";
import {
  parseGridReference,
  parseLatLong,
  parseLocation,
  gridRefToEastingsNorthings,
} from "../locationParser";

describe("gridRefToEastingsNorthings", () => {
  it("should parse 6-digit grid reference without spaces", () => {
    const result = gridRefToEastingsNorthings("TL137055");
    expect(result.eastings).toBe(513700);
    expect(result.northings).toBe(205500);
    expect(result.gridRef).toBe("TL 13700 05500");
  });

  it("should parse 6-digit grid reference with spaces", () => {
    const result = gridRefToEastingsNorthings("TL 137 055");
    expect(result.eastings).toBe(513700);
    expect(result.northings).toBe(205500);
    expect(result.gridRef).toBe("TL 13700 05500");
  });

  it("should parse lowercase grid reference", () => {
    const result = gridRefToEastingsNorthings("tl137055");
    expect(result.eastings).toBe(513700);
    expect(result.northings).toBe(205500);
    expect(result.gridRef).toBe("TL 13700 05500");
  });

  it("should parse 8-digit grid reference", () => {
    const result = gridRefToEastingsNorthings("TL13780553");
    expect(result.eastings).toBe(513780);
    expect(result.northings).toBe(205530);
    expect(result.gridRef).toBe("TL 13780 05530");
  });

  it("should parse 8-digit grid reference with spaces", () => {
    const result = gridRefToEastingsNorthings("TL 1378 0553");
    expect(result.eastings).toBe(513780);
    expect(result.northings).toBe(205530);
    expect(result.gridRef).toBe("TL 13780 05530");
  });

  it("should parse 10-digit grid reference", () => {
    const result = gridRefToEastingsNorthings("TL 13783 05532");
    expect(result.eastings).toBe(513783);
    expect(result.northings).toBe(205532);
    expect(result.gridRef).toBe("TL 13783 05532");
  });

  it("should throw error for 5-digit grid reference", () => {
    expect(() => gridRefToEastingsNorthings("TL13705")).toThrow(
      "Grid reference must have 6, 8, or 10 digits"
    );
  });

  it("should throw error for invalid grid letters", () => {
    expect(() => gridRefToEastingsNorthings("XX123456")).toThrow(
      "Invalid first letter in grid reference"
    );
  });

  it("should throw error for too short input", () => {
    expect(() => gridRefToEastingsNorthings("TL123")).toThrow(
      "Grid reference must have 6, 8, or 10 digits"
    );
  });

  it("should throw error for invalid format", () => {
    expect(() => gridRefToEastingsNorthings("12345678")).toThrow(
      "Invalid grid reference format"
    );
  });
});

describe("parseGridReference", () => {
  it("should return success for valid grid reference", () => {
    const result = parseGridReference("TL137055");
    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data?.eastings).toBe(513700);
  });

  it("should return error for invalid grid reference", () => {
    const result = parseGridReference("TL13705");
    expect(result.success).toBe(false);
    expect(result.error).toBeDefined();
  });
});

describe("parseLatLong", () => {
  it("should parse valid coordinates with space", () => {
    const result = parseLatLong("53.69417, -1.78231");
    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data?.lat).toBeCloseTo(53.69417, 5);
    expect(result.data?.lon).toBeCloseTo(-1.78231, 5);
  });

  it("should parse valid coordinates without space", () => {
    const result = parseLatLong("53.69417,-1.78231");
    expect(result.success).toBe(true);
    expect(result.data).toBeDefined();
    expect(result.data?.lat).toBeCloseTo(53.69417, 5);
    expect(result.data?.lon).toBeCloseTo(-1.78231, 5);
  });

  it("should return error for missing longitude", () => {
    const result = parseLatLong("53.69417");
    expect(result.success).toBe(false);
    expect(result.error).toContain("format");
  });

  it("should return error for non-numeric values", () => {
    const result = parseLatLong("abc, def");
    expect(result.success).toBe(false);
    expect(result.error).toContain("Invalid");
  });

  it("should return error for out-of-range latitude", () => {
    const result = parseLatLong("91.0, 0.0");
    expect(result.success).toBe(false);
    expect(result.error).toContain("Latitude");
  });

  it("should return error for out-of-range longitude", () => {
    const result = parseLatLong("0.0, 181.0");
    expect(result.success).toBe(false);
    expect(result.error).toContain("Longitude");
  });
});

describe("parseLocation", () => {
  it("should return empty error for empty input", () => {
    const result = parseLocation("");
    expect(result.success).toBe(false);
    expect(result.error).toBe("");
  });

  it("should parse grid reference first", () => {
    const result = parseLocation("TL137055");
    expect(result.success).toBe(true);
    expect(result.data?.gridRef).toBe("TL 13700 05500");
  });

  it("should parse lat/long if grid reference fails", () => {
    const result = parseLocation("53.69417, -1.78231");
    expect(result.success).toBe(true);
    expect(result.data?.lat).toBeCloseTo(53.69417, 5);
  });

  it("should return generic error if both formats fail", () => {
    const result = parseLocation("invalid input");
    expect(result.success).toBe(false);
    expect(result.error).toContain("Invalid location format");
  });
});
