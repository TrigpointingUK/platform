import { describe, it, expect } from "vitest";
import {
  getConditionColor,
  getUserLogColor,
  getIconUrlForTrig,
  getConditionColorWithMap,
  getUserLogColorWithMap,
  getIconUrlForTrigWithMap,
  getIconBaseName,
  getIconBaseNameFromCategory,
  ICON_LEGENDS,
} from "../mapIcons";
import type { Condition } from "../api";

// Sample conditions for testing dynamic lookups
const sampleConditions: Condition[] = [
  {
    code: "G",
    name: "Good",
    description: null,
    icon_file: "c_good.png",
    trig_colour: "green",
    log_colour: "green",
    similar_codes: "S",
    wiki_url: null,
    sort_order: 1,
  },
  {
    code: "D",
    name: "Damaged",
    description: null,
    icon_file: "c_damaged.png",
    trig_colour: "yellow",
    log_colour: "yellow",
    similar_codes: null,
    wiki_url: null,
    sort_order: 3,
  },
  {
    code: "X",
    name: "Destroyed",
    description: null,
    icon_file: "c_definitelymissing.png",
    trig_colour: "red",
    log_colour: "red",
    similar_codes: null,
    wiki_url: null,
    sort_order: 10,
  },
  {
    code: "P",
    name: "Inaccessible",
    description: null,
    icon_file: "c_unknown.png",
    trig_colour: "grey",
    log_colour: "grey",
    similar_codes: null,
    wiki_url: null,
    sort_order: 12,
  },
];

const conditionMap = new Map(sampleConditions.map((c) => [c.code, c]));

describe("getConditionColor (hardcoded)", () => {
  it("should return green for good conditions", () => {
    expect(getConditionColor("G")).toBe("green");
    expect(getConditionColor("S")).toBe("green");
  });

  it("should return yellow for damaged conditions", () => {
    expect(getConditionColor("D")).toBe("yellow");
    expect(getConditionColor("C")).toBe("yellow");
    expect(getConditionColor("T")).toBe("yellow");
    expect(getConditionColor("V")).toBe("yellow");
  });

  it("should return red for missing conditions", () => {
    expect(getConditionColor("Q")).toBe("red");
    expect(getConditionColor("X")).toBe("red");
    expect(getConditionColor("N")).toBe("red");
  });

  it("should return grey for unknown conditions", () => {
    expect(getConditionColor("P")).toBe("grey");
    expect(getConditionColor("U")).toBe("grey");
    expect(getConditionColor("Z")).toBe("grey");
  });

  it("should handle lowercase", () => {
    expect(getConditionColor("g")).toBe("green");
    expect(getConditionColor("d")).toBe("yellow");
  });

  it("should return grey for unknown codes", () => {
    expect(getConditionColor("INVALID")).toBe("grey");
  });
});

describe("getUserLogColor (hardcoded)", () => {
  it("should return grey when not logged", () => {
    expect(getUserLogColor({ hasLogged: false })).toBe("grey");
    expect(getUserLogColor({ hasLogged: false, condition: "G" })).toBe("grey");
  });

  it("should return green for empty/Z condition when logged", () => {
    expect(getUserLogColor({ hasLogged: true, condition: "" })).toBe("green");
    expect(getUserLogColor({ hasLogged: true, condition: "Z" })).toBe("green");
  });

  it("should return red for P/U when logged", () => {
    expect(getUserLogColor({ hasLogged: true, condition: "P" })).toBe("red");
    expect(getUserLogColor({ hasLogged: true, condition: "U" })).toBe("red");
  });

  it("should return condition color for other conditions", () => {
    expect(getUserLogColor({ hasLogged: true, condition: "G" })).toBe("green");
    expect(getUserLogColor({ hasLogged: true, condition: "D" })).toBe("yellow");
    expect(getUserLogColor({ hasLogged: true, condition: "X" })).toBe("red");
  });
});

describe("getConditionColorWithMap", () => {
  it("should use map when available", () => {
    expect(getConditionColorWithMap(conditionMap, "G")).toBe("green");
    expect(getConditionColorWithMap(conditionMap, "D")).toBe("yellow");
    expect(getConditionColorWithMap(conditionMap, "X")).toBe("red");
  });

  it("should fall back to hardcoded when map is null", () => {
    expect(getConditionColorWithMap(null, "G")).toBe("green");
    expect(getConditionColorWithMap(null, "D")).toBe("yellow");
  });

  it("should fall back to hardcoded when map is empty", () => {
    const emptyMap = new Map<string, Condition>();
    expect(getConditionColorWithMap(emptyMap, "G")).toBe("green");
  });

  it("should be case-insensitive", () => {
    expect(getConditionColorWithMap(conditionMap, "g")).toBe("green");
    expect(getConditionColorWithMap(conditionMap, "d")).toBe("yellow");
  });
});

