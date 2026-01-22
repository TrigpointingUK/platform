import { describe, it, expect } from "vitest";
import {
  mapTrigColourToIconColor,
  mapLogColourToIconColor,
  mapTrigColourToVariant,
  getConditionColour,
  getUserLogColour,
  conditionsAreSimilar,
  conditionsDisagree,
  getConditionIcon,
  getConditionName,
  getConditionVariant,
} from "../conditionUtils";
import type { Condition } from "../api";

// Sample conditions for testing
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
    code: "S",
    name: "Slightly Damaged",
    description: null,
    icon_file: "c_slightlydamaged.png",
    trig_colour: "green",
    log_colour: "green",
    similar_codes: "GD",
    wiki_url: null,
    sort_order: 2,
  },
  {
    code: "D",
    name: "Damaged",
    description: null,
    icon_file: "c_damaged.png",
    trig_colour: "yellow",
    log_colour: "yellow",
    similar_codes: "S",
    wiki_url: null,
    sort_order: 3,
  },
  {
    code: "Q",
    name: "Possibly Missing",
    description: null,
    icon_file: "c_possiblymissing.png",
    trig_colour: "red",
    log_colour: "red",
    similar_codes: "N",
    wiki_url: null,
    sort_order: 8,
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
    code: "N",
    name: "Couldn't Find",
    description: null,
    icon_file: "c_possiblymissing.png",
    trig_colour: "red",
    log_colour: null, // N has no log_colour - it's uncertain
    similar_codes: "Q",
    wiki_url: null,
    sort_order: 11,
  },
  {
    code: "P",
    name: "Inaccessible",
    description: null,
    icon_file: "c_unknown.png",
    trig_colour: "grey",
    log_colour: null, // P has no log_colour - it's uncertain
    similar_codes: null,
    wiki_url: null,
    sort_order: 12,
  },
  {
    code: "V",
    name: "Unreachable but Visible",
    description: null,
    icon_file: "c_unreachablebutvisible.png",
    trig_colour: "yellow",
    log_colour: null, // V has no log_colour - uncertain for disagreement
    similar_codes: null,
    wiki_url: null,
    sort_order: 7,
  },
];

const conditionMap = new Map(sampleConditions.map((c) => [c.code, c]));

describe("mapTrigColourToIconColor", () => {
  it("should map green to green", () => {
    expect(mapTrigColourToIconColor("green")).toBe("green");
  });

  it("should map yellow to yellow", () => {
    expect(mapTrigColourToIconColor("yellow")).toBe("yellow");
  });

  it("should map orange to yellow", () => {
    expect(mapTrigColourToIconColor("orange")).toBe("yellow");
  });

  it("should map amber to yellow", () => {
    expect(mapTrigColourToIconColor("amber")).toBe("yellow");
  });

  it("should map red to red", () => {
    expect(mapTrigColourToIconColor("red")).toBe("red");
  });

  it("should map unknown colours to grey", () => {
    expect(mapTrigColourToIconColor("purple")).toBe("grey");
    expect(mapTrigColourToIconColor("blue")).toBe("grey");
  });

  it("should return grey for null", () => {
    expect(mapTrigColourToIconColor(null)).toBe("grey");
  });

  it("should return grey for undefined", () => {
    expect(mapTrigColourToIconColor(undefined)).toBe("grey");
  });

  it("should be case-insensitive", () => {
    expect(mapTrigColourToIconColor("GREEN")).toBe("green");
    expect(mapTrigColourToIconColor("Green")).toBe("green");
    expect(mapTrigColourToIconColor("YELLOW")).toBe("yellow");
  });
});

describe("mapLogColourToIconColor", () => {
  it("should map colours the same as trig colour", () => {
    expect(mapLogColourToIconColor("green")).toBe("green");
    expect(mapLogColourToIconColor("yellow")).toBe("yellow");
    expect(mapLogColourToIconColor("red")).toBe("red");
    expect(mapLogColourToIconColor(null)).toBe("grey");
  });
});

