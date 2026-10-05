import { describe, it, expect } from "vitest";
import { conditionScale, trigIconColour } from "../iconColours";

// A slice of the conditions table, in its sort order (Q and N share 90)
const scale = conditionScale([
  { code: "G", sort_order: 10, trig_colour: "green", log_colour: "green" },
  { code: "S", sort_order: 20, trig_colour: "green", log_colour: "green" },
  { code: "D", sort_order: 40, trig_colour: "yellow", log_colour: "yellow" },
  { code: "Q", sort_order: 90, trig_colour: "red", log_colour: "red" },
  { code: "N", sort_order: 90, trig_colour: "red", log_colour: "red" },
  { code: "X", sort_order: 100, trig_colour: "red", log_colour: "red" },
  { code: "U", sort_order: 120, trig_colour: "grey", log_colour: "red" },
  { code: "Z", sort_order: 130, trig_colour: "grey", log_colour: "green" },
]);

describe("trigIconColour", () => {
  it("colours by the current condition", () => {
    expect(trigIconColour({ condition: "G", logged_condition: "X" }, "current", scale)).toBe("green");
    expect(trigIconColour({ condition: "U" }, "current", scale)).toBe("grey");
  });

  it("colours by the logged condition with its own colours", () => {
    expect(trigIconColour({ condition: "G", logged_condition: "D" }, "logged", scale)).toBe("yellow");
    // Unknown is grey as a trig's condition but red as a logged one
    expect(trigIconColour({ condition: "G", logged_condition: "U" }, "logged", scale)).toBe("red");
    expect(trigIconColour({ condition: "G", logged_condition: null }, "logged", scale)).toBe("grey");
  });

  it("falls back to the built-in colours for codes the scale lacks", () => {
    const empty = conditionScale([]);
    expect(trigIconColour({ condition: "D" }, "current", empty)).toBe("yellow");
    expect(trigIconColour({ condition: "G", logged_condition: "Z" }, "logged", empty)).toBe("green");
  });

  it("colours a difference by steps apart in the sort order", () => {
    const diff = (condition: string, logged: string | null) =>
      trigIconColour({ condition, logged_condition: logged }, "difference", scale);
    expect(diff("G", "G")).toBe("green");
    expect(diff("G", "S")).toBe("yellow");
    expect(diff("S", "G")).toBe("yellow");
    expect(diff("G", "D")).toBe("red");
    // Shared sort order: the same position
    expect(diff("Q", "N")).toBe("green");
    expect(diff("N", "X")).toBe("yellow");
    expect(diff("G", null)).toBe("grey");
  });

  it("can't compare a log with no condition", () => {
    expect(trigIconColour({ condition: "G", logged_condition: "Z" }, "difference", scale)).toBe("grey");
    // The logged colours still count it as a find, as on the main map
    expect(trigIconColour({ condition: "G", logged_condition: "Z" }, "logged", scale)).toBe("green");
  });

  it("can't compare conditions off the scale", () => {
    expect(
      trigIconColour({ condition: "G", logged_condition: "?" }, "difference", scale)
    ).toBe("grey");
  });
});