describe("getUserLogColorWithMap", () => {
  it("should use map when available", () => {
    expect(
      getUserLogColorWithMap(conditionMap, { hasLogged: true, condition: "G" })
    ).toBe("green");
    expect(
      getUserLogColorWithMap(conditionMap, { hasLogged: true, condition: "D" })
    ).toBe("yellow");
  });

  it("should fall back when map is null", () => {
    expect(
      getUserLogColorWithMap(null, { hasLogged: true, condition: "G" })
    ).toBe("green");
  });

  it("should return grey when not logged", () => {
    expect(
      getUserLogColorWithMap(conditionMap, { hasLogged: false })
    ).toBe("grey");
  });
});

describe("getIconBaseName", () => {
  it("should map physical types to icon names", () => {
    expect(getIconBaseName("Pillar")).toBe("pillar");
    expect(getIconBaseName("FBM")).toBe("fbm");
    expect(getIconBaseName("Flush Bracket")).toBe("fbm");
    expect(getIconBaseName("Passive Station")).toBe("passive");
    expect(getIconBaseName("Intersection")).toBe("intersected");
  });

  it("should return pillar as fallback", () => {
    expect(getIconBaseName("Unknown")).toBe("pillar");
    expect(getIconBaseName("Something Else")).toBe("pillar");
  });
});

describe("getIconBaseNameFromCategory", () => {
  it("should map category codes to icon names", () => {
    expect(getIconBaseNameFromCategory("PILLAR")).toBe("pillar");
    expect(getIconBaseNameFromCategory("FBM")).toBe("fbm");
    expect(getIconBaseNameFromCategory("SURVEY_MARK")).toBe("passive");
    expect(getIconBaseNameFromCategory("INTERSECTED")).toBe("intersected");
    expect(getIconBaseNameFromCategory("ACTIVE")).toBe("passive");
    expect(getIconBaseNameFromCategory("OTHER")).toBe("pillar");
  });

  it("should be case-insensitive", () => {
    expect(getIconBaseNameFromCategory("pillar")).toBe("pillar");
    expect(getIconBaseNameFromCategory("Pillar")).toBe("pillar");
  });

  it("should return pillar as fallback", () => {
    expect(getIconBaseNameFromCategory("UNKNOWN")).toBe("pillar");
    expect(getIconBaseNameFromCategory("")).toBe("pillar");
  });
});

describe("getIconUrlForTrig", () => {
  it("should generate correct URL for condition mode", () => {
    const url = getIconUrlForTrig("G", "condition", null, false, "PILLAR");
    expect(url).toBe("/icons/mapicon_pillar_green.png");
  });

  it("should generate correct URL for userLog mode", () => {
    const url = getIconUrlForTrig(
      "G",
      "userLog",
      { hasLogged: true, condition: "G" },
      false,
      "PILLAR"
    );
    expect(url).toBe("/icons/mapicon_pillar_green.png");
  });

  it("should add highlight suffix when highlighted", () => {
    const url = getIconUrlForTrig("G", "condition", null, true, "PILLAR");
    expect(url).toBe("/icons/mapicon_pillar_green_h.png");
  });

  it("should use grey for userLog mode when not logged", () => {
    const url = getIconUrlForTrig(
      "G",
      "userLog",
      { hasLogged: false },
      false,
      "PILLAR"
    );
    expect(url).toBe("/icons/mapicon_pillar_grey.png");
  });

  it("should default to pillar when no category", () => {
    const url = getIconUrlForTrig("G", "condition", null, false);
    expect(url).toBe("/icons/mapicon_pillar_green.png");
  });
});

describe("getIconUrlForTrigWithMap", () => {
  it("should use condition map for colour lookup", () => {
    const url = getIconUrlForTrigWithMap(
      conditionMap,
      "G",
      "condition",
      null,
      false,
      "PILLAR"
    );
    expect(url).toBe("/icons/mapicon_pillar_green.png");
  });

  it("should fall back when map is null", () => {
    const url = getIconUrlForTrigWithMap(
      null,
      "G",
      "condition",
      null,
      false,
      "PILLAR"
    );
    expect(url).toBe("/icons/mapicon_pillar_green.png");
  });

  it("should handle userLog mode with map", () => {
    const url = getIconUrlForTrigWithMap(
      conditionMap,
      "D",
      "userLog",
      { hasLogged: true, condition: "D" },
      false,
      "FBM"
    );
    expect(url).toBe("/icons/mapicon_fbm_yellow.png");
  });
});

describe("ICON_LEGENDS", () => {
  it("should have condition legend with 4 items", () => {
    expect(ICON_LEGENDS.condition).toHaveLength(4);
    expect(ICON_LEGENDS.condition.map((l) => l.color)).toEqual([
      "green",
      "yellow",
      "red",
      "grey",
    ]);
  });

  it("should have userLog legend with 4 items", () => {
    expect(ICON_LEGENDS.userLog).toHaveLength(4);
    expect(ICON_LEGENDS.userLog.map((l) => l.color)).toEqual([
      "green",
      "yellow",
      "red",
      "grey",
    ]);
  });

  it("should have descriptive labels", () => {
    for (const item of ICON_LEGENDS.condition) {
      expect(item.label.length).toBeGreaterThan(0);
    }
    for (const item of ICON_LEGENDS.userLog) {
      expect(item.label.length).toBeGreaterThan(0);
    }
  });
});