describe("mapTrigColourToVariant", () => {
  it("should map green to good", () => {
    expect(mapTrigColourToVariant("green")).toBe("good");
  });

  it("should map yellow to damaged", () => {
    expect(mapTrigColourToVariant("yellow")).toBe("damaged");
  });

  it("should map red to missing", () => {
    expect(mapTrigColourToVariant("red")).toBe("missing");
  });

  it("should map unknown to unknown", () => {
    expect(mapTrigColourToVariant("grey")).toBe("unknown");
    expect(mapTrigColourToVariant(null)).toBe("unknown");
    expect(mapTrigColourToVariant("blue")).toBe("unknown");
  });
});

describe("getConditionColour", () => {
  it("should return green for G condition", () => {
    expect(getConditionColour(conditionMap, "G")).toBe("green");
  });

  it("should return yellow for D condition", () => {
    expect(getConditionColour(conditionMap, "D")).toBe("yellow");
  });

  it("should return red for X condition", () => {
    expect(getConditionColour(conditionMap, "X")).toBe("red");
  });

  it("should return grey for unknown condition", () => {
    expect(getConditionColour(conditionMap, "UNKNOWN")).toBe("grey");
  });

  it("should return grey for null condition", () => {
    expect(getConditionColour(conditionMap, null)).toBe("grey");
  });

  it("should be case-insensitive", () => {
    expect(getConditionColour(conditionMap, "g")).toBe("green");
    expect(getConditionColour(conditionMap, "d")).toBe("yellow");
  });
});

describe("getUserLogColour", () => {
  it("should return grey for not logged", () => {
    expect(
      getUserLogColour(conditionMap, { hasLogged: false })
    ).toBe("grey");
  });

  it("should return green for logged without condition (empty)", () => {
    expect(
      getUserLogColour(conditionMap, { hasLogged: true, condition: "" })
    ).toBe("green");
  });

  it("should return green for logged with Z condition", () => {
    expect(
      getUserLogColour(conditionMap, { hasLogged: true, condition: "Z" })
    ).toBe("green");
  });

  it("should return colour based on log_colour for logged conditions", () => {
    expect(
      getUserLogColour(conditionMap, { hasLogged: true, condition: "G" })
    ).toBe("green");
    expect(
      getUserLogColour(conditionMap, { hasLogged: true, condition: "D" })
    ).toBe("yellow");
    expect(
      getUserLogColour(conditionMap, { hasLogged: true, condition: "X" })
    ).toBe("red");
  });
});

describe("conditionsAreSimilar", () => {
  it("should return true for same condition", () => {
    expect(conditionsAreSimilar(conditionMap, "G", "G")).toBe(true);
    expect(conditionsAreSimilar(conditionMap, "D", "D")).toBe(true);
  });

  it("should return true for G and S (G has similar_codes: S)", () => {
    expect(conditionsAreSimilar(conditionMap, "G", "S")).toBe(true);
    expect(conditionsAreSimilar(conditionMap, "S", "G")).toBe(true);
  });

  it("should return true for D and S (S has similar_codes: GD)", () => {
    expect(conditionsAreSimilar(conditionMap, "D", "S")).toBe(true);
    expect(conditionsAreSimilar(conditionMap, "S", "D")).toBe(true);
  });

  it("should return true for Q and N (both have each other)", () => {
    expect(conditionsAreSimilar(conditionMap, "Q", "N")).toBe(true);
    expect(conditionsAreSimilar(conditionMap, "N", "Q")).toBe(true);
  });

  it("should return false for G and D (not similar)", () => {
    expect(conditionsAreSimilar(conditionMap, "G", "D")).toBe(false);
  });

  it("should return false for G and X (not similar)", () => {
    expect(conditionsAreSimilar(conditionMap, "G", "X")).toBe(false);
  });

  it("should handle null/undefined codes", () => {
    expect(conditionsAreSimilar(conditionMap, null, "G")).toBe(false);
    expect(conditionsAreSimilar(conditionMap, "G", null)).toBe(false);
    // null === null is technically "same code" so returns true
    expect(conditionsAreSimilar(conditionMap, null, null)).toBe(true);
  });

  it("should be case-insensitive", () => {
    expect(conditionsAreSimilar(conditionMap, "g", "s")).toBe(true);
    expect(conditionsAreSimilar(conditionMap, "G", "s")).toBe(true);
  });
});

