import { describe, it, expect } from "vitest";
import { toggleAreaSelection, type SelectedArea } from "../areaSelection";

const derbyshire: SelectedArea = { id: 1, name: "Derbyshire", areaTypeId: 1, areaTypeName: "Historic County" };
const cheshire: SelectedArea = { id: 2, name: "Cheshire", areaTypeId: 1, areaTypeName: "Historic County" };
const explorerOL1: SelectedArea = { id: 900, name: "OL1", areaTypeId: 4, areaTypeName: "OS Explorer" };

describe("toggleAreaSelection", () => {
  it("adds areas of the same type", () => {
    expect(toggleAreaSelection([derbyshire], cheshire)).toEqual([derbyshire, cheshire]);
  });

  it("removes an area that is already selected", () => {
    expect(toggleAreaSelection([derbyshire, cheshire], derbyshire)).toEqual([cheshire]);
  });

  it("replaces the selection when the area is of another type", () => {
    expect(toggleAreaSelection([derbyshire, cheshire], explorerOL1)).toEqual([explorerOL1]);
  });
});
