import { describe, it, expect } from "vitest";
import { buildTrigFilterParams, selectsNothing } from "../trigFilterParams";

describe("buildTrigFilterParams", () => {
  it("converts status IDs to category codes", () => {
    const params = buildTrigFilterParams({ statusIds: [10, 20] });
    expect(params.get("categories")).toBe("PILLAR,FBM");
    expect(params.has("status_ids")).toBe(false);
  });

  it("only sends max_km alongside a centre", () => {
    expect(buildTrigFilterParams({ maxKm: 50 }).has("max_km")).toBe(false);
    const params = buildTrigFilterParams({ lat: 53.2, lon: -1.9, maxKm: 50 });
    expect(params.get("max_km")).toBe("50");
  });

  it("sends no radius when unlimited", () => {
    const params = buildTrigFilterParams({ lat: 53.2, lon: -1.9 });
    expect(params.get("lat")).toBe("53.2");
    expect(params.has("max_km")).toBe(false);
  });

  it("sends logged_by with the log filters", () => {
    const params = buildTrigFilterParams({
      loggedBy: 411,
      showNotLogged: false,
      loggedConditions: ["G", "S"],
    });
    expect(params.get("logged_by")).toBe("411");
    expect(params.get("only_found")).toBe("true");
    expect(params.has("exclude_found")).toBe(false);
    expect(params.get("logged_conditions")).toBe("G,S");
  });

  it("sends no log filters by default", () => {
    const params = buildTrigFilterParams({});
    expect([...params.keys()]).toEqual([]);
  });

  it("prefers area_ids over area_id", () => {
    const params = buildTrigFilterParams({ areaId: 1, areaIds: [2, 3] });
    expect(params.get("area_ids")).toBe("2,3");
    expect(params.has("area_id")).toBe(false);
  });
});

describe("selectsNothing", () => {
  it("is true when a filter has an empty selection", () => {
    expect(selectsNothing({ conditions: [] })).toBe(true);
    expect(selectsNothing({ types: ["HOTINE"], historicUse: [] })).toBe(true);
  });

  it("treats an empty area selection as no filter", () => {
    expect(selectsNothing({ areaIds: [] })).toBe(false);
    expect(selectsNothing({})).toBe(false);
  });
});
