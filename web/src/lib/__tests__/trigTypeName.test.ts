import { describe, it, expect } from "vitest";
import { formatTypeName } from "../trigTypeName";

describe("formatTypeName", () => {
  it("returns the type name when no material is recorded", () => {
    expect(formatTypeName("Buried Block")).toBe("Buried Block");
    expect(formatTypeName("Buried Block", null)).toBe("Buried Block");
  });

  it("qualifies the type with its variant", () => {
    expect(formatTypeName("Buried Block", "Concrete ring")).toBe(
      "Buried Block (concrete ring)"
    );
  });
});
