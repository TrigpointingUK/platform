import { describe, it, expect } from "vitest";
import { parseTrigPoints } from "../useTrigPoints";

describe("parseTrigPoints", () => {
  it("maps compact rows to trig objects by field name", () => {
    const result = parseTrigPoints({
      fields: ["id", "waypoint", "name", "lat", "lon", "condition", "osgb_gridref", "type_name", "category_code"],
      rows: [[7, "TP0007", "Kinder Low", 53.4, -1.87, "G", "SK 07900 87000", "Hotine", "PILLAR"]],
      total: 1,
      truncated: false,
    });

    expect(result.truncated).toBe(false);
    expect(result.trigs).toEqual([
      {
        id: 7,
        waypoint: "TP0007",
        name: "Kinder Low",
        wgs_lat: 53.4,
        wgs_long: -1.87,
        condition: "G",
        osgb_gridref: "SK 07900 87000",
        type_name: "Hotine",
        category_code: "PILLAR",
      },
    ]);
  });

  it("copes with missing type and category", () => {
    const result = parseTrigPoints({
      fields: ["id", "waypoint", "name", "lat", "lon", "condition", "osgb_gridref", "type_name", "category_code"],
      rows: [[8, "TP0008", "Nowhere", 50, -3, "U", "", null, null]],
      total: 1,
      truncated: true,
    });
    expect(result.trigs[0].type_name).toBeUndefined();
    expect(result.trigs[0].category_code).toBeUndefined();
    expect(result.truncated).toBe(true);
  });
});
