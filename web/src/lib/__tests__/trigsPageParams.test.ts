import { describe, expect, it } from "vitest";
import { readAreaIds, readSelection, writeSelection } from "../trigsPageParams";

const ALL = ["G", "S", "D"];

function roundTrip<T extends string | number>(selected: T[], all: T[]): T[] {
  const params = new URLSearchParams();
  writeSelection(params, "key", selected, all);
  // Through a real URL, as a shared link or refresh would
  return readSelection(new URLSearchParams(params.toString()), "key", all);
}

describe("readSelection", () => {
  it("selects everything when the parameter is absent", () => {
    expect(readSelection(new URLSearchParams(""), "conditions", ALL)).toEqual(ALL);
  });

  it("selects nothing when the parameter is empty", () => {
    expect(readSelection(new URLSearchParams("conditions="), "conditions", ALL)).toEqual([]);
  });

  it("drops unknown values", () => {
    expect(readSelection(new URLSearchParams("conditions=G,X"), "conditions", ALL)).toEqual(["G"]);
  });

  it("falls back to everything when no listed value is known", () => {
    expect(readSelection(new URLSearchParams("conditions=X,Y"), "conditions", ALL)).toEqual(ALL);
  });

  it("reads numbers", () => {
    expect(readSelection(new URLSearchParams("categories=10,30"), "categories", [10, 20, 30])).toEqual([10, 30]);
  });
});

describe("writeSelection", () => {
  it("omits the parameter when everything is selected", () => {
    const params = new URLSearchParams();
    writeSelection(params, "conditions", ["D", "G", "S"], ALL);
    expect(params.has("conditions")).toBe(false);
  });

  it("round-trips a partial selection", () => {
    expect(roundTrip(["G", "D"], ALL)).toEqual(["G", "D"]);
  });

  it("round-trips an empty selection", () => {
    expect(roundTrip([], ALL)).toEqual([]);
  });

  it("round-trips values containing spaces", () => {
    const uses = ["Active station", "GPS Station", "none"];
    expect(roundTrip(["Active station", "none"], uses)).toEqual(["Active station", "none"]);
  });

  it("round-trips numbers", () => {
    expect(roundTrip([20], [10, 20, 30])).toEqual([20]);
  });
});

describe("readAreaIds", () => {
  it("reads area IDs, ignoring junk", () => {
    expect(readAreaIds(new URLSearchParams("areas=12,abc,34,-1"))).toEqual([12, 34]);
  });

  it("is empty when there's no area filter", () => {
    expect(readAreaIds(new URLSearchParams(""))).toEqual([]);
  });
});