describe("conditionsDisagree", () => {
  it("should return false when logged condition has no log_colour (uncertain)", () => {
    // N has no log_colour, so it shouldn't trigger disagreement
    expect(conditionsDisagree(conditionMap, "N", "G")).toBe(false);
    expect(conditionsDisagree(conditionMap, "P", "G")).toBe(false);
  });

  it("should return false when conditions are similar", () => {
    expect(conditionsDisagree(conditionMap, "G", "S")).toBe(false);
    expect(conditionsDisagree(conditionMap, "S", "G")).toBe(false);
    expect(conditionsDisagree(conditionMap, "D", "S")).toBe(false);
  });

  it("should return true when conditions disagree", () => {
    expect(conditionsDisagree(conditionMap, "G", "D")).toBe(true);
    expect(conditionsDisagree(conditionMap, "G", "X")).toBe(true);
    expect(conditionsDisagree(conditionMap, "D", "X")).toBe(true);
  });

  it("should return false when no logged condition", () => {
    expect(conditionsDisagree(conditionMap, null, "G")).toBe(false);
    expect(conditionsDisagree(conditionMap, "", "G")).toBe(false);
  });

  it("should return false when no curated condition", () => {
    expect(conditionsDisagree(conditionMap, "G", null)).toBe(false);
    expect(conditionsDisagree(conditionMap, "G", "")).toBe(false);
  });

  it("should handle V condition special case for red curated", () => {
    // V has no log_colour but should show disagreement if curated is red
    expect(conditionsDisagree(conditionMap, "V", "X")).toBe(true);
    expect(conditionsDisagree(conditionMap, "V", "Q")).toBe(true);
    // But not for non-red curated
    expect(conditionsDisagree(conditionMap, "V", "G")).toBe(false);
    expect(conditionsDisagree(conditionMap, "V", "D")).toBe(false);
  });
});

describe("getConditionIcon", () => {
  it("should return icon for valid code", () => {
    expect(getConditionIcon(conditionMap, "G")).toBe("c_good.png");
    expect(getConditionIcon(conditionMap, "D")).toBe("c_damaged.png");
  });

  it("should return null for unknown code", () => {
    expect(getConditionIcon(conditionMap, "UNKNOWN")).toBeNull();
  });

  it("should return null for null code", () => {
    expect(getConditionIcon(conditionMap, null)).toBeNull();
  });

  it("should be case-insensitive", () => {
    expect(getConditionIcon(conditionMap, "g")).toBe("c_good.png");
  });
});

describe("getConditionName", () => {
  it("should return name for valid code", () => {
    expect(getConditionName(conditionMap, "G")).toBe("Good");
    expect(getConditionName(conditionMap, "D")).toBe("Damaged");
  });

  it("should return Unknown for unknown code", () => {
    expect(getConditionName(conditionMap, "UNKNOWN")).toBe("Unknown");
  });

  it("should return Unknown for null code", () => {
    expect(getConditionName(conditionMap, null)).toBe("Unknown");
  });
});

describe("getConditionVariant", () => {
  it("should return correct variant for codes", () => {
    expect(getConditionVariant(conditionMap, "G")).toBe("good");
    expect(getConditionVariant(conditionMap, "D")).toBe("damaged");
    expect(getConditionVariant(conditionMap, "X")).toBe("missing");
    expect(getConditionVariant(conditionMap, "P")).toBe("unknown");
  });

  it("should return unknown for unknown code", () => {
    expect(getConditionVariant(conditionMap, "INVALID")).toBe("unknown");
  });
});

