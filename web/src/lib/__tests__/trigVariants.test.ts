import { describe, it, expect } from "vitest";
import {
  VARIANT_NOT_RECORDED,
  allVariantFilterValues,
  relevantVariantGroups,
  typeVariantGroup,
  variantFilter,
} from "../trigVariants";
import type { TrigCategory } from "../../hooks/useTrigTypes";
import type { VariantGroup } from "../../hooks/useReferenceData";

const type = (id: number, code: string, variant_group: string | null = null) => ({
  id,
  category_id: 3,
  code,
  name: code,
  description: null,
  wiki_url: null,
  sort_order: id,
  variant_group,
});

const CATEGORIES: TrigCategory[] = [
  {
    id: 3,
    code: "SURVEY_MARK",
    name: "Survey mark",
    description: null,
    wiki_url: null,
    sort_order: 30,
    types: [type(7, "BURIED_BLOCK", "DETECTOR"), type(8, "RIVET")],
  },
];

describe("typeVariantGroup", () => {
  it("returns the type's group", () => {
    expect(typeVariantGroup(CATEGORIES, 7)).toBe("DETECTOR");
  });

  it("is null for types without variants, no type or unknown type", () => {
    expect(typeVariantGroup(CATEGORIES, 8)).toBeNull();
    expect(typeVariantGroup(CATEGORIES, null)).toBeNull();
    expect(typeVariantGroup(CATEGORIES, 999)).toBeNull();
    expect(typeVariantGroup(undefined, 7)).toBeNull();
  });
});

describe("relevantVariantGroups", () => {
  const DETECTOR: VariantGroup = {
    code: "DETECTOR",
    name: "Detector material",
    values: [{ value: "CONCRETE_RING", label: "Concrete ring" }],
  };
  const DESIGN: VariantGroup = {
    code: "DESIGN",
    name: "Pillar design",
    values: [{ value: "HOTINE", label: "Hotine" }],
  };
  const GROUPS = [DETECTOR, DESIGN];
  const ALL = ["PILLAR", "BURIED_BLOCK", "BOLT", "RIVET"];
  const TYPE_GROUPS = new Map([
    ["BURIED_BLOCK", "DETECTOR"],
    ["BOLT", "DETECTOR"],
    ["PILLAR", "DESIGN"],
  ]);
  const codes = (groups: VariantGroup[]) => groups.map((g) => g.code);
  // The default: everything ticked, i.e. no filter
  const EVERY = allVariantFilterValues(GROUPS);

  it("lists every variant then not recorded", () => {
    expect(EVERY).toEqual(["CONCRETE_RING", "HOTINE", VARIANT_NOT_RECORDED]);
  });

  it("offers nothing while every type is selected", () => {
    expect(relevantVariantGroups(GROUPS, ALL, TYPE_GROUPS)).toEqual([]);
  });

  it("offers the groups of the selected types when they all have variants", () => {
    expect(codes(relevantVariantGroups(GROUPS, ["BURIED_BLOCK"], TYPE_GROUPS))).toEqual([
      "DETECTOR",
    ]);
    expect(codes(relevantVariantGroups(GROUPS, ["BURIED_BLOCK", "BOLT"], TYPE_GROUPS))).toEqual([
      "DETECTOR",
    ]);
    expect(codes(relevantVariantGroups(GROUPS, ["PILLAR", "BOLT"], TYPE_GROUPS))).toEqual([
      "DETECTOR",
      "DESIGN",
    ]);
  });

  it("offers nothing once any selected type has no variants", () => {
    expect(relevantVariantGroups(GROUPS, ["BOLT", "RIVET"], TYPE_GROUPS)).toEqual([]);
    expect(relevantVariantGroups(GROUPS, ["RIVET"], TYPE_GROUPS)).toEqual([]);
  });

  it("offers nothing while no type is selected", () => {
    expect(relevantVariantGroups(GROUPS, [], TYPE_GROUPS)).toEqual([]);
  });
});

describe("variantFilter", () => {
  const DETECTOR: VariantGroup = {
    code: "DETECTOR",
    name: "Detector material",
    values: [
      { value: "CONCRETE_RING", label: "Concrete ring" },
      { value: "BRONZE_RING", label: "Bronze ring" },
    ],
  };
  const DESIGN: VariantGroup = {
    code: "DESIGN",
    name: "Pillar design",
    values: [{ value: "HOTINE", label: "Hotine" }],
  };

  it("doesn't filter while the filter is hidden, whatever is ticked", () => {
    expect(variantFilter([], ["CONCRETE_RING"])).toBeUndefined();
    expect(variantFilter([], [])).toBeUndefined();
  });

  it("doesn't filter while everything on offer is ticked", () => {
    expect(
      variantFilter([DETECTOR], ["CONCRETE_RING", "BRONZE_RING", VARIANT_NOT_RECORDED])
    ).toBeUndefined();
  });

  it("ignores ticks outside the groups on offer", () => {
    expect(
      variantFilter([DETECTOR], ["CONCRETE_RING", "BRONZE_RING", VARIANT_NOT_RECORDED, "HOTINE"])
    ).toBeUndefined();
    expect(variantFilter([DETECTOR], ["CONCRETE_RING", "HOTINE"])).toEqual(["CONCRETE_RING"]);
  });

  it("filters by the ticked values, empty meaning nothing", () => {
    expect(variantFilter([DETECTOR, DESIGN], ["HOTINE", VARIANT_NOT_RECORDED])).toEqual([
      "HOTINE",
      VARIANT_NOT_RECORDED,
    ]);
    expect(variantFilter([DETECTOR], [])).toEqual([]);
  });
});
