import { describe, expect, it } from "vitest";
import {
  readAreaIds,
  readListFilter,
  readSelection,
  writeListFilter,
  writeSelection,
} from "../trigsPageParams";

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

describe("list filter", () => {
  function roundTripList(filter: Parameters<typeof writeListFilter>[1]) {
    const params = new URLSearchParams();
    writeListFilter(params, filter);
    return { query: params.toString(), read: readListFilter(new URLSearchParams(params.toString())) };
  }

  it("round-trips 'in' lists", () => {
    const { query, read } = roundTripList({ mode: "in", listIds: [3, 7] });
    expect(query).toBe("lists=3%2C7");
    expect(read).toEqual({ mode: "in", listIds: [3, 7] });
  });

  it("round-trips 'not in' lists", () => {
    const { query, read } = roundTripList({ mode: "not_in", listIds: [3] });
    expect(query).toBe("lists=3&listsMode=not");
    expect(read).toEqual({ mode: "not_in", listIds: [3] });
  });

  it("leaves the URL alone when off, or when no list is picked", () => {
    expect(roundTripList({ mode: "all", listIds: [3] }).query).toBe("");
    expect(roundTripList({ mode: "in", listIds: [] }).query).toBe("");
  });

  it("ignores junk IDs, and listsMode without lists", () => {
    expect(readListFilter(new URLSearchParams("lists=abc,5,-2"))).toEqual({ mode: "in", listIds: [5] });
    expect(readListFilter(new URLSearchParams("listsMode=not"))).toEqual({ mode: "all", listIds: [] });
  });
});
